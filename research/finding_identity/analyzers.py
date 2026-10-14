"""Analyzers that produce the findings the harness tracks: CodeGuard, Bandit or Semgrep.

Each analyzer takes one file version and returns its findings as :class:`RawFinding`
(rule, line, column and the fields some identity schemes compare). Bandit and Semgrep are
research-only dependencies (``requirements.txt``) and are imported when first used.

- ``codeguard`` runs CodeGuard's ``AnalysisRunner`` in process.
- ``bandit`` runs Bandit 1.9.4 in process, through the same ``BanditManager`` code path as
  the command line (``_parse_file``, then ``get_issue_list``). Python files only.
- ``semgrep`` runs the Semgrep 1.180.0 command line on each file with a local rules file,
  with metrics, version checks and registry access off, so runs are offline and pinned.
  Semgrep redacts ``match_based_id`` and metavariable bindings without an app token; a
  placeholder token un-redacts them. Every proxy variable points at a closed local port,
  so the scan cannot reach the network. The ``semgrep`` key is the ``match_based_id``
  Semgrep itself emitted, and every file also cross-checks the port in :mod:`schemes`.
"""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.registry import language_for_path

from .schemes import FindingMeta, SemgrepMatch, semgrep_formula_string, semgrep_match_based_ids

HERE = Path(__file__).parent
DEFAULT_SEMGREP_RULES = HERE / "semgrep_rules.yml"
BANDIT_VERSION = "1.9.4"
SEMGREP_VERSION = "1.180.0"


@dataclass(frozen=True)
class RawFinding:
    rule: str
    line: int
    col: int
    meta: FindingMeta


class Analyzer(Protocol):
    name: str

    def supports(self, path: str) -> bool:
        """Whether the analyzer looks at files like *path* at all."""
        ...

    def analyze(self, path: str, text: str) -> list[RawFinding] | None:
        """Findings for one file version, or ``None`` if it cannot be analysed."""
        ...

    def describe(self) -> dict[str, Any]:
        """Name, version and configuration, for the run's metadata."""
        ...


class CodeGuardAnalyzer:
    name = "codeguard"

    def __init__(self, rule_ids: list[str]) -> None:
        self._runner = AnalysisRunner(rule_ids=rule_ids)
        self._rule_ids = rule_ids

    def supports(self, path: str) -> bool:
        return language_for_path(path) is not None

    def analyze(self, path: str, text: str) -> list[RawFinding] | None:
        lang = language_for_path(path)
        if lang is None:
            return None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                findings = self._runner.run(text, filename=path, language=lang)
        except (SyntaxError, ValueError, RecursionError):
            return None
        return [
            RawFinding(
                f.rule_id,
                f.location.line,
                f.location.col,
                # The description is the SARIF result message.
                FindingMeta(
                    message=f.description,
                    severity=f.severity.value,
                    confidence=str(f.confidence),
                    cwe=f.cwe or "",
                    test=f.title,
                ),
            )
            for f in findings
        ]

    def describe(self) -> dict[str, Any]:
        import codeguard

        return {"analyzer": self.name, "version": codeguard.__version__, "rules": self._rule_ids}


