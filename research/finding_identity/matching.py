"""Compare each identity scheme with the ground truth for one file across one change.

Ground truth: an old finding and a new finding are the same when they have the same
rule and the old finding's line maps (see :mod:`linemap`) to the new finding's line.
Each new finding then has a true status, "known" (it existed before) or "new".

A scheme predicts a status by matching keys: findings with equal keys are paired in
line order. Comparing the two statuses gives, per new finding:

- ``known_ok``     known, and the scheme paired it with its true predecessor
- ``mispaired``    known, but the scheme paired it with a different old finding
- ``false_new``    known, but the scheme reports it as new (noise, broken baselines)
- ``false_known``  new, but the scheme matched it to an old finding (a hidden finding)
- ``new_ok``       new, and the scheme reports it as new
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field

OUTCOMES = ("known_ok", "mispaired", "false_new", "false_known", "new_ok")


@dataclass(frozen=True)
class Observation:
    """One finding in one version of one file."""

    rule: str
    line: int
    col: int
    keys: dict[str, str] = field(hash=False, compare=False)


@dataclass
class FileResult:
    """Outcome counts for one file across one change."""

    gt: dict[str, int]
    by_scheme: dict[str, dict[str, int]]
    records: list[dict[str, object]]


def ground_truth(
    old: Sequence[Observation],
    new: Sequence[Observation],
    line_map: dict[int, tuple[int, str]],
) -> dict[int, tuple[int, str]]:
    """``{new index: (old index, "equal" | "edited")}`` for findings that persisted."""
    by_rule_line: dict[tuple[str, int], list[int]] = defaultdict(list)
    for j, n in enumerate(new):
        by_rule_line[(n.rule, n.line)].append(j)
    pairs: dict[int, tuple[int, str]] = {}
    for i in sorted(range(len(old)), key=lambda k: (old[k].line, old[k].col)):
        o = old[i]
        mapped = line_map.get(o.line)
        if mapped is None:
            continue
        candidates = [j for j in by_rule_line.get((o.rule, mapped[0]), []) if j not in pairs]
        if candidates:
            j = min(candidates, key=lambda k: abs(new[k].col - o.col))
            pairs[j] = (i, mapped[1])
    return pairs


def scheme_pairs(
    old: Sequence[Observation], new: Sequence[Observation], scheme: str
) -> dict[int, int]:
    """``{new index: old index}`` as the scheme would match them."""
    old_by_key: dict[str, list[int]] = defaultdict(list)
    new_by_key: dict[str, list[int]] = defaultdict(list)
    for i, o in enumerate(old):
        old_by_key[o.keys[scheme]].append(i)
    for j, n in enumerate(new):
        new_by_key[n.keys[scheme]].append(j)
    pairs: dict[int, int] = {}
    for key, new_idx in new_by_key.items():
        old_idx = sorted(old_by_key.get(key, []), key=lambda k: (old[k].line, old[k].col))
        new_sorted = sorted(new_idx, key=lambda k: (new[k].line, new[k].col))
        for i, j in zip(old_idx, new_sorted, strict=False):
            pairs[j] = i
    return pairs


def evaluate(
    old: Sequence[Observation],
    new: Sequence[Observation],
    line_map: dict[int, tuple[int, str]],
    schemes: Sequence[str],
    *,
    keep_records: bool = False,
) -> FileResult:
    gt_pairs = ground_truth(old, new, line_map)
    return score(old, new, gt_pairs, schemes, keep_records=keep_records)


def score(
    old: Sequence[Observation],
    new: Sequence[Observation],
    gt_pairs: dict[int, tuple[int, str]],
    schemes: Sequence[str],
    *,
    keep_records: bool = False,
) -> FileResult:
    """Score every scheme against true pairs ``{new index: (old index, kind)}``."""
    gt = {
        "old": len(old),
        "new": len(new),
        "known": len(gt_pairs),
        "known_equal": sum(1 for _, kind in gt_pairs.values() if kind == "equal"),
        "known_edited": sum(1 for _, kind in gt_pairs.values() if kind == "edited"),
        "introduced": len(new) - len(gt_pairs),
        "removed": len(old) - len(gt_pairs),
    }
    by_scheme: dict[str, dict[str, int]] = {}
    statuses: dict[str, list[str]] = {}
    for scheme in schemes:
        predicted = scheme_pairs(old, new, scheme)
        counts = dict.fromkeys(OUTCOMES, 0)
        counts["false_new_equal"] = counts["false_new_edited"] = 0
        per_new: list[str] = []
        for j in range(len(new)):
            truth = gt_pairs.get(j)
            guess = predicted.get(j)
            if truth is None:
                outcome = "new_ok" if guess is None else "false_known"
            elif guess is None:
                outcome = "false_new"
                counts[f"false_new_{truth[1]}"] += 1
            else:
                outcome = "known_ok" if guess == truth[0] else "mispaired"
            counts[outcome] += 1
            per_new.append(outcome)
        by_scheme[scheme] = counts
        statuses[scheme] = per_new

    records: list[dict[str, object]] = []
    if keep_records:
        for j, n in enumerate(new):
            truth = gt_pairs.get(j)
            records.append(
                {
                    "rule": n.rule,
                    "line": n.line,
                    "col": n.col,
                    "truth": "new" if truth is None else "known",
                    "truth_kind": None if truth is None else truth[1],
                    "old_line": None if truth is None else old[truth[0]].line,
                    "outcomes": {s: statuses[s][j] for s in schemes},
                }
            )
    return FileResult(gt, by_scheme, records)


def collisions(observations: Sequence[Observation], schemes: Sequence[str]) -> dict[str, int]:
    """Per scheme, how many findings share their key with another finding in the same file."""
    out: dict[str, int] = {}
    for scheme in schemes:
        counts: dict[str, int] = defaultdict(int)
        for o in observations:
            counts[o.keys[scheme]] += 1
        out[scheme] = sum(c for c in counts.values() if c > 1)
    return out
