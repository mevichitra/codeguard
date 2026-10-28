"""``rescore``: replay a recorded run from its observation cache, with any schemes.

A recording (:mod:`observations`) holds the analyzer's findings for every file version
a replay scanned and the commit pairs it walked. Rescoring runs :func:`replay.replay`
over that recording with a :class:`scan.Scanner` that reads findings from the cache and
computes the keys of the requested schemes from the file text, which comes from the
repository's git blobs. The output has the layout of a live replay (``summary.json``,
``pairs.jsonl``, ``findings.jsonl``, ``analyzer.json``), so every report works on it.

``--check <results>`` compares a rescore with an earlier run of the same recording:
the totals, the per-pair counts and the per-finding records must be identical for the
schemes both have.

``--merge-from <results>`` is for iterating on one scheme: rescore only that scheme
(``--schemes``) and take every other scheme's counts and outcomes from an earlier run of
the same recording, which the ground truth of both runs must agree on. SonarQube's
tracker and GitHub's rolling hash are most of a rescore's time; a new scheme on its own
costs little more than the line map.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .observations import META, ObservationReader, RecordedRepo
from .replay import replay
from .scan import Scanner
from .schemes import schemes_for

HERE = Path(__file__).parent


def recordings(root: Path) -> list[Path]:
    """The recording directories under *root*, or *root* itself if it is one."""
    if (root / META).exists():
        return [root]
    return sorted(d for d in root.iterdir() if d.is_dir() and (d / META).exists())


def repository_for(reader: ObservationReader, workdir: Path | None) -> Path:
    """Where the recorded repository's blobs are: *workdir*/label, else the recorded path."""
    label = str(reader.meta["label"])
    if workdir is not None and (workdir / label / ".git").exists():
        return workdir / label
    recorded = Path(str(reader.meta["repo"]))
    if (recorded / ".git").exists():
        return recorded
    raise FileNotFoundError(
        f"no clone of {label}: not at {recorded}" + (f" nor {workdir}" if workdir else "")
    )


def rescore_one(
    recording: Path,
    out: Path,
    schemes: list[str] | None,
    *,
    workdir: Path | None = None,
    details: bool = True,
    merge_from: Path | None = None,
) -> dict[str, Any]:
    """Rescore one recording into ``out``; return the summary.

    With *merge_from*, the results of an earlier run of the same recording under
    ``merge_from/<label>`` are merged in: its schemes' counts and outcomes are kept, the
    rescored schemes' added or replaced.
    """
    reader = ObservationReader(recording)
    wanted = list(schemes) if schemes else list(schemes_for(reader.analyzer))
    repo = RecordedRepo(reader, repository_for(reader, workdir))
    scanner = Scanner.from_observations(reader, wanted)
    meta = reader.meta
    try:
        summary = replay(
            repo,
            ref=str(meta["ref"]),
            commits=int(meta["commits"]),
            scanner=scanner,
            schemes=wanted,
            out_dir=out,
            label=str(meta["label"]),
            categories=[str(c) for c in meta["categories"]],
            details=details,
        )
    finally:
        repo.close()
    described = {**scanner.describe(), "rescored_schemes": wanted}
    if merge_from is not None:
        summary = merge(out, merge_from / str(meta["label"]))
        described["merged_from"] = str(merge_from)
    (out / "analyzer.json").write_text(json.dumps(described, indent=2) + "\n", encoding="utf-8")
    return summary


def _run(
    args: tuple[Path, Path, list[str] | None, Path | None, bool, Path | None],
) -> tuple[str, float]:
    recording, out, schemes, workdir, details, merge_from = args
    started = time.monotonic()
    rescore_one(recording, out, schemes, workdir=workdir, details=details, merge_from=merge_from)
    return recording.name, time.monotonic() - started


# -- merging with an earlier run ------------------------------------------------------


def _merged(reference: dict[str, Any], rescored: dict[str, Any]) -> dict[str, Any]:
    """*reference*'s per-scheme dict with *rescored*'s schemes added or replaced."""
    return {**reference, **rescored}


