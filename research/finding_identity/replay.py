"""Replay a repository's history and score every identity scheme against the ground truth.

For each consecutive pair of commits on the first-parent line, every changed source file
is scanned before and after the change. Unchanged files are skipped: every scheme
trivially keeps their findings, so they would only inflate the counts.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path
from typing import Any

import codeguard

from .categories import split_by_category
from .gitrepo import Change, GitRepo
from .linemap import line_map as compute_line_map
from .matching import GT_KEYS as MATCH_GT_KEYS
from .matching import SCHEME_KEYS, Observation, evaluate, ground_truth, score
from .observations import ObservationWriter
from .scan import Scanner, is_candidate

#: The ground-truth counts, plus the findings whose new line lies in a replaced block too
#: large for the full alignment (aligned in a band, see :mod:`linemap`).
GT_KEYS = (*MATCH_GT_KEYS, "known_banded", "introduced_banded")


def _empty_totals(schemes: Sequence[str]) -> dict[str, Any]:
    return {
        "gt": dict.fromkeys(GT_KEYS, 0),
        "schemes": {s: dict.fromkeys(SCHEME_KEYS, 0) for s in schemes},
        "files": 0,
        "renamed_files": 0,
        "skipped_files": 0,
    }


def _add(totals: dict[str, Any], other: dict[str, Any]) -> None:
    for k, v in other["gt"].items():
        totals["gt"][k] += v
    for s, counts in other["schemes"].items():
        for k, v in counts.items():
            totals["schemes"][s][k] += v
    for k in ("files", "renamed_files", "skipped_files"):
        totals[k] += other[k]


def _versions(repo: GitRepo, history: Sequence[str]) -> Iterator[tuple[str, str, bytes]]:
    """``(blob, path, data)`` of every file version :func:`_replay_change` will scan."""
    for old, new in pairwise(history):
        for ch in repo.changes(old, new):
            for path, sha in ((ch.old_path, ch.old_sha), (ch.new_path, ch.new_sha)):
                if path and sha and is_candidate(path):
                    yield sha, path, repo.blob(sha)


def _replay_change(
    repo: GitRepo,
    scanner: Scanner,
    ch: Change,
    schemes: Sequence[str],
    totals: dict[str, Any],
    records: list[dict[str, Any]] | None,
    by_category: dict[str, dict[str, Any]] | None = None,
) -> None:
    old_ok, new_ok = is_candidate(ch.old_path), is_candidate(ch.new_path)
    if not (old_ok or new_ok):
        return
    old_res = new_res = None
    if old_ok and ch.old_sha and ch.old_path:
        old_res = scanner.scan(ch.old_sha, ch.old_path, repo.blob(ch.old_sha))
        if old_res is None:
            totals["skipped_files"] += 1
            return
    if new_ok and ch.new_sha and ch.new_path:
        new_res = scanner.scan(ch.new_sha, ch.new_path, repo.blob(ch.new_sha))
        if new_res is None:
            totals["skipped_files"] += 1
            return
    old_obs = old_res.observations if old_res else []
    new_obs = new_res.observations if new_res else []
    if not old_obs and not new_obs:
        return
    lm = compute_line_map(old_res.lines, new_res.lines) if old_res and new_res else None
    line_map = lm.pairs if lm else {}
    renamed = ch.status == "R"
    gt_pairs = ground_truth(old_obs, new_obs, line_map)
    result = score(
        old_obs, new_obs, gt_pairs, schemes, keep_records=records is not None, renamed=renamed
    )
    for k, v in result.gt.items():
        totals["gt"][k] += v
    if lm and lm.banded_new:
        for j, n in enumerate(new_obs):
            if n.line in lm.banded_new:
                totals["gt"]["known_banded" if j in gt_pairs else "introduced_banded"] += 1
    for s, counts in result.by_scheme.items():
        for k, v in counts.items():
            totals["schemes"][s][k] += v
    totals["files"] += 1
    if ch.status == "R":
        totals["renamed_files"] += 1
    if records is not None:
        for rec in result.records:
            rec.update(path=ch.new_path, old_path=ch.old_path, status=ch.status)
            records.append(rec)
    if by_category is not None:
        _add_by_category(by_category, old_obs, new_obs, line_map, schemes, ch.status)


def _add_by_category(
    by_category: dict[str, dict[str, Any]],
    old_obs: Sequence[Observation],
    new_obs: Sequence[Observation],
    line_map: dict[int, tuple[int, str]],
    schemes: Sequence[str],
    status: str,
) -> None:
    """Score each rule category's findings on their own (they add up to the totals)."""
    old_split, new_split = split_by_category(old_obs), split_by_category(new_obs)
    for category in sorted(old_split.keys() | new_split.keys()):
        result = evaluate(
            old_split.get(category, []),
            new_split.get(category, []),
            line_map,
            schemes,
            renamed=status == "R",
        )
        totals = by_category.setdefault(category, _empty_totals(schemes))
        for k, v in result.gt.items():
            totals["gt"][k] += v
        for s, counts in result.by_scheme.items():
            for k, v in counts.items():
                totals["schemes"][s][k] += v
        totals["files"] += 1
        if status == "R":
            totals["renamed_files"] += 1


