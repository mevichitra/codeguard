# SPDX-License-Identifier: Apache-2.0
"""Fixture tests for the 2.2 rule packs (security, performance, quality).

Each rule has ``vulnerable.*`` (must report exactly N findings) and ``safe.*``
(must report none).  Rules with an autofix also have ``fixed.*``: applying the
safe fixes to ``vulnerable.*`` must reproduce it byte for byte, and the result
must still parse.
"""

from __future__ import annotations

import pytest

from codeguard.engine.fixes import apply_fixes
from codeguard.engine.registry import REGISTRY
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.registry import language_for_path, support_for
from tests.conftest import fixture_path

# (language, category, fixture dir, rule id, findings in vulnerable.*)
CASES = [
    ("python", "security", "cg_sec_006", "CG-SEC-006", 3),
    ("python", "security", "cg_sec_007", "CG-SEC-007", 6),
    ("python", "security", "cg_sec_008", "CG-SEC-008", 2),
    ("python", "security", "cg_sec_009", "CG-SEC-009", 3),
    ("javascript", "security", "cg_sec_107", "CG-SEC-107", 2),
    ("javascript", "security", "cg_sec_108", "CG-SEC-108", 3),
    ("javascript", "security", "cg_sec_109", "CG-SEC-109", 3),
    ("javascript", "security", "cg_sec_110", "CG-SEC-110", 3),
    ("javascript", "security", "cg_sec_111", "CG-SEC-111", 2),
    ("python", "performance", "cg_perf_001", "CG-PERF-001", 3),
    ("python", "performance", "cg_perf_002", "CG-PERF-002", 2),
    ("python", "performance", "cg_perf_003", "CG-PERF-003", 1),
    ("python", "performance", "cg_perf_004", "CG-PERF-004", 3),
    ("python", "performance", "cg_perf_005", "CG-PERF-005", 2),
    ("javascript", "performance", "cg_perf_101", "CG-PERF-101", 2),
    ("javascript", "performance", "cg_perf_102", "CG-PERF-102", 1),
    ("javascript", "performance", "cg_perf_103", "CG-PERF-103", 2),
    ("javascript", "performance", "cg_perf_104", "CG-PERF-104", 1),
    ("javascript", "performance", "cg_perf_105", "CG-PERF-105", 1),
    ("python", "quality", "cg_qual_001", "CG-QUAL-001", 3),
    ("python", "quality", "cg_qual_002", "CG-QUAL-002", 2),
    ("python", "quality", "cg_qual_003", "CG-QUAL-003", 1),
    ("python", "quality", "cg_qual_004", "CG-QUAL-004", 1),
    ("python", "quality", "cg_qual_005", "CG-QUAL-005", 1),
    ("javascript", "quality", "cg_qual_101", "CG-QUAL-101", 3),
    ("javascript", "quality", "cg_qual_102", "CG-QUAL-102", 1),
    ("javascript", "quality", "cg_qual_103", "CG-QUAL-103", 1),
    ("javascript", "quality", "cg_qual_104", "CG-QUAL-104", 2),
]
AUTOFIX = [c for c in CASES if REGISTRY.get(c[3]) is not None and REGISTRY.get(c[3]).autofix]  # type: ignore[union-attr]


def _scan(lang: str, cat: str, d: str, rule: str, name: str) -> tuple[str, list]:  # type: ignore[type-arg]
    path = fixture_path(lang, cat, d, name)
    source = path.read_text(encoding="utf-8")
    findings = AnalysisRunner(rule_ids=[rule]).run(source, filename=str(path))
    return source, [f for f in findings if not f.suppressed]


@pytest.mark.parametrize(("lang", "cat", "d", "rule", "count"), CASES, ids=[c[3] for c in CASES])
def test_vulnerable(lang: str, cat: str, d: str, rule: str, count: int) -> None:
    _, findings = _scan(lang, cat, d, rule, "vulnerable")
    assert [f.rule_id for f in findings] == [rule] * count