def _merge_block(new: dict[str, Any], old: dict[str, Any], what: str) -> None:
    """Merge the scheme counts of two ``{"totals", "collisions"}`` blocks into *new*."""
    if new["totals"]["gt"] != old["totals"]["gt"]:
        raise ValueError(f"{what}: the ground truth differs, so the runs cannot be merged")
    new["totals"]["schemes"] = _merged(old["totals"]["schemes"], new["totals"]["schemes"])
    if new["collisions"]["observations"] != old["collisions"]["observations"]:
        raise ValueError(f"{what}: the observation counts differ")
    new["collisions"]["by_scheme"] = _merged(
        old["collisions"]["by_scheme"], new["collisions"]["by_scheme"]
    )


_RECORD_IDENTITY = ("commit", "rule", "line", "col", "truth", "truth_kind", "old_line", "path")


def merge(out: Path, reference: Path) -> dict[str, Any]:
    """Merge the run at *reference* into the rescore at *out*, in place; return the summary."""
    new: dict[str, Any] = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    old: dict[str, Any] = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    if new["commit_pairs"] != old["commit_pairs"]:
        raise ValueError(f"{reference}: a different number of commit pairs")
    _merge_block(new, old, "totals")
    for category, block in old.get("by_category", {}).items():
        mine = new.setdefault("by_category", {}).get(category)
        if mine is None:
            raise ValueError(f"{reference}: category {category} is missing from the rescore")
        _merge_block(mine, block, f"by_category.{category}")
    new["schemes"] = [*old["schemes"], *(s for s in new["schemes"] if s not in old["schemes"])]
    new["merged_from"] = str(reference)
    (out / "summary.json").write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")

    def merge_lines(name: str, key: str, same: list[str]) -> None:
        mine, theirs = out / name, reference / name
        if not theirs.exists():
            return
        if not mine.exists():
            raise ValueError(f"{mine} is missing: rescore with details")
        merged = []
        with mine.open(encoding="utf-8") as f_new, theirs.open(encoding="utf-8") as f_old:
            for n, (a, b) in enumerate(zip(f_new, f_old, strict=True), start=1):
                ra, rb = json.loads(a), json.loads(b)
                if any(ra.get(k) != rb.get(k) for k in same):
                    raise ValueError(f"{name} line {n}: the runs disagree on {same}")
                ra[key] = _merged(rb[key], ra[key])
                merged.append(json.dumps(ra) + "\n")
        mine.write_text("".join(merged), encoding="utf-8")

    merge_lines("pairs.jsonl", "schemes", ["old", "new", "gt"])
    merge_lines("findings.jsonl", "outcomes", list(_RECORD_IDENTITY))
    return new


# -- checking against an earlier run ------------------------------------------------


def _same_counts(a: dict[str, Any], b: dict[str, Any], schemes: list[str]) -> bool:
    """Whether two totals blocks agree on the ground truth and on *schemes*."""
    if a["gt"] != b["gt"]:
        return False
    if any(a["schemes"].get(s) != b["schemes"].get(s) for s in schemes):
        return False
    return all(a.get(k) == b.get(k) for k in ("files", "renamed_files", "skipped_files"))