def _category_summaries(
    by_category: dict[str, dict[str, Any]],
    scanner: Scanner,
    schemes: Sequence[str],
    categories: Sequence[str],
) -> dict[str, Any]:
    """Per category, a ``{"totals", "collisions"}`` block shaped like the summary's."""
    names = sorted(set(categories) | by_category.keys() | scanner.category_observations.keys())
    return {
        c: {
            "totals": by_category.get(c, _empty_totals(schemes)),
            "collisions": {
                "observations": scanner.category_observations.get(c, 0),
                "by_scheme": scanner.category_collisions.get(c, dict.fromkeys(schemes, 0)),
            },
        }
        for c in names
    }


def replay(
    repo: GitRepo,
    *,
    ref: str,
    commits: int,
    scanner: Scanner,
    schemes: Sequence[str],
    out_dir: Path,
    label: str,
    categories: Sequence[str],
    details: bool = False,
    observations: ObservationWriter | None = None,
) -> dict[str, Any]:
    """Replay *commits* pairs behind *ref* and write the results to *out_dir*.

    With *observations* (which the *scanner* must also record to), the commit pairs and
    their changes are recorded too, so that :mod:`rescore` can replay the run.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    history = repo.first_parent_history(ref, commits + 1)
    head = repo.resolve(ref)
    meta = {
        "label": label,
        "repo": str(repo.path),
        "ref": ref,
        "head": head,
        "commit_pairs": max(len(history) - 1, 0),
        "categories": list(categories),
        "schemes": list(schemes),
        "codeguard_version": codeguard.__version__,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    totals = _empty_totals(schemes)
    category_totals: dict[str, dict[str, Any]] = {}
    started = time.monotonic()
    scanner.prefetch(_versions(repo, history))
    with (
        (out_dir / "pairs.jsonl").open("w", encoding="utf-8") as pairs_out,
        (out_dir / "findings.jsonl").open("w", encoding="utf-8") as findings_out,
    ):
        for n, (old, new) in enumerate(pairwise(history), start=1):
            pair_totals = _empty_totals(schemes)
            records: list[dict[str, Any]] | None = [] if details else None
            changes = repo.changes(old, new)
            if observations is not None:
                looked_at = [
                    c for c in changes if is_candidate(c.old_path) or is_candidate(c.new_path)
                ]
                observations.pair(old, new, looked_at)
            for ch in changes:
                _replay_change(repo, scanner, ch, schemes, pair_totals, records, category_totals)
            _add(totals, pair_totals)
            pairs_out.write(json.dumps({"old": old, "new": new, **pair_totals}) + "\n")
            for rec in records or []:
                findings_out.write(json.dumps({"commit": new, **rec}) + "\n")
            if n % 25 == 0 or n == meta["commit_pairs"]:
                elapsed = time.monotonic() - started
                print(
                    f"[{label}] {n}/{meta['commit_pairs']} commit pairs, "
                    f"{totals['gt']['new']} findings compared, {elapsed:.0f}s",
                    file=sys.stderr,
                )
    meta["elapsed_seconds"] = round(time.monotonic() - started, 1)
    meta["versions_scanned"] = scanner.versions_scanned
    meta["parse_failures"] = scanner.parse_failures
    summary = {
        **meta,
        "totals": totals,
        "collisions": {
            "observations": scanner.observations,
            "by_scheme": scanner.collision_totals,
        },
        "by_category": _category_summaries(category_totals, scanner, schemes, categories),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if observations is not None:
        observations.close({**meta, "commits": commits, "analyzer": scanner.describe()})
    return summary
