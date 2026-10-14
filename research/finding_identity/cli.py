"""Command line: ``python -m research.finding_identity {replay,summarize,drift,drift-summary}``."""

from __future__ import annotations

import argparse
from pathlib import Path

from .drift import add_arguments as add_drift_arguments
from .drift import run as run_drift
from .gitrepo import GitRepo
from .replay import replay
from .scan import Scanner, rule_ids_for
from .schemes import ALL_SCHEMES
from .summarize import summarize, summarize_drift

HERE = Path(__file__).parent


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m research.finding_identity")
    sub = parser.add_subparsers(dest="command", required=True)

    rp = sub.add_parser("replay", help="replay a repository's history")
    rp.add_argument("repo", help="local repository path or a git URL to clone")
    rp.add_argument("--ref", default="HEAD", help="branch or commit to walk back from")
    rp.add_argument("--commits", type=int, default=200, help="number of commit pairs")
    rp.add_argument("--label", help="name for the results (default: repository name)")
    rp.add_argument("--out", type=Path, help="results directory")
    rp.add_argument("--workdir", type=Path, default=HERE / ".repos", help="where to clone")
    rp.add_argument(
        "--categories",
        default="security,performance,quality",
        help="comma-separated rule categories to run",
    )
    rp.add_argument("--details", action="store_true", help="write one record per finding")

    sp = sub.add_parser("summarize", help="print rate tables for one or more result dirs")
    sp.add_argument("results", nargs="+", type=Path)
    sp.add_argument("--csv", type=Path, help="also write the rows to this CSV file")

    add_drift_arguments(sub.add_parser("drift", help="score an anchor commit against later ones"))
    dp = sub.add_parser("drift-summary", help="print per-span rate tables for drift results")
    dp.add_argument("results", nargs="+", type=Path)
    dp.add_argument("--csv", type=Path, help="also write one row per span and scheme to this CSV")

    args = parser.parse_args(argv)
    if args.command == "drift":
        run_drift(args)
        return
    if args.command == "drift-summary":
        summarize_drift(args.results, args.csv)
        return
    if args.command == "summarize":
        summarize(args.results, args.csv)
        return

    ref = None if args.ref == "HEAD" else args.ref
    repo = GitRepo.open_or_clone(args.repo, args.workdir, depth=args.commits + 2, ref=ref)
    label = args.label or repo.path.name
    out = args.out or HERE / "results" / label
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    scanner = Scanner(rule_ids_for(categories), ALL_SCHEMES)
    try:
        replay(
            repo,
            ref=args.ref,
            commits=args.commits,
            scanner=scanner,
            schemes=ALL_SCHEMES,
            out_dir=out,
            label=label,
            categories=categories,
            details=args.details,
        )
    finally:
        repo.close()
    summarize([out])
