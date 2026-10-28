# SPDX-License-Identifier: Apache-2.0
"""What ``scan --baseline`` does with a finding when its file changes.

These tests pin the behaviour of the baseline comparison through the real runner and
``apply_baseline``: what the ``codeguard/v1`` fingerprint already got right, and the
cases the finding-identity study (``research/finding_identity``) measured as failures
of v1, which ``codeguard/v2`` (``docs/design/finding-identity-v2.md``) fixes: one
record hides one finding, a pasted copy is reported, and a finding survives a renamed
file, a renamed or extracted enclosing function, a renamed local and an edited line.
"""

from __future__ import annotations

import ast
import textwrap

import codeguard.rules  # noqa: F401  (registers rules)
from codeguard.engine import fingerprint as fp
from codeguard.engine.baseline import Baseline, apply_baseline
from codeguard.engine.finding import Finding
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language

EVAL = "ev" + "al"  # keeps the dynamic-code rule from firing on this file


def _scan(source: str, filename: str = "pkg/mod.py") -> list[Finding]:
    lang = Language.PYTHON if filename.endswith(".py") else Language.JAVASCRIPT
    runner = AnalysisRunner(rule_ids=["CG-SEC-003", "CG-SEC-101"])
    return runner.run(textwrap.dedent(source), filename=filename, language=lang)


def _new(after: list[Finding], before: list[Finding]) -> list[Finding]:
    """The findings of *after* that ``scan --baseline`` would report as new."""
    baseline = Baseline.from_findings(before)
    return [f for f in apply_baseline(after, baseline) if not f.baselined]


ONE = f"""
    def handler(data):
        return {EVAL}(data)
    """


# ---------------------------------------------------------------------------
# What v1 gets right and v2 must keep
# ---------------------------------------------------------------------------


def test_reformatted_file_keeps_its_fingerprint() -> None:
    before = _scan(f"def handler(data):\n    return {EVAL}( data )\n")
    after = _scan(f'"""Doc."""\n\n\ndef handler(data):\n    return {EVAL}(data)  # noqa\n')
    assert len(before) == len(after) == 1
    assert before[0].fingerprint == after[0].fingerprint
    assert _new(after, before) == []


def test_lines_inserted_above_keep_the_fingerprint() -> None:
    before = _scan(ONE)
    after = _scan("import os\nimport sys\n\n" + textwrap.dedent(ONE))
    assert after[0].location.line != before[0].location.line
    assert _new(after, before) == []


def test_changed_literals_keep_the_fingerprint() -> None:
    before = _scan(f"def h():\n    return {EVAL}('x' + str(1))\n")
    after = _scan(f"def h():\n    return {EVAL}('y_v2' + str(2))\n")
    assert _new(after, before) == []


def test_renamed_statement_is_new() -> None:
    before = _scan(f"def h(a):\n    return {EVAL}(a)\n")
    after = _scan(f"def h(a, b):\n    return {EVAL}(b)\n")
    assert len(_new(after, before)) == 1


# ---------------------------------------------------------------------------
# One record hides one finding (v1 compared by set membership)
# ---------------------------------------------------------------------------

TWIN = f"""
    def handler(data, other):
        out = {EVAL}(data)
        out = {EVAL}(data)
        return out
    """


def test_equal_statements_in_one_scope_share_a_fingerprint() -> None:
    findings = _scan(TWIN)
    assert len(findings) == 2
    assert findings[0].fingerprint == findings[1].fingerprint


def test_second_equal_statement_is_reported_as_new() -> None:
    before = _scan(f"def handler(data, other):\n    out = {EVAL}(data)\n    return out\n")
    after = _scan(TWIN)
    assert len(_new(after, before)) == 1


def test_copy_pasted_above_a_baselined_finding_is_new() -> None:
    before = _scan(f"def handler(data):\n    out = {EVAL}(data)\n    return out\n")
    after = _scan(TWIN)
    assert len(after) == 2
    [new] = _new(after, before)
    # The copy above is reported, not the original, which kept its following line.
    assert new.location.line == min(f.location.line for f in after)


# ---------------------------------------------------------------------------
# The path is not in the key: a renamed file keeps its findings
# ---------------------------------------------------------------------------


def test_renamed_file_keeps_its_findings() -> None:
    # No SCM here to report the rename: the two files are paired by content.
    before = _scan(ONE, "pkg/old_name.py")
    after = _scan(ONE, "pkg/new_name.py")
    assert _new(after, before) == []


def test_same_statement_in_two_files_has_two_fingerprints() -> None:
    # The path keeps two files apart today; v2 has to keep them apart another way.
    a = _scan(ONE, "pkg/a.py")
    b = _scan(ONE, "pkg/b.py")
    assert a[0].fingerprint != b[0].fingerprint


# ---------------------------------------------------------------------------
# Scope, identifier and edit fallbacks
# ---------------------------------------------------------------------------


def test_renamed_enclosing_function_keeps_the_finding() -> None:
    before = _scan(ONE)
    after = _scan(f"def handle_request(data):\n    return {EVAL}(data)\n")
    assert _new(after, before) == []


def test_statement_extracted_into_a_helper_keeps_the_finding() -> None:
    before = _scan(ONE)
    after = _scan(
        f"def _run(data):\n    return {EVAL}(data)\n\n\ndef handler(data):\n    return _run(data)\n"
    )
    assert _new(after, before) == []


def test_renamed_local_variable_keeps_the_finding() -> None:
    before = _scan(f"def h(req):\n    data = req.body\n    return {EVAL}(data)\n")
    after = _scan(f"def h(req):\n    payload = req.body\n    return {EVAL}(payload)\n")
    assert _new(after, before) == []


def test_edited_flagged_line_keeps_the_finding() -> None:
    before = _scan(f"def h(data):\n    return {EVAL}(data)\n")
    after = _scan(f"def h(data):\n    return {EVAL}(data.strip())\n")
    assert _new(after, before) == []


# ---------------------------------------------------------------------------
# JavaScript and TypeScript: v1 had no scope, v2 has one
# ---------------------------------------------------------------------------


def test_javascript_v1_fingerprint_has_no_scope() -> None:
    js = f"function handler(data) {{\n  return {EVAL}(data);\n}}\n"
    [finding] = _scan(js, "src/app.js")
    assert finding.fingerprint == fp.compute(
        "CG-SEC-101", "src/app.js", js, finding.location.line, scope=""
    )
    assert finding.identity is not None and finding.identity.scope == "handler"


def test_javascript_renamed_function_keeps_the_finding() -> None:
    before = _scan(f"function handler(data) {{\n  return {EVAL}(data);\n}}\n", "src/app.js")
    after = _scan(f"function handle(data) {{\n  return {EVAL}(data);\n}}\n", "src/app.js")
    assert _new(after, before) == []


def test_python_scope_is_the_dotted_enclosing_name() -> None:
    src = "class View:\n    def get(self, request):\n        data = 1\n"
    assert fp.python_scope(ast.parse(src), 3) == "View.get"
