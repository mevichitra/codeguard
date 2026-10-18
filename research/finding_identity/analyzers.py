"""Analyzers that produce the findings the harness tracks: CodeGuard, Bandit or Semgrep.

Each analyzer takes one file version and returns its findings as :class:`RawFinding`
(rule, line, column and the fields some identity schemes compare). Bandit and Semgrep are
research-only dependencies (``requirements.txt``) and are imported when first used.

- ``codeguard`` runs CodeGuard's ``AnalysisRunner`` in process.
- ``bandit`` runs Bandit 1.9.4 in process, through the same ``BanditManager`` code path as
  the command line (``_parse_file``, then ``get_issue_list``). Python files only.
- ``semgrep`` runs the Semgrep 1.180.0 command line with local rules, with metrics,
  version checks and registry access off, so runs are offline and pinned. The rules are
  either one file (by default ``semgrep_rules.yml``, written for this study) or a
  checkout of a rules repository in the layout of ``semgrep/semgrep-rules`` (one
  directory per language), such as the LGPL-2.1 ``opengrep/opengrep-rules``: Python
  files are then scanned with ``python/``, JavaScript and TypeScript files with
  ``javascript/`` and ``typescript/``. Loading a rules repository takes Semgrep more than
  ten seconds, so a replay first hands :meth:`SemgrepAnalyzer.prefetch` every file
  version it will need, which scans them in a few calls instead of one per version.
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
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language
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


def _first_offset(value: Any) -> int | None:
    """The start offset of the first location in a ``dataflow_trace`` source."""
    if isinstance(value, dict):
        start = value.get("start")
        if isinstance(start, dict) and isinstance(start.get("offset"), int):
            return int(start["offset"])
        value = list(value.values())
    if isinstance(value, list):
        for item in value:
            found = _first_offset(item)
            if found is not None:
                return found
    return None


def semgrep_matches(results: list[dict[str, Any]], formulas: dict[str, str]) -> list[SemgrepMatch]:
    """What the ``match_based_id`` port needs from Semgrep's JSON results."""
    return [
        SemgrepMatch(
            r["check_id"],
            r["path"],
            formulas.get(r["check_id"], ""),
            {k: v["abstract_content"] for k, v in r["extra"].get("metavars", {}).items()},
            start=r.get("start", {}).get("offset"),
            end=r.get("end", {}).get("offset"),
            message=r["extra"].get("message", ""),
            taint_source=_first_offset(
                (r["extra"].get("dataflow_trace") or {}).get("taint_source")
            ),
        )
        for r in results
    ]


def semgrep_formulas(rules_text: str) -> dict[str, str]:
    yaml = importlib.import_module("yaml")
    return {r["id"]: semgrep_formula_string(r) for r in yaml.safe_load(rules_text)["rules"]}


#: Directories of a rules repository (``semgrep/semgrep-rules`` layout) that each kind of
#: file is scanned with; see :func:`semgrep_kind`.
SEMGREP_RULE_DIRS = {"python": ("python",), "javascript": ("javascript", "typescript")}
#: Where a rules repository's rules are copied, inside the scan directory. Semgrep prefixes
#: each rule ID with the rule file's directory relative to the scan directory, so copying
#: keeps the IDs, and so ``match_based_id``, independent of where the checkout lives. The
#: harness records rule IDs without this prefix.
SEMGREP_RULES_ROOT = "_semgrep_rules"


def semgrep_kind(path: str) -> str:
    """Which rules scan *path*: ``python``, or ``javascript`` for JavaScript and TypeScript."""
    return "python" if language_for_path(path) is Language.PYTHON else "javascript"


def _version_key(path: str, text: str) -> tuple[str, str]:
    return path, hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SemgrepRuleSet:
    """Rules installed in a scan directory."""

    #: Per kind of file, the ``--config`` paths, relative to the scan directory.
    configs: dict[str, tuple[str, ...]]
    #: ``{rule ID as Semgrep reports it: formula string}``, for the ``match_based_id`` port.
    formulas: dict[str, str]
    #: Removed from the front of Semgrep's rule IDs.
    prefix: str
    #: What :meth:`SemgrepAnalyzer.describe` reports about the rules.
    info: dict[str, Any]


