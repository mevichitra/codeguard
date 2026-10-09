# SPDX-License-Identifier: Apache-2.0
"""Apply autofix edits to source text.

Edits are positioned in 1-indexed lines and 1-indexed **UTF-8 byte** columns
(see :class:`~codeguard.engine.finding.TextEdit`), so they are applied to the
encoded bytes of the source.  That keeps them correct on lines that contain
non-ASCII text, and leaves line endings (``\\n`` or ``\\r\\n``) untouched.

The edits of one :class:`~codeguard.engine.finding.Fix` are applied
atomically: a fix whose edits overlap an already-accepted fix is skipped as a
whole and reported, never half-applied.
"""

from __future__ import annotations

import ast
import difflib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from codeguard.lang.node import SourceNode

from .finding import Finding, TextEdit


class EditConflictError(ValueError):
    """Two edits overlap, or an edit points outside the source."""


@dataclass(frozen=True)
class FixResult:
    """Outcome of :func:`apply_fixes`."""

    source: str
    applied: tuple[Finding, ...]
    skipped: tuple[Finding, ...]

    @property
    def changed(self) -> bool:
        return bool(self.applied)


# ---------------------------------------------------------------------------
# Building edits
# ---------------------------------------------------------------------------


def edit_for_ast_node(node: ast.AST, replacement: str) -> TextEdit:
    """A :class:`TextEdit` replacing the full span of an ``ast`` *node*."""
    line = getattr(node, "lineno", None)
    col = getattr(node, "col_offset", None)
    end_line = getattr(node, "end_lineno", None)
    end_col = getattr(node, "end_col_offset", None)
    if line is None or col is None or end_line is None or end_col is None:
        raise ValueError(f"{type(node).__name__} has no source span")
    return TextEdit(line, col + 1, end_line, end_col + 1, replacement)


def edit_for_source_node(node: SourceNode, replacement: str) -> TextEdit:
    """A :class:`TextEdit` replacing the full span of a :class:`SourceNode`."""
    end = node.end
    if end is None:
        raise ValueError(f"{node.kind} has no end position")
    return TextEdit(node.start.line, node.start.col, end.line, end.col, replacement)


def line_insert(line: int, text: str) -> TextEdit:
    """A zero-width insertion of *text* at the start of *line*."""
    return TextEdit(line, 1, line, 1, text)


# ---------------------------------------------------------------------------
# Applying edits
# ---------------------------------------------------------------------------


def _line_starts(data: bytes) -> list[int]:
    starts = [0]
    for i, byte in enumerate(data):
        if byte == 0x0A:  # \n
            starts.append(i + 1)
    return starts


def _offset(starts: list[int], size: int, line: int, col: int) -> int:
    if line < 1 or col < 1:
        raise EditConflictError(f"edit position {line}:{col} is not 1-indexed")
    if line > len(starts):
        # Allow inserting at the very end of a file that lacks a final newline.
        if line == len(starts) + 1 and col == 1:
            return size
        raise EditConflictError(f"edit line {line} is past the end of the source")
    offset = starts[line - 1] + col - 1
    line_end = starts[line] if line < len(starts) else size
    if offset > line_end:
        raise EditConflictError(f"edit column {col} is past the end of line {line}")
    return offset


def _spans(source_bytes: bytes, edits: Sequence[TextEdit]) -> list[tuple[int, int, int, str]]:
    starts = _line_starts(source_bytes)
    size = len(source_bytes)
    spans = []
    for order, e in enumerate(edits):
        start = _offset(starts, size, e.start_line, e.start_col)
        end = _offset(starts, size, e.end_line, e.end_col)
        if end < start:
            raise EditConflictError(f"edit ends before it starts: {e}")
        spans.append((start, end, order, e.replacement))
    return spans


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    (s1, e1), (s2, e2) = a, b
    if s1 == e1 and s2 == e2:  # two insertions never conflict
        return False
    if s1 == e1:  # insertion strictly inside a replacement
        return s2 < s1 < e2
    if s2 == e2:
        return s1 < s2 < e1
    return s1 < e2 and s2 < e1


