"""Long-span ("drift") mode: score an anchor commit against commits far after it.

A baseline is usually created once and compared with much later versions, so replaying
consecutive commits understates how often identity breaks. This mode picks an anchor
commit c0 on the first-parent line and, for each span k, compares the findings at c0
with the findings at c_k, the k-th first-parent commit after c0.

Ground truth is chained, not taken from a direct c0 -> c_k diff (which mis-maps blocks
that moved). Each anchor finding's line is followed through every intermediate
first-parent commit with :func:`linemap.map_lines` on that step's diff, following
renames (``git diff -M``) step by step. A finding persists to c_k when its chain is
unbroken and a finding with the same rule sits at the mapped line in c_k. It counts as
"edited" when any step edited its line, otherwise as "equal" (only moved).

Only files are compared whose lineage changed in the first k steps, plus files added
since c0: every scheme trivially keeps the findings of untouched files. Only c0 and the
c_k are scanned; intermediate commits are read only as blobs of files that hold tracked
findings, to compute the line maps.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime, timezone
from itertools import pairwise
from pathlib import Path
from typing import Any

import codeguard

from .gitrepo import Change, GitRepo
from .linemap import map_lines
from .matching import Observation, score
from .replay import GT_KEYS, SCHEME_KEYS
from .scan import Scanner, ScanResult, is_candidate, rule_ids_for
from .schemes import ALL_SCHEMES, split_lines
from .summarize import summarize_drift

HERE = Path(__file__).parent
DEFAULT_SPANS = (1, 10, 50, 100, 200)

#: Where an anchor line is at some commit: ``(path, line, edited on the way)``, or
#: ``None`` once its file was deleted or its line removed or rewritten.
Position = tuple[str, int, bool] | None
#: An anchor line: ``(path at c0, line at c0)``.
Anchor = tuple[str, int]


def trace_files(
    paths: Iterable[str], steps: Sequence[Sequence[Change]], spans: Iterable[int]
) -> tuple[dict[str, int], dict[int, dict[str, str]]]:
    """Follow every file of the anchor commit through *steps*, following renames.

    Returns ``{anchor path: first step that changed it}`` and, for each span k,
    ``{path at c_k: anchor path}`` for the anchor files still present at c_k.
    """
    origin = {p: p for p in paths}
    first_touch: dict[str, int] = {}
    snapshots: dict[int, dict[str, str]] = {}
    wanted = set(spans)
    for step, changes in enumerate(steps, start=1):
        # Apply renames after the whole step, so a swap a <-> b reads the old origins.
        moved: dict[str, str] = {}
        for ch in changes:
            if ch.old_path is None or ch.status == "C" or ch.old_path not in origin:
                continue
            first_touch.setdefault(origin[ch.old_path], step)
            if ch.status in ("D", "R"):
                src = origin.pop(ch.old_path)
                if ch.status == "R" and ch.new_path is not None:
                    moved[ch.new_path] = src
        origin.update(moved)
        if step in wanted:
            snapshots[step] = dict(origin)
    return first_touch, snapshots


def chain_lines(
    steps: Sequence[Sequence[Change]],
    tracked: Mapping[str, Iterable[int]],
    spans: Iterable[int],
    read_lines: Callable[[str], list[str]],
) -> dict[int, dict[Anchor, Position]]:
    """Follow anchor lines through *steps*, one line map per changed file per step.

    *tracked* maps anchor paths to the lines to follow and *read_lines* returns the
    lines of a blob. Returns, for each span k, ``{anchor: position at c_k}``.
    """
    live: dict[str, dict[Anchor, tuple[int, bool]]] = {
        path: {(path, line): (line, False) for line in lines} for path, lines in tracked.items()
    }
    anchors = [anchor for chains in live.values() for anchor in chains]
    snapshots: dict[int, dict[Anchor, Position]] = {}
    wanted = set(spans)
    for step, changes in enumerate(steps, start=1):
        moved: dict[str, dict[Anchor, tuple[int, bool]]] = {}
        for ch in changes:
            if ch.old_path is None or ch.status == "C":
                continue
            chains = live.pop(ch.old_path, None)
            if chains is None or ch.new_path is None or ch.new_sha is None:
                continue  # untracked, or deleted: the chains break
            if ch.old_sha == ch.new_sha:  # pure rename or mode change
                moved[ch.new_path] = chains
                continue
            assert ch.old_sha is not None
            line_map = map_lines(read_lines(ch.old_sha), read_lines(ch.new_sha))
            kept: dict[Anchor, tuple[int, bool]] = {}
            for anchor, (line, edited) in chains.items():
                hit = line_map.get(line)
                if hit is not None:
                    kept[anchor] = (hit[0], edited or hit[1] == "edited")
            if kept:
                moved[ch.new_path] = kept
        live.update(moved)
        if step in wanted:
            positions: dict[Anchor, Position] = dict.fromkeys(anchors)
            for path, chains in live.items():
                for anchor, (line, edited) in chains.items():
                    positions[anchor] = (path, line, edited)
            snapshots[step] = positions
    return snapshots


class _Blobs:
    """Lines of blobs, cached briefly: a step's new blob is the next step's old blob."""

    def __init__(self, repo: GitRepo) -> None:
        self._repo = repo
        self._cache: dict[str, list[str]] = {}
        self.read = 0

    def lines(self, sha: str) -> list[str]:
        hit = self._cache.get(sha)
        if hit is None:
            if len(self._cache) >= 512:
                self._cache.clear()
            hit = split_lines(self._repo.blob(sha).decode("utf-8", errors="replace"))
            self._cache[sha] = hit
            self.read += 1
        return hit


def _empty_totals(schemes: Sequence[str]) -> dict[str, Any]:
    return {
        "gt": dict.fromkeys(GT_KEYS, 0),
        "schemes": {s: dict.fromkeys(SCHEME_KEYS, 0) for s in schemes},
        "files": 0,
        "renamed_files": 0,
        "skipped_files": 0,
    }


def _compare_span(
    repo: GitRepo,
    scanner: Scanner,
    schemes: Sequence[str],
    *,
    span: int,
    files: dict[str, str],
    first_touch: dict[str, int],
    origin_of: dict[str, str],
    old_scans: dict[str, ScanResult | None],
    positions: dict[Anchor, Position],
    records: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Compare c0 with c_k (*files* is c_k's tree) and score every scheme."""
    dest_of = {src: path for path, src in origin_of.items()}
    old_paths = [p for p in sorted(old_scans) if first_touch[p] <= span]
    # Files at c_k that descend from a changed anchor file, or that were added since c0.
    new_paths = [
        q
        for q in sorted(files)
        if is_candidate(q)
        and (q not in origin_of or first_touch.get(origin_of[q], span + 1) <= span)
    ]
    new_scans = {q: scanner.scan(files[q], q, repo.blob(files[q])) for q in new_paths}

    units: list[tuple[str | None, str | None]] = []
    for path in old_paths:
        dest = dest_of.get(path)
        units.append((path, dest if dest in new_scans else None))
    paired = {q for _, q in units}
    units += [(None, q) for q in new_paths if q not in paired]

    totals = _empty_totals(schemes)
    collided = dict.fromkeys(schemes, 0)
    old: list[Observation] = []
    new: list[Observation] = []
    old_at: list[str] = []
    new_at: list[str] = []
    for p, q in units:
        old_res = old_scans[p] if p is not None else None
        new_res = new_scans[q] if q is not None else None
        if (p is not None and old_res is None) or (q is not None and new_res is None):
            totals["skipped_files"] += 1
            continue
        old_obs = old_res.observations if old_res else []
        new_obs = new_res.observations if new_res else []
        if not old_obs and not new_obs:
            continue
        totals["files"] += 1
        if p is not None and q is not None and p != q:
            totals["renamed_files"] += 1
        for res in (old_res, new_res):
            for scheme, count in (res.collisions if res else {}).items():
                collided[scheme] += count
        old += old_obs
        new += new_obs
        old_at += [p or ""] * len(old_obs)
        new_at += [q or ""] * len(new_obs)

    # Chained ground truth: same rule at the line the anchor line was followed to.
    at_spot: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for j, n in enumerate(new):
        at_spot[(new_at[j], n.rule, n.line)].append(j)
    gt_pairs: dict[int, tuple[int, str]] = {}
    chains = {"tracked": len(old), "alive": 0, "alive_edited": 0}
    for i in sorted(range(len(old)), key=lambda k: (old_at[k], old[k].line, old[k].col)):
        o = old[i]
        pos = positions.get((old_at[i], o.line))
        if pos is None:
            continue
        path, line, edited = pos
        chains["alive"] += 1
        chains["alive_edited"] += edited
        candidates = [j for j in at_spot.get((path, o.rule, line), []) if j not in gt_pairs]
        if candidates:
            j = min(candidates, key=lambda k: abs(new[k].col - o.col))
            gt_pairs[j] = (i, "edited" if edited else "equal")

    result = score(old, new, gt_pairs, schemes, keep_records=records is not None)
    totals["gt"].update(result.gt)
    for scheme, counts in result.by_scheme.items():
        totals["schemes"][scheme].update(counts)
    if records is not None:
        for j, rec in enumerate(result.records):
            truth = gt_pairs.get(j)
            rec.update(span=span, path=new_at[j], old_path=old_at[truth[0]] if truth else None)
            records.append(rec)
    return {
        "totals": totals,
        "collisions": {"observations": len(old) + len(new), "by_scheme": collided},
        "chains": chains,
    }