def _checkout_commit(directory: Path) -> str | None:
    """The commit checked out in *directory*, if it is the root of a git checkout."""
    if not (directory / ".git").exists():
        return None
    proc = subprocess.run(
        ["git", "-C", str(directory), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() or None if proc.returncode == 0 else None


def install_semgrep_rules(source: Path, work: Path) -> SemgrepRuleSet:
    """Copy the rules at *source*, a rules file or a rules repository, into *work*.

    A directory with ``python/``, ``javascript/`` or ``typescript/`` is read in the
    ``semgrep/semgrep-rules`` layout (other directories, such as ``generic/``, are left
    out); any other directory is used whole for every file. Files that are not rule files
    (no top-level ``rules`` list) and test targets (``*.test.yaml``) are skipped.
    """
    if source.is_file():
        text = source.read_text(encoding="utf-8")
        # Rule IDs carry no directory prefix when the rules file sits in the scan directory.
        (work / "rules.yml").write_text(text, encoding="utf-8")
        single = semgrep_formulas(text)
        return SemgrepRuleSet(
            configs=dict.fromkeys(SEMGREP_RULE_DIRS, ("rules.yml",)),
            formulas=single,
            prefix="",
            info={
                "rules": str(source),
                "rules_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "rule_count": len(single),
            },
        )
    yaml = importlib.import_module("yaml")
    wanted = sorted({d for dirs in SEMGREP_RULE_DIRS.values() for d in dirs})
    layout = any((source / d).is_dir() for d in wanted)
    digest = hashlib.sha256()
    formulas: dict[str, str] = {}
    files = skipped = 0
    for top in wanted if layout else [""]:
        if not (source / top).is_dir():
            continue
        for f in sorted((source / top).rglob("*")):
            if f.suffix not in (".yaml", ".yml") or f.name.endswith((".test.yaml", ".test.yml")):
                continue
            raw = f.read_bytes()
            try:
                body = yaml.safe_load(raw)
            except yaml.YAMLError:
                body = None
            if not isinstance(body, dict) or not isinstance(body.get("rules"), list):
                skipped += 1
                continue
            rel = f.relative_to(source)
            target = work / SEMGREP_RULES_ROOT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            digest.update(rel.as_posix().encode() + b"\0" + raw + b"\0")
            files += 1
            prefix = ".".join((SEMGREP_RULES_ROOT, *rel.parent.parts))
            for rule in body["rules"]:
                if isinstance(rule, dict) and "id" in rule:
                    formulas[f"{prefix}.{rule['id']}"] = semgrep_formula_string(rule)
    if not files:
        raise ValueError(f"no Semgrep rule files under {source}")
    configs: dict[str, tuple[str, ...]] = {
        kind: (
            tuple(f"{SEMGREP_RULES_ROOT}/{d}" for d in dirs if (source / d).is_dir())
            if layout
            else (SEMGREP_RULES_ROOT,)
        )
        for kind, dirs in SEMGREP_RULE_DIRS.items()
    }
    return SemgrepRuleSet(
        configs=configs,
        formulas=formulas,
        prefix=SEMGREP_RULES_ROOT + ".",
        info={
            "rules": str(source),
            "rules_commit": _checkout_commit(source),
            "rules_sha256": digest.hexdigest(),
            "rule_dirs": {kind: list(c) for kind, c in configs.items()},
            "rule_files": files,
            "rule_files_skipped": skipped,
            "rule_count": len(formulas),
        },
    )


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
        self._work = Path(tempfile.mkdtemp(prefix="finding-identity-semgrep-"))
        weakref.finalize(self, shutil.rmtree, self._work, ignore_errors=True)
        self._rules = install_semgrep_rules(rules, self._work)
        self._formulas = self._rules.formulas
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
        self.calls = 0
        self.prefetched = 0
        self.failed_batches = 0
        #: Errors Semgrep reported (timeouts, unparsable code, ...), by type.
        self.errors: dict[str, int] = {}
        #: Results of prefetched versions, by path and SHA-256 of the text.
        self._prefetched: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def _run_version(self) -> str:
        out = subprocess.run(
            [self._exe, "--version"], capture_output=True, text=True, env=self._env, check=True
        )
        return out.stdout.strip()

    def supports(self, path: str) -> bool:
        return language_for_path(path) is not None

    def _write(self, path: str, text: str) -> Path:
        target = self._work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        return target

    def _scan(self, kind: str, paths: Sequence[str]) -> dict[str, Any] | None:
        """One Semgrep call on *paths*, already written under the scan directory."""
        configs = [arg for c in self._rules.configs[kind] for arg in ("--config", c)]
        self.calls += 1
        proc = subprocess.run(
            [self._exe, *SEMGREP_SCAN_ARGS, *configs, "--jobs", "1", *paths],
            cwd=self._work,
            env=self._env,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return None
        result: dict[str, Any] = json.loads(proc.stdout)
        for error in result.get("errors", []):
            kind_of = error.get("type", "unknown")
            name = kind_of if isinstance(kind_of, str) else str(kind_of[0])
            self.errors[name] = self.errors.get(name, 0) + 1
        return result

    def run_json(self, path: str, text: str) -> dict[str, Any] | None:
        """Semgrep's JSON output for one file version, scanned at its repository path."""
        target = self._write(path, text)
        try:
            return self._scan(semgrep_kind(path), [path])
        finally:
            target.unlink()

    def prefetch(self, versions: Sequence[tuple[str, str]]) -> None:
        """Scan many ``(path, text)`` versions in a few calls, for :meth:`analyze` to use.

        The versions are scanned in layers. A layer holds one kind of file and at most one
        version of each path, so every file is scanned at its own path with the rules it
        gets alone; Semgrep reports the same results for a file whether it is scanned alone
        or with others. A layer whose call fails is left to :meth:`analyze`, which then
        scans those versions one at a time.
        """
        layers: dict[tuple[str, int], dict[str, str]] = {}
        depth: dict[str, int] = {}
        seen = set(self._prefetched)
        for path, text in versions:
            key = _version_key(path, text)
            if key in seen:
                continue
            seen.add(key)
            d = depth.get(path, 0)
            depth[path] = d + 1
            layers.setdefault((semgrep_kind(path), d), {})[path] = text
        for n, ((kind, _), files) in enumerate(sorted(layers.items()), start=1):
            targets = [self._write(path, text) for path, text in files.items()]
            try:
                output = self._scan(kind, list(files))
            finally:
                for target in targets:
                    target.unlink()
            if output is None:
                self.failed_batches += 1
                continue
            by_path: dict[str, list[dict[str, Any]]] = {path: [] for path in files}
            for r in output["results"]:
                by_path.setdefault(r["path"], []).append(r)
            for path, text in files.items():
                self._prefetched[_version_key(path, text)] = by_path[path]
            self.prefetched += len(files)
            print(
                f"semgrep prefetch: layer {n}/{len(layers)}, {len(files)} {kind} files",
                file=sys.stderr,
            )

    def analyze(self, path: str, text: str) -> list[RawFinding] | None:
        results = self._prefetched.pop(_version_key(path, text), None)
        if results is None:
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
            rule = r["check_id"].removeprefix(self._rules.prefix)
            out.append(
                RawFinding(
                    rule,
                    r["start"]["line"],
                    r["start"]["col"],
                    FindingMeta(
                        message=extra["message"],
                        severity=extra["severity"],
                        confidence=str(meta.get("confidence", "")),
                        cwe=str(meta.get("cwe", "")),
                        test=rule,
                        semgrep_id=emitted,
                    ),
                )
            )
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "analyzer": self.name,
            "version": self.version,
            **self._rules.info,
            "port_checked": self.port_checked,
            "port_mismatches": self.port_mismatches,
            "semgrep_calls": self.calls,
            "prefetched_versions": self.prefetched,
            "failed_batches": self.failed_batches,
            "scan_errors": dict(sorted(self.errors.items())),
        }


def make_analyzer(name: str, *, rule_ids: list[str], semgrep_rules: Path | None = None) -> Analyzer:
    if name == "codeguard":
        return CodeGuardAnalyzer(rule_ids)
    if name == "bandit":
        return BanditAnalyzer()
    if name == "semgrep":
        return SemgrepAnalyzer(semgrep_rules or DEFAULT_SEMGREP_RULES)
    raise ValueError(f"unknown analyzer {name!r}")
