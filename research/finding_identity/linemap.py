"""Map lines of an old file version to lines of the new version (the ground truth).

Lines the diff keeps unchanged map exactly ("equal"). Inside a replaced block, old and
new lines are paired when they are similar enough ("edited"): an order-preserving
alignment that maximizes total similarity, counting only pairs at or above the
threshold. Deleted lines and lines with no similar partner are not mapped.
"""

from __future__ import annotations

import difflib
from collections.abc import Sequence

EDIT_THRESHOLD = 0.6
#: Replaced blocks larger than this (old lines x new lines) are aligned position by
#: position instead of with the full alignment, to keep the cost bounded.
MAX_ALIGN_CELLS = 4000


def similarity(a: str, b: str) -> float:
    a, b = a.strip(), b.strip()
    if not a and not b:
        return 1.0
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if matcher.real_quick_ratio() < EDIT_THRESHOLD or matcher.quick_ratio() < EDIT_THRESHOLD:
        return 0.0
    return matcher.ratio()


def _align(old: Sequence[str], new: Sequence[str]) -> list[tuple[int, int]]:
    n, m = len(old), len(new)
    if n * m > MAX_ALIGN_CELLS:
        return [(k, k) for k in range(min(n, m)) if similarity(old[k], new[k]) >= EDIT_THRESHOLD]
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


def map_lines(old: Sequence[str], new: Sequence[str]) -> dict[int, tuple[int, str]]:
    """``{old line: (new line, "equal" | "edited")}`` with 1-based line numbers."""
    out: dict[int, tuple[int, str]] = {}
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                out[i1 + k + 1] = (j1 + k + 1, "equal")
        elif tag == "replace":
            for i, j in _align(old[i1:i2], new[j1:j2]):
                out[i1 + i + 1] = (j1 + j + 1, "edited")
    return out