def check(rescored: Path, reference: Path) -> list[str]:
    """Differences between a rescored run and a reference run of the same recording."""
    problems: list[str] = []
    new = json.loads((rescored / "summary.json").read_text(encoding="utf-8"))
    old = json.loads((reference / "summary.json").read_text(encoding="utf-8"))
    common = [s for s in old["schemes"] if s in new["schemes"]]
    if not common:
        return ["no scheme in common"]
    if not _same_counts(new["totals"], old["totals"], common):
        problems.append("totals differ")
    for name in ("observations",):
        if new["collisions"][name] != old["collisions"][name]:
            problems.append(f"collisions.{name} differ")
    for s in common:
        if new["collisions"]["by_scheme"].get(s) != old["collisions"]["by_scheme"].get(s):
            problems.append(f"collisions of {s} differ")
    for category, block in old.get("by_category", {}).items():
        mine = new.get("by_category", {}).get(category)
        if mine is None or not _same_counts(mine["totals"], block["totals"], common):
            problems.append(f"by_category.{category} totals differ")
    for k in ("versions_scanned", "parse_failures", "commit_pairs"):
        if new.get(k) != old.get(k):
            problems.append(f"{k}: {new.get(k)} vs {old.get(k)}")
    with (
        (rescored / "pairs.jsonl").open(encoding="utf-8") as f_new,
        (reference / "pairs.jsonl").open(encoding="utf-8") as f_old,
    ):
        for n, (a, b) in enumerate(zip(f_new, f_old, strict=True), start=1):
            pa, pb = json.loads(a), json.loads(b)
            if (pa["old"], pa["new"]) != (pb["old"], pb["new"]) or not _same_counts(pa, pb, common):
                problems.append(f"pairs.jsonl line {n} differs")
                break
    new_f, old_f = rescored / "findings.jsonl", reference / "findings.jsonl"
    if new_f.exists() and old_f.exists():
        with new_f.open(encoding="utf-8") as f_new, old_f.open(encoding="utf-8") as f_old:
            for n, (a, b) in enumerate(zip(f_new, f_old, strict=True), start=1):
                ra, rb = json.loads(a), json.loads(b)
                ra["outcomes"] = {s: ra["outcomes"][s] for s in common}
                rb["outcomes"] = {s: rb["outcomes"][s] for s in common}
                if ra != rb:
                    problems.append(f"findings.jsonl line {n} differs")
                    break
    return problems


# -- command line --------------------------------------------------------------------


def add_parser(sub: Any) -> None:
    p = sub.add_parser("rescore", help="replay recorded observations with any schemes")
    p.add_argument("observations", type=Path, help="a recording, or a directory of them")
    p.add_argument("--out", type=Path, required=True, help="results directory")
    p.add_argument("--schemes", help="comma-separated schemes (default: the analyzer's)")
    p.add_argument("--only", help="comma-separated labels (default: all recordings)")
    p.add_argument(
        "--workdir",
        type=Path,
        default=HERE / ".repos",
        help="where the clones are (default: .repos; else the recorded path)",
    )
    p.add_argument("--jobs", type=int, default=4, help="recordings rescored in parallel")
    p.add_argument("--no-details", action="store_true", help="skip findings.jsonl")
    p.add_argument("--check", type=Path, help="results of an earlier run to compare with")
    p.add_argument(
        "--merge-from",
        type=Path,
        help="results of an earlier run of the same recording: keep its other schemes",
    )


def run(args: argparse.Namespace) -> None:
    found = recordings(args.observations)
    if args.only:
        wanted = {x.strip() for x in args.only.split(",") if x.strip()}
        found = [d for d in found if d.name in wanted]
    if not found:
        raise SystemExit(f"no recordings under {args.observations}")
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()] if args.schemes else None
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [
        (d, args.out / d.name, schemes, args.workdir, not args.no_details, args.merge_from)
        for d in found
    ]
    started = time.monotonic()
    failed = 0
    with ProcessPoolExecutor(max_workers=max(args.jobs, 1)) as pool:
        futures = {pool.submit(_run, job): job[0].name for job in jobs}
        for n, future in enumerate(as_completed(futures), start=1):
            label = futures[future]
            try:
                _, seconds = future.result()
            except Exception as exc:  # report it and rescore the others
                failed += 1
                print(
                    f"[{n}/{len(jobs)}] {label}: failed ({type(exc).__name__}: {exc})",
                    file=sys.stderr,
                )
                continue
            note = ""
            if args.check:
                problems = check(args.out / label, args.check / label)
                note = (
                    ", matches " + args.check.name
                    if not problems
                    else ", DIFFERS: " + "; ".join(problems)
                )
                failed += bool(problems)
            print(f"[{n}/{len(jobs)}] {label}: ok in {seconds:.1f}s{note}", file=sys.stderr)
    print(f"rescored {len(jobs)} recordings in {time.monotonic() - started:.0f}s", file=sys.stderr)
    if failed:
        sys.exit(1)
