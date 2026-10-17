"""Corpus-level subcommands: ``batch``, ``corpus pin``, ``corpus check`` and ``stats``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .batch import BatchOptions, run_batch
from .corpus import CorpusEntry, load_corpus, measure, pin, save_corpus
from .stats import ALL, run_stats

HERE = Path(__file__).parent

Handler = Callable[[argparse.Namespace], None]


def register(sub: Any) -> dict[str, Handler]:
    """Add the subcommands to *sub* (an argparse subparsers object); return their handlers."""
    bp = sub.add_parser("batch", help="replay every repository of a corpus file")
    bp.add_argument("corpus", type=Path, help="corpus CSV (see corpus.csv)")
    bp.add_argument("--commits", type=int, default=200, help="commit pairs per repository")
    bp.add_argument("--jobs", type=int, default=4, help="repositories replayed in parallel")
    bp.add_argument("--out", type=Path, default=HERE / "results", help="results directory")
    bp.add_argument("--workdir", type=Path, default=HERE / ".repos", help="where to clone")
    bp.add_argument("--only", help="comma-separated labels to run (default: all)")
    bp.add_argument(
        "--categories",
        default="security,performance,quality",
        help="comma-separated rule categories to run",
    )
    bp.add_argument("--details", action="store_true", help="write one record per finding")
    bp.add_argument("--timeout", type=float, help="seconds allowed per repository")
    bp.add_argument("--force", action="store_true", help="rerun repositories already done")
    bp.add_argument(
        "--delete-clones", action="store_true", help="delete each clone after its replay"
    )

    cp = sub.add_parser("corpus", help="pin corpus commits or check the selection criteria")
    cp.add_argument("action", choices=["pin", "check"])
    cp.add_argument("corpus", type=Path)
    cp.add_argument("--workdir", type=Path, default=HERE / ".repos", help="where to clone")
    cp.add_argument("--only", help="comma-separated labels (default: all)")
    cp.add_argument("--write", action="store_true", help="check: write the measured columns back")

    st = sub.add_parser("stats", help="confidence intervals and spread over many replays")
    st.add_argument("results", nargs="+", type=Path, help="result directories or their parent")
    st.add_argument("--out", type=Path, default=HERE / "tables", help="where to write tables")
    st.add_argument("--corpus", type=Path, help="restrict to (and order by) this corpus")
    st.add_argument(
        "--scopes",
        default=f"{ALL},security",
        help=f"comma-separated scopes: {ALL!r} and/or rule categories",
    )
    st.add_argument("--resamples", type=int, default=10_000, help="bootstrap resamples")
    st.add_argument("--seed", type=int, default=20261014, help="bootstrap random seed")
    st.add_argument("--plot", action="store_true", help="box plot (needs matplotlib)")

    return {"batch": _batch, "corpus": _corpus, "stats": _stats}


def _select(entries: list[CorpusEntry], only: str | None) -> list[CorpusEntry]:
    if not only:
        return entries
    wanted = {x.strip() for x in only.split(",") if x.strip()}
    unknown = wanted - {e.label for e in entries}
    if unknown:
        raise SystemExit(f"unknown labels: {', '.join(sorted(unknown))}")
    return [e for e in entries if e.label in wanted]


def _batch(args: argparse.Namespace) -> None:
    entries = _select(load_corpus(args.corpus), args.only)
    unpinned = [e.label for e in entries if not e.sha]
    if unpinned:
        raise SystemExit(f"not pinned (run `corpus pin` first): {', '.join(unpinned)}")
    opts = BatchOptions(
        commits=args.commits,
        out=args.out,
        workdir=args.workdir,
        categories=args.categories,
        details=args.details,
        timeout=args.timeout,
        delete_clones=args.delete_clones,
    )
    statuses = run_batch(entries, opts, jobs=args.jobs, force=args.force)
    if any(s["status"] == "failed" for s in statuses):
        sys.exit(1)


def _corpus(args: argparse.Namespace) -> None:
    entries = load_corpus(args.corpus)
    chosen = _select(entries, args.only)
    if args.action == "pin":
        today = datetime.now(timezone.utc).date()
        for e in chosen:
            pin(e, today)
            print(f"{e.label}: {e.branch} @ {e.sha}")
        save_corpus(args.corpus, entries)
        return
    failures = 0
    for e in chosen:
        try:
            problems = measure(e, args.workdir)
        except Exception as exc:  # report it and check the others
            problems = [f"{type(exc).__name__}: {exc}"]
        failures += bool(problems)
        verdict = "ok" if not problems else "FAIL: " + "; ".join(problems)
        print(
            f"{e.label:<22} {e.commits_2y or '?':>5} commits/2y  py={e.py_files or '?':>5} "
            f"js={e.js_files or '?':>5}  {e.commit_date or '?'}  {verdict}"
        )
    if args.write:
        save_corpus(args.corpus, entries)
    print(f"{len(chosen) - failures}/{len(chosen)} meet the criteria (checked {date.today()})")
    if failures:
        sys.exit(1)


def _stats(args: argparse.Namespace) -> None:
    labels = [e.label for e in load_corpus(args.corpus)] if args.corpus else None
    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    run_stats(
        args.results,
        args.out,
        labels=labels,
        scopes=scopes,
        resamples=args.resamples,
        seed=args.seed,
        plot=args.plot,
    )
