# SPDX-License-Identifier: Apache-2.0
"""Pair the files of a baseline with the files of a scan, across renames.

Findings are matched file by file (:mod:`codeguard.engine.matcher`), so a renamed
file must first be paired with its old name.  Three sources, in order: the same path;
renames git reports between the baseline's commit and the working tree; and, for what
is still unpaired, content: a removed and an added file whose findings' line hashes
(the ``lh`` key) overlap enough.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class PairConfig:
    """``content_threshold``: the least Jaccard similarity of two files' ``lh``
    multisets that pairs them by content (git's rename detection uses 50% of
    content).  ``same_extension``: only pair files with the same extension by
    content.  ``pair_by_content``: whether to try content pairing at all."""

    content_threshold: float = 0.5
    same_extension: bool = True
    pair_by_content: bool = True


DEFAULT_PAIR_CONFIG = PairConfig()


@dataclass(frozen=True)
class FilePair:
    old: str
    new: str
    how: str  # "path" | "rename" | "content"


def multiset_jaccard(a: Counter[str], b: Counter[str]) -> float:
    """Jaccard similarity of two multisets; 0 when either is empty."""
    if not a or not b:
        return 0.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def pair_files(
    old_files: Iterable[str],
    new_files: Iterable[str],
    *,
    renames: Mapping[str, str] | None = None,
    old_keys: Mapping[str, Iterable[str]] | None = None,
    new_keys: Mapping[str, Iterable[str]] | None = None,
    config: PairConfig | None = None,
) -> list[FilePair]:
    """Pair old and new file paths, each at most once.

    *renames* maps old path to new path (from git); *old_keys* and *new_keys* give,
    per path, the ``lh`` keys of its findings for content pairing.
    """
    cfg = config or DEFAULT_PAIR_CONFIG
    olds = list(dict.fromkeys(old_files))
    news = list(dict.fromkeys(new_files))
    new_set = set(news)
    out: list[FilePair] = []
    paired_old: set[str] = set()
    paired_new: set[str] = set()
    for path in olds:
        if path in new_set:
            out.append(FilePair(path, path, "path"))
            paired_old.add(path)
            paired_new.add(path)
    for old, new in (renames or {}).items():
        if old in paired_old or new in paired_new or old not in olds or new not in new_set:
            continue
        out.append(FilePair(old, new, "rename"))
        paired_old.add(old)
        paired_new.add(new)
    if cfg.pair_by_content and old_keys is not None and new_keys is not None:
        left_old = [p for p in olds if p not in paired_old]
        left_new = [p for p in news if p not in paired_new]
        old_counts = {p: Counter(old_keys.get(p, ())) for p in left_old}
        new_counts = {p: Counter(new_keys.get(p, ())) for p in left_new}
        scored: list[tuple[float, str, str]] = []
        for o in left_old:
            for n in left_new:
                if cfg.same_extension and PurePosixPath(o).suffix != PurePosixPath(n).suffix:
                    continue
                score = multiset_jaccard(old_counts[o], new_counts[n])
                if score >= cfg.content_threshold:
                    scored.append((-score, o, n))
        scored.sort()
        for _neg, o, n in scored:
            if o in paired_old or n in paired_new:
                continue
            out.append(FilePair(o, n, "content"))
            paired_old.add(o)
            paired_new.add(n)
    return out
