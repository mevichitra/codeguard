"""Command line: ``python -m research.finding_identity <command>``.

Commands: replay, rescore, summarize, transform, drift, drift-summary, batch, corpus,
stats.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import commands, rescore, transform_cli
from .drift import add_arguments as add_drift_arguments
from .drift import run as run_drift
from .gitrepo import GitRepo
from .observations import ObservationWriter
from .replay import replay
from .scan import Scanner, rule_ids_for
from .schemes import ANALYZERS, schemes_for
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
    rp.add_argument(
        "--analyzer",
        choices=ANALYZERS,
        default="codeguard",
        help="what produces the findings (bandit and semgrep: see requirements.txt)",
    )
    rp.add_argument(
        "--semgrep-rules",
        type=Path,
        help="for --analyzer semgrep: a rules file or a rules repository checkout "
        "(default: semgrep_rules.yml)",
    )
    rp.add_argument(
        "--observations",
        type=Path,
        help="record every scanned version and commit pair here, for `rescore`",
    )
    rescore.add_parser(sub)

    sp = sub.add_parser("summarize", help="print rate tables for one or more result dirs")
    sp.add_argument("results", nargs="+", type=Path)
    sp.add_argument("--csv", type=Path, help="also write the rows to this CSV file")

    transform_cli.add_parser(sub)
    add_drift_arguments(sub.add_parser("drift", help="score an anchor commit against later ones"))
    dp = sub.add_parser("drift-summary", help="print per-span rate tables for drift results")
    dp.add_argument("results", nargs="+", type=Path)
    dp.add_argument("--csv", type=Path, help="also write one row per span and scheme to this CSV")

    corpus_commands = commands.register(sub)

    args = parser.parse_args(argv)
    if args.command == "transform":
        transform_cli.run(args)
        return
    if args.command in corpus_commands:
        corpus_commands[args.command](args)
        return
    if args.command == "drift":
        run_drift(args)
        return
    if args.command == "rescore":
        rescore.run(args)
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
    if args.analyzer != "codeguard" and not args.label:
        label = f"{label}-{args.analyzer}"
    out = args.out or HERE / "results" / label
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    schemes = schemes_for(args.analyzer)
    writer = ObservationWriter(args.observations) if args.observations else None
    scanner = Scanner(
        rule_ids_for(categories),
        schemes,
        analyzer=args.analyzer,
        semgrep_rules=args.semgrep_rules,
        record_to=writer,
    )
    try:
        replay(
            repo,
            ref=args.ref,
            commits=args.commits,
            scanner=scanner,
            schemes=schemes,
            out_dir=out,
            label=label,
            categories=categories,
            details=args.details,
            observations=writer,
        )
    finally:
        repo.close()
    (out / "analyzer.json").write_text(
        json.dumps(scanner.describe(), indent=2) + "\n", encoding="utf-8"
    )
    summarize([out])
