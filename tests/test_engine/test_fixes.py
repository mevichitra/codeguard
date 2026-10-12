# SPDX-License-Identifier: Apache-2.0
"""Tests for the autofix edit engine."""

from __future__ import annotations

import ast

import pytest

from codeguard.engine.finding import Category, Finding, Fix, Location, Severity, TextEdit
from codeguard.engine.fixes import (
    EditConflictError,
    apply_edits,
    apply_fixes,
    edit_for_ast_node,
    line_insert,
    select_non_overlapping,
    unified_diff,
)


def _finding(
    edits: tuple[TextEdit, ...], *, safe: bool = True, line: int = 1, **kw: object
) -> Finding:
    return Finding(
        rule_id=str(kw.pop("rule_id", "CG-TEST-001")),
        title="t",
        description="d",
        severity=Severity.LOW,
        category=Category.PERFORMANCE,
        location=Location("f.py", line, 1),
        fix=Fix("fix it", edits, safe=safe),
        **kw,  # type: ignore[arg-type]
    )


class TestApplyEdits:
    def test_single_replacement(self) -> None:
        assert apply_edits("a = b\n", [TextEdit(1, 5, 1, 6, "c")]) == "a = c\n"

    def test_multiple_edits_applied_right_to_left(self) -> None:
        src = "x in [1, 2]\ny in [3]\n"
        edits = [TextEdit(1, 6, 1, 12, "{1, 2}"), TextEdit(2, 6, 2, 9, "{3}")]
        assert apply_edits(src, edits) == "x in {1, 2}\ny in {3}\n"

    def test_insertion(self) -> None:
        assert apply_edits("a\nb\n", [line_insert(2, "import x\n")]) == "a\nimport x\nb\n"

    def test_insert_at_end_without_trailing_newline(self) -> None:
        assert apply_edits("a", [line_insert(2, "\nb")]) == "a\nb"

    def test_columns_are_utf8_bytes(self) -> None:
        # "é" is two bytes; ast reports byte offsets, so the edit targets bytes.
        src = 's = "é"; t = d.keys()\n'
        tree = ast.parse(src)
        call = tree.body[1].value  # type: ignore[attr-defined]
        assert apply_edits(src, [edit_for_ast_node(call, "d")]) == 's = "é"; t = d\n'

    def test_crlf_preserved(self) -> None:
        assert apply_edits("a = b\r\nc\r\n", [TextEdit(1, 5, 1, 6, "z")]) == "a = z\r\nc\r\n"

    def test_overlap_raises(self) -> None:
        with pytest.raises(EditConflictError):
            apply_edits("abcdef", [TextEdit(1, 1, 1, 4, "x"), TextEdit(1, 3, 1, 5, "y")])

    def test_out_of_bounds_raises(self) -> None:
        with pytest.raises(EditConflictError):
            apply_edits("abc\n", [TextEdit(5, 1, 5, 2, "x")])
        with pytest.raises(EditConflictError):
            apply_edits("abc\n", [TextEdit(1, 10, 1, 11, "x")])

    def test_inverted_edit_raises(self) -> None:
        with pytest.raises(EditConflictError):
            apply_edits("abc\n", [TextEdit(1, 3, 1, 1, "x")])

    def test_two_insertions_at_same_point_keep_order(self) -> None:
        out = apply_edits("b\n", [line_insert(1, "1"), line_insert(1, "2")])
        assert out == "12b\n"


class TestApplyFixes:
    def test_overlapping_fix_skipped_whole(self) -> None:
        a = _finding((TextEdit(1, 1, 1, 4, "AAA"),), rule_id="CG-A")
        b = _finding((TextEdit(1, 3, 1, 6, "BBB"), TextEdit(2, 1, 2, 2, "Z")), rule_id="CG-B")
        result = apply_fixes("abcdef\nq\n", [a, b])
        assert result.source == "AAAdef\nq\n"  # b's second edit NOT applied
        assert result.applied == (a,)
        assert result.skipped == (b,)

    def test_unsafe_fix_ignored_by_default(self) -> None:
        f = _finding((TextEdit(1, 1, 1, 2, "z"),), safe=False)
        assert apply_fixes("a\n", [f]).source == "a\n"
        assert apply_fixes("a\n", [f], safe_only=False).source == "z\n"

    def test_suppressed_and_baselined_not_fixed(self) -> None:
        f = _finding((TextEdit(1, 1, 1, 2, "z"),)).as_suppressed()
        g = _finding((TextEdit(1, 1, 1, 2, "z"),)).as_baselined()
        assert not apply_fixes("a\n", [f, g]).changed

    def test_identical_fixes_applied_once(self) -> None:
        edit = (line_insert(1, "import secrets\n"),)
        a, b = _finding(edit), _finding(edit, line=3)
        accepted, skipped = select_non_overlapping("x\n", [a, b])
        assert len(accepted) == 2 and not skipped
        assert apply_fixes("x\n", [a, b]).source == "import secrets\nx\n"

    def test_out_of_bounds_fix_skipped(self) -> None:
        f = _finding((TextEdit(9, 1, 9, 2, "z"),))
        result = apply_fixes("a\n", [f])
        assert result.skipped == (f,) and not result.changed


def test_unified_diff() -> None:
    diff = unified_diff("p.py", "a\n", "b\n")
    assert diff.startswith("--- a/p.py\n+++ b/p.py\n")
    assert "-a\n+b\n" in diff
