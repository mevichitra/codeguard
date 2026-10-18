"""Map lines of an old file version to lines of the new version (the ground truth).

Three kinds of mapping, decided in this order:

``equal``
    Lines the line diff (:mod:`difflib`) keeps unchanged.
``edited``
    Inside a replaced block, old and new lines paired when they are similar enough: an
    order-preserving alignment that maximizes total similarity, counting only pairs at or
    above the threshold. Blocks up to :data:`FULL_ALIGN_CELLS` (old lines x new lines)
    get the full alignment; larger ones are aligned inside a band around the block's
    diagonal (:data:`BAND_CELLS`), which bounds the cost.
``relocated``
    Moved code: a block of consecutive old lines that the diff left unmapped (deleted,
    or unpaired in a replaced block) and that reappears, line for line, as a block of
    consecutive unmapped new lines elsewhere in the file. Modelled on Git's moved-line
    detection (``git diff --color-moved=blocks``: "blocks of moved text of at least 20
    alphanumeric characters are detected greedily"), with two differences: lines are
    compared without leading and trailing whitespace, so a block that changes indentation
    still counts as moved, and a block is mapped only when its text occurs exactly once in
    the old version and once in the new one, so the pairing is never a guess between
    copies of repeated code. Blocks are taken greedily, the one with the most alphanumeric
    characters first.

Edited lines inside a moved block: an edit splits the block in two. When two relocated
blocks are adjacent on both sides apart from a gap of at most :data:`MOVE_GAP` unmapped
lines, the gap lines are aligned as in a replaced block and paired as ``edited``. An
edit at either end of a moved block (for example a renamed ``def`` line) is not
recovered, and moves between files are not detected: every file pair is mapped on its
own. Deleted lines and lines with no partner stay unmapped.
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

EDIT_THRESHOLD = 0.6
#: Replaced blocks up to this size (old lines x new lines) get the full alignment.
FULL_ALIGN_CELLS = 40_000
#: Larger blocks are aligned inside a band around their diagonal of about this many cells.
BAND_CELLS = 200_000
#: Git's minimum for a moved block (``COLOR_MOVED_MIN_ALNUM_COUNT`` in Git's ``diff.c``).
MOVE_MIN_ALNUM = 20
#: Largest gap (in lines, on either side) between two moved blocks that is aligned as edits.
MOVE_GAP = 10
#: Lines occurring more often than this among the unmapped new lines do not start a block.
MOVE_MAX_STARTS = 50

EQUAL, EDITED, RELOCATED = "equal", "edited", "relocated"
KINDS = (EQUAL, EDITED, RELOCATED)


@dataclass(frozen=True)
class LineMap:
    """``pairs``: ``{old line: (new line, kind)}``, 1-based. ``banded_old`` and
    ``banded_new``: lines of replaced blocks too large for the full alignment."""

    pairs: dict[int, tuple[int, str]]
    banded_old: frozenset[int] = field(default_factory=frozenset)
    banded_new: frozenset[int] = field(default_factory=frozenset)


def similarity(a: str, b: str) -> float:
    a, b = a.strip(), b.strip()
    if not a and not b:
        return 1.0
    # The bound real_quick_ratio() computes, without building a matcher.
    if 2 * min(len(a), len(b)) < EDIT_THRESHOLD * (len(a) + len(b)):
        return 0.0
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if matcher.quick_ratio() < EDIT_THRESHOLD:
        return 0.0
    return matcher.ratio()


def _align_full(old: Sequence[str], new: Sequence[str]) -> list[tuple[int, int]]:
    n, m = len(old), len(new)
    sim = [[similarity(old[i], new[j]) for j in range(m)] for i in range(n)]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            take = sim[i][j] + best[i + 1][j + 1] if sim[i][j] >= EDIT_THRESHOLD else -1.0
            best[i][j] = max(take, best[i + 1][j], best[i][j + 1])
    pairs: list[tuple[int, int]] = []
    i = j = 0
    while i < n and j < m:
        if sim[i][j] >= EDIT_THRESHOLD and best[i][j] == sim[i][j] + best[i + 1][j + 1]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif best[i][j] == best[i + 1][j]:
            i += 1
        else:
            j += 1
    return pairs


def _band_width(n: int, m: int) -> int:
    return max(-(-m // n) + 1, BAND_CELLS // (2 * n))


def _align_banded(old: Sequence[str], new: Sequence[str]) -> list[tuple[int, int]]:
    """The same alignment, restricted to cells within ``w`` of the line ``j = i m / n``.

    The band contains (0, 0) and (n, m) and is at least as wide as the diagonal's slope,
    so a path through it always exists; cells outside it are unreachable.
    """
    n, m = len(old), len(new)
    w = _band_width(n, m)
    neg = float("-inf")

    def lo(i: int) -> int:
        return max(0, (i * m) // n - w)

    def hi(i: int) -> int:  # exclusive
        return min(m, (i * m) // n + w + 1)

    best: dict[tuple[int, int], float] = {}
    sim: dict[tuple[int, int], float] = {}

    def value(i: int, j: int) -> float:
        if i == n or j == m:
            return 0.0
        return best.get((i, j), neg)

    for i in range(n - 1, -1, -1):
        for j in range(hi(i) - 1, lo(i) - 1, -1):
            s = similarity(old[i], new[j])
            sim[(i, j)] = s
            take = s + value(i + 1, j + 1) if s >= EDIT_THRESHOLD else neg
            best[(i, j)] = max(take, value(i + 1, j), value(i, j + 1))
    pairs: list[tuple[int, int]] = []
    i = j = 0
    while i < n and j < m:
        s = sim.get((i, j), 0.0)
        if s >= EDIT_THRESHOLD and value(i, j) == s + value(i + 1, j + 1):
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif value(i, j) == value(i + 1, j):
            i += 1
        else:
            j += 1
    return pairs


def _align(old: Sequence[str], new: Sequence[str]) -> tuple[list[tuple[int, int]], bool]:
    """Pairs ``(old index, new index)`` and whether the banded alignment was used."""
    if not old or not new:
        return [], False
    if len(old) * len(new) <= FULL_ALIGN_CELLS:
        return _align_full(old, new), False
    return _align_banded(old, new), True


def _alnum(text: str) -> int:
    return sum(ch.isalnum() for ch in text)


def _moves(
    old: Sequence[str], new: Sequence[str], pairs: dict[int, tuple[int, str]]
) -> dict[int, tuple[int, str]]:
    """Relocated (and edited-in-move) pairs among the lines *pairs* leaves unmapped."""
    free_old = [True] * len(old)
    free_new = [True] * len(new)
    for i, (j, _) in pairs.items():
        free_old[i - 1] = False
        free_new[j - 1] = False
    a = [ln.strip() for ln in old]
    b = [ln.strip() for ln in new]

    # Where each non-blank text starts: among the unmapped new lines (block candidates),
    # and anywhere in either version (the uniqueness test).
    starts_new: dict[str, list[int]] = defaultdict(list)
    anywhere_old: dict[str, list[int]] = defaultdict(list)
    anywhere_new: dict[str, list[int]] = defaultdict(list)
    for j, text in enumerate(b):
        if text:
            anywhere_new[text].append(j)
            if free_new[j]:
                starts_new[text].append(j)
    for i, text in enumerate(a):
        if text:
            anywhere_old[text].append(i)

    # Maximal runs of equal, unmapped lines on a diagonal (i + k, j + k).
    runs: list[tuple[int, int, int, int]] = []  # (-alnum, i, j, length)
    for i, text in enumerate(a):
        if not free_old[i] or not text:
            continue
        cands = starts_new.get(text, [])
        if len(cands) > MOVE_MAX_STARTS:
            continue
        for j in cands:
            if i and j and free_old[i - 1] and free_new[j - 1] and a[i - 1] == b[j - 1]:
                if a[i - 1]:
                    continue  # inside a run that starts earlier
            k = 0
            while (i + k < len(a) and j + k < len(b) and free_old[i + k] and free_new[j + k]) and a[
                i + k
            ] == b[j + k]:
                k += 1
            while k and not a[i + k - 1]:  # no trailing blank lines
                k -= 1
            alnum = sum(_alnum(a[i + t]) for t in range(k))
            if alnum >= MOVE_MIN_ALNUM:
                runs.append((-alnum, i, j, k))
    runs.sort()

    def occurrences(seq: Sequence[str], starts: list[int], block: Sequence[str]) -> int:
        n = 0
        for p in starts:
            if p + len(block) <= len(seq) and all(
                seq[p + t] == block[t] for t in range(len(block))
            ):
                n += 1
        return n

    out: dict[int, tuple[int, str]] = {}
    blocks: list[tuple[int, int, int]] = []
    for _, i, j, k in runs:
        if not all(free_old[i + t] and free_new[j + t] for t in range(k)):
            continue  # overlaps a block already taken
        block = a[i : i + k]
        # Unique in the whole file on both sides: a block repeated elsewhere, even in lines
        # the diff already mapped, could be any of its copies.
        if occurrences(a, anywhere_old[block[0]], block) != 1:
            continue
        if occurrences(b, anywhere_new[block[0]], block) != 1:
            continue
        for t in range(k):
            free_old[i + t] = free_new[j + t] = False
            out[i + t + 1] = (j + t + 1, RELOCATED)
        blocks.append((i, j, k))

    # Edits inside a moved block: align the gap between two blocks adjacent on both sides.
    blocks.sort()
    for (i1, j1, k1), (i2, j2, _) in pairwise(blocks):
        go, gn = range(i1 + k1, i2), range(j1 + k1, j2)
        if not go or not gn or len(go) > MOVE_GAP or len(gn) > MOVE_GAP:
            continue
        if not all(free_old[i] for i in go) or not all(free_new[j] for j in gn):
            continue
        aligned, _ = _align([old[i] for i in go], [new[j] for j in gn])
        for di, dj in aligned:
            out[go[di] + 1] = (gn[dj] + 1, EDITED)
    return out


def line_map(old: Sequence[str], new: Sequence[str], *, moves: bool = True) -> LineMap:
    """The full line map of *old* to *new*; ``moves=False`` gives the map without moves."""
    pairs: dict[int, tuple[int, str]] = {}
    banded_old: set[int] = set()
    banded_new: set[int] = set()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                pairs[i1 + k + 1] = (j1 + k + 1, EQUAL)
        elif tag == "replace":
            aligned, banded = _align(old[i1:i2], new[j1:j2])
            if banded:
                banded_old.update(range(i1 + 1, i2 + 1))
                banded_new.update(range(j1 + 1, j2 + 1))
            for i, j in aligned:
                pairs[i1 + i + 1] = (j1 + j + 1, EDITED)
    if moves:
        pairs.update(_moves(old, new, pairs))
    return LineMap(pairs, frozenset(banded_old), frozenset(banded_new))


def map_lines(
    old: Sequence[str], new: Sequence[str], *, moves: bool = True
) -> dict[int, tuple[int, str]]:
    """``{old line: (new line, "equal" | "edited" | "relocated")}`` with 1-based lines."""
    return line_map(old, new, moves=moves).pairs