def apply_edits(source: str, edits: Sequence[TextEdit]) -> str:
    """Apply *edits* to *source* and return the new text.

    Raises
    ------
    EditConflictError
        If two edits overlap or an edit is out of bounds.
    """
    data = source.encode("utf-8")
    spans = sorted(_spans(data, edits))
    for prev, cur in pairwise(spans):
        if _overlaps((prev[0], prev[1]), (cur[0], cur[1])):
            raise EditConflictError("overlapping edits")
    buf = bytearray(data)
    # Descending by start; equal-offset insertions keep their input order.
    for start, end, _order, text in sorted(spans, key=lambda s: (s[0], s[2]), reverse=True):
        buf[start:end] = text.encode("utf-8")
    return buf.decode("utf-8")


def _fixable(findings: Iterable[Finding], *, safe_only: bool) -> list[Finding]:
    return [
        f
        for f in findings
        if f.fix is not None
        and f.fix.edits
        and (f.fix.safe or not safe_only)
        and not f.suppressed
        and not f.baselined
    ]


def select_non_overlapping(
    source: str, findings: Iterable[Finding], *, safe_only: bool = True
) -> tuple[list[Finding], list[Finding]]:
    """Split fixable *findings* into ``(accepted, skipped)`` so accepted fixes never overlap.

    Fixes are considered in source order; a fix that collides with one already
    accepted (or is out of bounds) is skipped whole.
    """
    data = source.encode("utf-8")
    candidates: list[tuple[int, Finding, list[tuple[int, int]] | None]] = []
    for f in _fixable(findings, safe_only=safe_only):
        assert f.fix is not None
        try:
            spans = [(s, e) for s, e, _, _ in _spans(data, f.fix.edits)]
        except EditConflictError:
            candidates.append((len(data) + 1, f, None))
            continue
        candidates.append((min(s for s, _ in spans), f, spans))
    candidates.sort(key=lambda c: (c[0], c[1].rule_id, c[1].location.col))

    accepted: list[Finding] = []
    skipped: list[Finding] = []
    taken: list[tuple[int, int]] = []
    seen: set[tuple[tuple[int, int, int, int, str], ...]] = set()
    for _, finding, maybe_spans in candidates:
        if maybe_spans is None:
            skipped.append(finding)
            continue
        spans = maybe_spans
        assert finding.fix is not None
        key = tuple(
            (e.start_line, e.start_col, e.end_line, e.end_col, e.replacement)
            for e in finding.fix.edits
        )
        if key in seen:  # identical fix from a duplicate finding -- apply once
            accepted.append(finding)
            continue
        own_ok = all(not _overlaps(a, b) for i, a in enumerate(spans) for b in spans[i + 1 :])
        if not own_ok or any(_overlaps(s, t) for s in spans for t in taken):
            skipped.append(finding)
            continue
        seen.add(key)
        taken.extend(spans)
        accepted.append(finding)
    return accepted, skipped


def edits_for(findings: Iterable[Finding]) -> list[TextEdit]:
    """All edits of *findings*' fixes, de-duplicated, in input order."""
    out: list[TextEdit] = []
    seen: set[TextEdit] = set()
    for f in findings:
        if f.fix is None:
            continue
        for e in f.fix.edits:
            if e not in seen:
                seen.add(e)
                out.append(e)
    return out


def apply_fixes(source: str, findings: Iterable[Finding], *, safe_only: bool = True) -> FixResult:
    """Apply every non-overlapping fix in *findings* to *source*."""
    accepted, skipped = select_non_overlapping(source, findings, safe_only=safe_only)
    if not accepted:
        return FixResult(source, (), tuple(skipped))
    new_source = apply_edits(source, edits_for(accepted))
    return FixResult(new_source, tuple(accepted), tuple(skipped))


def unified_diff(path: str, before: str, after: str) -> str:
    """A ``git``-style unified diff of *before* -> *after*."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