def drift(
    repo: GitRepo,
    *,
    ref: str,
    anchor_back: int,
    spans: Sequence[int],
    scanner: Scanner,
    schemes: Sequence[str],
    out_dir: Path,
    label: str,
    categories: Sequence[str],
    details: bool = False,
) -> dict[str, Any]:
    """Score every scheme between the anchor commit and each span; write ``summary.json``."""
    spans = sorted(set(spans))
    if not spans or spans[0] < 1 or spans[-1] > anchor_back:
        raise ValueError(f"spans must lie between 1 and --anchor-back ({anchor_back})")
    history = repo.first_parent_history(ref, anchor_back + 1)
    if len(history) < anchor_back + 1:
        raise ValueError(
            f"{ref} has only {len(history) - 1} first-parent commits behind it, fewer than "
            f"--anchor-back {anchor_back} (delete a shallow clone to re-clone it deeper)"
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    anchor = history[0]

    def progress(msg: str) -> None:
        print(f"[{label}] {msg}, {time.monotonic() - started:.0f}s", file=sys.stderr)

    steps = [repo.changes(a, b) for a, b in pairwise(history[: spans[-1] + 1])]
    anchor_files = repo.files(anchor)
    first_touch, origins = trace_files(anchor_files, steps, spans)
    old_scans = {
        p: scanner.scan(anchor_files[p], p, repo.blob(anchor_files[p]))
        for p in sorted(first_touch)
        if is_candidate(p)
    }
    tracked = {p: {o.line for o in r.observations} for p, r in old_scans.items() if r}
    progress(f"anchor {anchor[:12]}: {len(old_scans)} changed files scanned")
    blobs = _Blobs(repo)
    positions = chain_lines(steps, tracked, spans, blobs.lines)
    progress(f"chained {sum(map(len, tracked.values()))} lines over {len(steps)} commits")

    entries: list[dict[str, Any]] = []
    with (out_dir / "findings.jsonl").open("w", encoding="utf-8") as findings_out:
        for k in spans:
            records: list[dict[str, Any]] | None = [] if details else None
            entry = _compare_span(
                repo,
                scanner,
                schemes,
                span=k,
                files=repo.files(history[k]),
                first_touch=first_touch,
                origin_of=origins[k],
                old_scans=old_scans,
                positions=positions[k],
                records=records,
            )
            entries.append({"span": k, "commit": history[k], **entry})
            for rec in records or []:
                findings_out.write(json.dumps(rec) + "\n")
            gt = entry["totals"]["gt"]
            progress(f"span {k}: {gt['old']} anchor findings, {gt['new']} at c_{k}")

    summary = {
        "mode": "drift",
        "label": label,
        "repo": str(repo.path),
        "ref": ref,
        "head": repo.resolve(ref),
        "anchor": anchor,
        "anchor_back": anchor_back,
        "categories": list(categories),
        "schemes": list(schemes),
        "codeguard_version": codeguard.__version__,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 1),
        "versions_scanned": scanner.versions_scanned,
        "parse_failures": scanner.parse_failures,
        "blobs_read": blobs.read,
        "spans": entries,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


# -- command line ---------------------------------------------------------------


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("repo", help="local repository path or a git URL to clone")
    parser.add_argument("--ref", default="HEAD", help="branch or commit the spans end at")
    parser.add_argument(
        "--anchor-back",
        type=int,
        default=200,
        help="anchor commit: this many first-parent commits behind --ref",
    )
    parser.add_argument(
        "--spans",
        help="comma-separated spans in commits after the anchor "
        f"(default: {','.join(map(str, DEFAULT_SPANS))}, up to --anchor-back)",
    )
    parser.add_argument("--label", help="name for the results (default: repository name)")
    parser.add_argument("--out", type=Path, help="results directory")
    parser.add_argument("--workdir", type=Path, default=HERE / ".repos", help="where to clone")
    parser.add_argument(
        "--categories",
        default="security,performance,quality",
        help="comma-separated rule categories to run",
    )
    parser.add_argument("--details", action="store_true", help="write one record per finding")


def run(args: argparse.Namespace) -> None:
    if args.spans:
        spans = [int(s) for s in args.spans.split(",") if s.strip()]
    else:
        spans = [k for k in DEFAULT_SPANS if k <= args.anchor_back]
    ref = None if args.ref == "HEAD" else args.ref
    repo = GitRepo.open_or_clone(args.repo, args.workdir, depth=args.anchor_back + 2, ref=ref)
    label = args.label or repo.path.name
    out = args.out or HERE / "results" / "drift" / label
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    scanner = Scanner(rule_ids_for(categories), ALL_SCHEMES)
    try:
        drift(
            repo,
            ref=args.ref,
            anchor_back=args.anchor_back,
            spans=spans,
            scanner=scanner,
            schemes=ALL_SCHEMES,
            out_dir=out,
            label=label,
            categories=categories,
            details=args.details,
        )
    finally:
        repo.close()
    summarize_drift([out])