@pytest.mark.parametrize(("lang", "cat", "d", "rule", "count"), CASES, ids=[c[3] for c in CASES])
def test_safe(lang: str, cat: str, d: str, rule: str, count: int) -> None:
    assert _scan(lang, cat, d, rule, "safe")[1] == []


@pytest.mark.parametrize(("lang", "cat", "d", "rule", "count"), CASES, ids=[c[3] for c in CASES])
def test_category_matches_directory(lang: str, cat: str, d: str, rule: str, count: int) -> None:
    registered = REGISTRY.get(rule)
    assert registered is not None
    assert registered.category.value == cat


@pytest.mark.parametrize(
    ("lang", "cat", "d", "rule", "count"), AUTOFIX, ids=[c[3] for c in AUTOFIX]
)
def test_autofix_matches_golden_file(lang: str, cat: str, d: str, rule: str, count: int) -> None:
    source, findings = _scan(lang, cat, d, rule, "vulnerable")
    result = apply_fixes(source, findings)
    expected = fixture_path(lang, cat, d, "fixed").read_text(encoding="utf-8")
    assert result.source == expected
    assert not result.skipped
    # The fixed file still parses, and every remaining finding is one without a fix.
    path = fixture_path(lang, cat, d, "fixed")
    lang_enum = language_for_path(path)
    assert lang_enum is not None
    assert support_for(lang_enum).parse(expected, str(path)).ok
    remaining = AnalysisRunner(rule_ids=[rule]).run(expected, filename=str(path))
    assert all(f.fix is None for f in remaining)


def test_every_autofix_rule_has_golden_case() -> None:
    covered = {c[3] for c in AUTOFIX}
    declared = {r.id for r in REGISTRY.all() if r.autofix}
    assert declared <= covered


def test_rule_option_changes_threshold() -> None:
    src = "def f(x):\n    if x:\n        return 1\n    return 2\n"
    runner = AnalysisRunner(
        rule_ids=["CG-QUAL-003"], rule_options={"CG-QUAL-003": {"max_complexity": 1}}
    )
    findings = runner.run(src, filename="m.py")
    assert len(findings) == 1
    assert "complexity 2 (limit 1)" in findings[0].description
    assert (findings[0].location.col, findings[0].location.end_col) == (1, 6)  # just `def f`


def test_min_elements_option() -> None:
    src = "for x in y:\n    if x in ['a', 'b']:\n        pass\n"
    assert AnalysisRunner(rule_ids=["CG-PERF-001"]).run(src, filename="m.py") == []
    runner = AnalysisRunner(
        rule_ids=["CG-PERF-001"], rule_options={"CG-PERF-001": {"min_elements": 2}}
    )
    assert len(runner.run(src, filename="m.py")) == 1


def test_secrets_import_not_duplicated_when_present() -> None:
    src = "import random\nimport secrets\napi_token = random.choice('ab')\n"
    (finding,) = AnalysisRunner(rule_ids=["CG-SEC-009"]).run(src, filename="m.py")
    assert finding.fix is not None and len(finding.fix.edits) == 1
    assert apply_fixes(src, [finding]).source.endswith("api_token = secrets.choice('ab')\n")


def test_secrets_alias_reused() -> None:
    src = "import random\nimport secrets as s\nreset_token = random.getrandbits(64)\n"
    (finding,) = AnalysisRunner(rule_ids=["CG-SEC-009"]).run(src, filename="m.py")
    assert apply_fixes(src, [finding]).source.endswith("reset_token = s.randbits(64)\n")


def test_import_inserted_after_docstring_without_trailing_newline() -> None:
    src = '"""doc"""\nimport random\nauth_token = random.choice("ab")'
    (finding,) = AnalysisRunner(rule_ids=["CG-SEC-009"]).run(src, filename="m.py")
    fixed = apply_fixes(src, [finding]).source
    assert fixed == '"""doc"""\nimport random\nimport secrets\nauth_token = secrets.choice("ab")'
