# SPDX-License-Identifier: Apache-2.0

"""Semgrep with a rules repository: installing the rules and scanning in batches."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from research.finding_identity.analyzers import (
    DEFAULT_SEMGREP_RULES,
    SEMGREP_RULES_ROOT,
    SemgrepAnalyzer,
    install_semgrep_rules,
    semgrep_kind,
)
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import ALL_SCHEMES

needs_semgrep = pytest.mark.skipif(shutil.which("semgrep") is None, reason="semgrep not installed")

RULE = """rules:
  - id: {id}
    languages: [{lang}]
    severity: WARNING
    message: {id} found
    pattern: eval(...)
"""


def _rules_repo(root: Path) -> Path:
    """A tiny checkout in the semgrep-rules layout, with files the install must skip."""
    for rel, rule_id, lang in (
        ("python/lang/security/eval.yaml", "eval-py", "python"),
        ("javascript/lang/eval.yml", "eval-js", "javascript"),
        ("typescript/lang/eval.yaml", "eval-ts", "typescript"),
        ("generic/secrets/key.yaml", "generic-key", "generic"),
    ):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(RULE.format(id=rule_id, lang=lang))
    (root / "python" / "lang" / "security" / "eval.py").write_text("eval(x)\n")
    (root / "python" / "lang" / "security" / "eval.test.yaml").write_text("a: 1\n")
    (root / "python" / "metadata.yaml").write_text("not_rules: []\n")
    return root


def test_install_reads_the_rules_repository_layout(tmp_path: Path) -> None:
    rules = install_semgrep_rules(_rules_repo(tmp_path / "repo"), tmp_path / "work")
    assert rules.configs == {
        "python": (f"{SEMGREP_RULES_ROOT}/python",),
        "javascript": (f"{SEMGREP_RULES_ROOT}/javascript", f"{SEMGREP_RULES_ROOT}/typescript"),
    }
    # Semgrep's rule IDs: the rule file's directory, dotted, then the rule's own ID.
    assert set(rules.formulas) == {
        f"{SEMGREP_RULES_ROOT}.python.lang.security.eval-py",
        f"{SEMGREP_RULES_ROOT}.javascript.lang.eval-js",
        f"{SEMGREP_RULES_ROOT}.typescript.lang.eval-ts",
    }
    assert set(rules.formulas.values()) == {"eval(...)"}
    assert rules.info["rule_files"] == 3 and rules.info["rule_files_skipped"] == 1
    assert rules.info["rules_commit"] is None  # not a git checkout
    assert not (tmp_path / "work" / SEMGREP_RULES_ROOT / "generic").exists()
    # The digest depends on the rules, not on where they were installed.
    again = install_semgrep_rules(tmp_path / "repo", tmp_path / "work2")
    assert again.info["rules_sha256"] == rules.info["rules_sha256"]


def test_install_keeps_a_single_rules_file_unprefixed(tmp_path: Path) -> None:
    rules = install_semgrep_rules(DEFAULT_SEMGREP_RULES, tmp_path)
    assert rules.prefix == "" and set(rules.configs.values()) == {("rules.yml",)}
    assert (tmp_path / "rules.yml").read_text() == DEFAULT_SEMGREP_RULES.read_text()


def test_kind_groups_typescript_with_javascript() -> None:
    assert [semgrep_kind(p) for p in ("a.py", "b.js", "c.ts", "d.tsx")] == [
        "python",
        "javascript",
        "javascript",
        "javascript",
    ]


def test_prefetch_is_a_no_op_for_other_analyzers() -> None:
    def versions() -> Iterator[tuple[str, str, bytes]]:
        raise AssertionError("read the versions")
        yield ("", "", b"")

    Scanner(["CG-SEC-003"], ALL_SCHEMES).prefetch(versions())


PY_V1 = "def f(cmd):\n    eval(cmd)\n    eval(cmd)\n"
PY_V2 = "def f(cmd):\n    x = 1\n    eval(cmd)\n    eval(cmd)\n    eval(x)\n"
JS_V1 = "function f(a) { eval(a); }\n"


@needs_semgrep
def test_prefetch_gives_the_results_of_single_file_scans(tmp_path: Path) -> None:
    # The study's rules, in the layout of a rules repository.
    repo = tmp_path / "repo"
    for lang in ("python", "javascript"):
        (repo / lang).mkdir(parents=True)
        shutil.copy(DEFAULT_SEMGREP_RULES, repo / lang / "rules.yaml")
    versions = [("app/v.py", PY_V1), ("app/v.py", PY_V2), ("app/w.js", JS_V1), ("lib/u.py", PY_V2)]

    alone = SemgrepAnalyzer(repo)
    expected = [alone.analyze(path, text) for path, text in versions]
    assert alone.describe()["semgrep_calls"] == len(versions)

    batched = SemgrepAnalyzer(repo)
    batched.prefetch(versions)
    # Two layers of Python files (two versions of app/v.py) and one of JavaScript.
    assert batched.describe()["semgrep_calls"] == 3
    got = [batched.analyze(path, text) for path, text in versions]
    assert batched.describe()["semgrep_calls"] == 3  # nothing scanned again
    assert got == expected
    assert all(findings for findings in got)
    rules = {f.rule for findings in got if findings for f in findings}
    assert all(not r.startswith(SEMGREP_RULES_ROOT) for r in rules)
    described = batched.describe()
    assert described["port_mismatches"] == 0 and described["prefetched_versions"] == 4