class BanditAnalyzer:
    name = "bandit"

    def __init__(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._bandit = importlib.import_module("bandit")
            self._config = importlib.import_module("bandit.core.config").BanditConfig()
            self._manager = importlib.import_module("bandit.core.manager")
        if self._bandit.__version__ != BANDIT_VERSION:
            warnings.warn(
                f"bandit {self._bandit.__version__} installed; the harness pins "
                f"{BANDIT_VERSION} (research/finding_identity/requirements.txt)",
                stacklevel=2,
            )
        logging.getLogger("bandit").setLevel(logging.CRITICAL)

    def supports(self, path: str) -> bool:
        return path.endswith(".py")

    def analyze(self, path: str, text: str) -> list[RawFinding] | None:
        data = text.encode("utf-8")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mgr = self._manager.BanditManager(self._config, "file", quiet=True)
            mgr._parse_file(path, io.BytesIO(data), [path])
            if mgr.skipped:
                return None
            issues = mgr.get_issue_list()
        return [
            RawFinding(
                i.test_id,
                i.lineno,
                i.col_offset + 1,
                FindingMeta(
                    message=i.text,
                    severity=i.severity,
                    confidence=i.confidence,
                    cwe=str(i.cwe.id),
                    test=i.test,
                ),
            )
            for i in issues
        ]

    def describe(self) -> dict[str, Any]:
        return {"analyzer": self.name, "version": self._bandit.__version__}


def semgrep_env(home: Path) -> dict[str, str]:
    """Environment for an offline Semgrep run that still emits ``match_based_id``."""
    dead = "http://127.0.0.1:9"  # a closed port: any network request fails at once
    return {
        **os.environ,
        "HTTPS_PROXY": dead,
        "HTTP_PROXY": dead,
        "https_proxy": dead,
        "http_proxy": dead,
        "NO_PROXY": "",
        "no_proxy": "",
        "HOME": str(home),
        "SEMGREP_APP_TOKEN": "offline-placeholder",
        "SEMGREP_SETTINGS_FILE": str(home / "settings.yml"),
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SEND_METRICS": "off",
    }


SEMGREP_SCAN_ARGS = ("scan", "--metrics=off", "--disable-version-check", "--json", "--quiet")


def semgrep_matches(results: list[dict[str, Any]], formulas: dict[str, str]) -> list[SemgrepMatch]:
    """What the ``match_based_id`` port needs from Semgrep's JSON results."""
    return [
        SemgrepMatch(
            r["check_id"],
            r["path"],
            formulas.get(r["check_id"], ""),
            {k: v["abstract_content"] for k, v in r["extra"].get("metavars", {}).items()},
        )
        for r in results
    ]


def semgrep_formulas(rules_text: str) -> dict[str, str]:
    yaml = importlib.import_module("yaml")
    return {r["id"]: semgrep_formula_string(r) for r in yaml.safe_load(rules_text)["rules"]}


class SemgrepAnalyzer:
    name = "semgrep"

    def __init__(self, rules: Path = DEFAULT_SEMGREP_RULES) -> None:
        exe = shutil.which("semgrep")
        if exe is None:
            raise RuntimeError(
                "semgrep is not installed: "
                "pip install -r research/finding_identity/requirements.txt"
            )
        self._exe = exe
        self._rules_text = rules.read_text(encoding="utf-8")
        self._formulas = semgrep_formulas(self._rules_text)
        self._rules_path = rules
        self._work = Path(tempfile.mkdtemp(prefix="finding-identity-semgrep-"))
        weakref.finalize(self, shutil.rmtree, self._work, ignore_errors=True)
        # Rule IDs carry no directory prefix when the rules file sits in the working dir.
        (self._work / "rules.yml").write_text(self._rules_text, encoding="utf-8")
        # An empty .semgrepignore replaces Semgrep's default ignore list (tests/, etc.).
        (self._work / ".semgrepignore").write_text("", encoding="utf-8")
        self._env = semgrep_env(self._work)
        self.version = self._run_version()
        if self.version != SEMGREP_VERSION:
            warnings.warn(
                f"semgrep {self.version} installed; the harness pins {SEMGREP_VERSION}",
                stacklevel=2,
            )
        self.port_checked = 0
        self.port_mismatches = 0

    def _run_version(self) -> str:
        out = subprocess.run(
            [self._exe, "--version"], capture_output=True, text=True, env=self._env, check=True
        )
        return out.stdout.strip()

    def supports(self, path: str) -> bool:
        return language_for_path(path) is not None

    def run_json(self, path: str, text: str) -> dict[str, Any] | None:
        """Semgrep's JSON output for one file version, scanned at its repository path."""
        target = self._work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        try:
            proc = subprocess.run(
                [self._exe, *SEMGREP_SCAN_ARGS, "--config", "rules.yml", "--jobs", "1", path],
                cwd=self._work,
                env=self._env,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            target.unlink()
        if proc.returncode != 0:
            return None
        result: dict[str, Any] = json.loads(proc.stdout)
        return result

    def analyze(self, path: str, text: str) -> list[RawFinding] | None:
        output = self.run_json(path, text)
        if output is None:
            return None
        results = output["results"]
        ported = semgrep_match_based_ids(semgrep_matches(results, self._formulas))
        out = []
        for r, port_id in zip(results, ported, strict=True):
            extra = r["extra"]
            emitted = extra["fingerprint"]
            self.port_checked += 1
            if emitted != port_id:
                self.port_mismatches += 1
                print(
                    f"semgrep port mismatch: {path}:{r['start']['line']} {r['check_id']}",
                    file=sys.stderr,
                )
            meta = extra.get("metadata", {})
            out.append(
                RawFinding(
                    r["check_id"],
                    r["start"]["line"],
                    r["start"]["col"],
                    FindingMeta(
                        message=extra["message"],
                        severity=extra["severity"],
                        confidence=str(meta.get("confidence", "")),
                        cwe=str(meta.get("cwe", "")),
                        test=r["check_id"],
                        semgrep_id=emitted,
                    ),
                )
            )
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "version": self.version,
            "rules": str(self._rules_path),
            "rules_sha256": hashlib.sha256(self._rules_text.encode()).hexdigest(),
            "port_checked": self.port_checked,
            "port_mismatches": self.port_mismatches,
        }


def make_analyzer(name: str, *, rule_ids: list[str], semgrep_rules: Path | None = None) -> Analyzer:
    if name == "codeguard":
        return CodeGuardAnalyzer(rule_ids)
    if name == "bandit":
        return BanditAnalyzer()
    if name == "semgrep":
        return SemgrepAnalyzer(semgrep_rules or DEFAULT_SEMGREP_RULES)
    raise ValueError(f"unknown analyzer {name!r}")
