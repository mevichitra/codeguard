# SPDX-License-Identifier: Apache-2.0
"""What ``scan --baseline`` does with a finding when its file changes.

These tests pin the shipped behaviour of the ``codeguard/v1`` fingerprint and the
baseline's set-membership comparison, including the cases the finding-identity study
(``research/finding_identity``) measured as failures. The failures are marked ``xfail``
with the behaviour the next scheme (``codeguard/v2``, ``docs/design/finding-identity-v2.md``)
has to fix; the passes pin what it must keep.
"""

from __future__ import annotations

import ast
import textwrap

import pytest

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
# Set membership: one baselined fingerprint hides any number of equal findings
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


@pytest.mark.xfail(
    reason="v1 compares by set membership: one baselined fingerprint hides every equal "
    "finding. v2 pairs findings one to one, so the second copy is new.",
    strict=True,
)
def test_second_equal_statement_is_reported_as_new() -> None:
    before = _scan(f"def handler(data, other):\n    out = {EVAL}(data)\n    return out\n")
    after = _scan(TWIN)
    assert len(_new(after, before)) == 1


@pytest.mark.xfail(
    reason="A copy of a baselined statement pasted above it has the same fingerprint, so "
    "the baseline hides it (RQ2 duplicate_above: 100% hidden). v2 must report one of the "
    "two as new, and prefer reporting the copy.",
    strict=True,
)
def test_copy_pasted_above_a_baselined_finding_is_new() -> None:
    before = _scan(f"def handler(data):\n    out = {EVAL}(data)\n    return out\n")
    after = _scan(TWIN)
    assert len(after) == 2
    assert len(_new(after, before)) == 1


# ---------------------------------------------------------------------------
# The path inside the key: a rename loses every finding
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="The relative path is part of the v1 key, so a renamed file reports all of its "
    "findings as new (RQ1: 287 of 287, 69% of codeguard's false-new reports). v2 keeps "
    "the path out of the key and pairs files across renames.",
    strict=True,
)
def test_renamed_file_keeps_its_findings() -> None:
    before = _scan(ONE, "pkg/old_name.py")
    after = _scan(ONE, "pkg/new_name.py")
    assert _new(after, before) == []


def test_same_statement_in_two_files_has_two_fingerprints() -> None:
    # The path keeps two files apart today; v2 has to keep them apart another way.
    a = _scan(ONE, "pkg/a.py")
    b = _scan(ONE, "pkg/b.py")
    assert a[0].fingerprint != b[0].fingerprint


# ---------------------------------------------------------------------------
# The scope inside the key: renaming or extracting the function loses the finding
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="The enclosing function's name is part of the v1 key (RQ2 rename_function: "
    "100% false new). v2 falls back on a scope-free key.",
    strict=True,
)
def test_renamed_enclosing_function_keeps_the_finding() -> None:
    before = _scan(ONE)
    after = _scan(f"def handle_request(data):\n    return {EVAL}(data)\n")
    assert _new(after, before) == []


@pytest.mark.xfail(
    reason="Extracting the statement into a helper changes its scope (RQ2 extract_helper: "
    "100% false new). v2 falls back on a scope-free key.",
    strict=True,
)
def test_statement_extracted_into_a_helper_keeps_the_finding() -> None:
    before = _scan(ONE)
    after = _scan(
        f"def _run(data):\n    return {EVAL}(data)\n\n\ndef handler(data):\n    return _run(data)\n"
    )
    assert _new(after, before) == []


@pytest.mark.xfail(
    reason="Renaming a local used on the flagged line changes the normalized statement "
    "(RQ2 rename_local: 97.9% false new). v2 falls back on an identifier-masked key.",
    strict=True,
)
def test_renamed_local_variable_keeps_the_finding() -> None:
    before = _scan(f"def h(req):\n    data = req.body\n    return {EVAL}(data)\n")
    after = _scan(f"def h(req):\n    payload = req.body\n    return {EVAL}(payload)\n")
    assert _new(after, before) == []


@pytest.mark.xfail(
    reason="An edited flagged line gets a new fingerprint (RQ1: 74.8% of persisting "
    "findings on edited lines reported as new). v2 pairs unmatched findings of one rule "
    "by statement similarity.",
    strict=True,
)
def test_edited_flagged_line_keeps_the_finding() -> None:
    before = _scan(f"def h(data):\n    return {EVAL}(data)\n")
    after = _scan(f"def h(data):\n    return {EVAL}(data.strip())\n")
    assert _new(after, before) == []


# ---------------------------------------------------------------------------
# JavaScript and TypeScript findings get no scope at all
# ---------------------------------------------------------------------------


def test_javascript_findings_have_no_scope() -> None:
    js = f"function handler(data) {{\n  return {EVAL}(data);\n}}\n"
    [finding] = _scan(js, "src/app.js")
    assert finding.fingerprint == fp.compute(
        "CG-SEC-101", "src/app.js", js, finding.location.line, scope=""
    )


def test_python_scope_is_the_dotted_enclosing_name() -> None:
    src = "class View:\n    def get(self, request):\n        data = 1\n"
    assert fp.python_scope(ast.parse(src), 3) == "View.get"
