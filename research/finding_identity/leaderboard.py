# SPDX-License-Identifier: Apache-2.0

"""Leaderboard: every identity scheme against the best one, on every metric.

``python -m research.finding_identity.leaderboard --codeguard <results> [--bandit ...]
[--semgrep ...] [--transform <dir>] [--drift <dir>] --out leaderboard.md`` ranks the
schemes of each analyzer's replays on the RQ1 metrics of :mod:`paper_kit` (pooled rate
with its cluster-bootstrap interval), gives each scheme's paired difference to the best
scheme on the same findings, and counts on how many metrics each scheme is best or not
distinguishable from the best (the paired interval includes zero). Lower is better on
every metric. With ``--transform`` and ``--drift`` it adds the RQ2 matrix and the
long-span rates, ranked the same way. ``--repos`` restricts the replays to a list of
labels, so a scheme designed on one half of the corpus can be scored on the other.

The estimates reuse :mod:`paper_kit`, :mod:`gate`, :mod:`stats` and :mod:`drift_kit`:
nothing here computes a rate of its own.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import drift_kit
from .corpus import load_corpus
from .paper_kit import (
    CODEGUARD_SECURITY_PREFIX,
    DUPLICATES,
    TABLE_SCHEMES,
    Estimate,
    estimate,
    load_matrices,
    load_runs,
    paired_difference,
    repo_table,
    rq2_estimates,
)
from .stats import bootstrap_draws

HERE = Path(__file__).parent

#: The RQ1 columns, in order: (metric, heading).
COLUMNS = (
    ("false_new", "false new"),
    ("false_new_same_path", "same path"),
    ("false_new_renamed", "renamed"),
    ("hidden", "hidden"),
    ("hidden_silent", "hidden, silent"),
    ("mispair", "mispaired"),
    ("collision", "collisions"),
    ("gate_miss", "gate miss"),
    ("gate_false_alarm", "gate alarm"),
)
TITLES = {
    "codeguard": "CodeGuard findings",
    "codeguard_security": "CodeGuard findings, security rules only",
    "bandit": "Bandit findings",
    "semgrep": "Semgrep findings",
}


@dataclass(frozen=True)
class Row:
    """One scheme's standing on one metric."""

    estimate: Estimate
    rank: int | None
    best: str | None
    #: ``rate - rate(best)`` in points, with its paired interval; ``None`` for the best.
    difference: tuple[float | None, tuple[float, float] | None] | None

    @property
    def is_best(self) -> bool:
        return self.rank == 1

    @property
    def ties_best(self) -> bool:
        """Best, or not distinguishable from the best (the paired interval holds 0)."""
        if self.is_best:
            return True
        if self.difference is None or self.difference[1] is None:
            return False
        lo, hi = self.difference[1]
        return lo <= 0 <= hi


@dataclass(frozen=True)
class Board:
    title: str
    repos: int
    schemes: tuple[str, ...]
    metrics: tuple[str, ...]
    rows: dict[tuple[str, str], Row]

    def summary(self, scheme: str) -> tuple[int, int, int]:
        """(best on, ties the best on, metrics ranked) for *scheme*."""
        ranked = [self.rows[(scheme, m)] for m in self.metrics if self.rows[(scheme, m)].rank]
        return (
            sum(r.is_best for r in ranked),
            sum(r.ties_best for r in ranked),
            len(ranked),
        )


def _rank(rates: dict[str, float]) -> tuple[dict[str, int], str | None]:
    """Dense ranks by rate, ties sharing a rank; and the best scheme (lowest, first by name)."""
    if not rates:
        return {}, None
    order = sorted(rates, key=lambda s: (rates[s], s))
    ranks: dict[str, int] = {}
    rank, previous = 0, None
    for s in order:
        if rates[s] != previous:
            rank += 1
            previous = rates[s]
        ranks[s] = rank
    return ranks, order[0]


def board_from_table(
    title: str,
    table: Mapping[tuple[str, str], Sequence[tuple[int, int]]],
    schemes: Sequence[str],
    metrics: Sequence[str],
    draws: Sequence[Sequence[int]],
    repos: int,
) -> Board:
    """Rank *schemes* on *metrics* from per-repository ``(num, den)`` pairs."""
    rows: dict[tuple[str, str], Row] = {}
    for metric in metrics:
        est = {s: estimate(table[(s, metric)], draws) for s in schemes if (s, metric) in table}
        rates = {s: e.rate for s, e in est.items() if e.rate is not None}
        ranks, best = _rank(rates)
        for s in schemes:
            if s not in est:
                continue
            diff = None
            if best is not None and s in rates and s != best:
                value, ci = paired_difference(table[(s, metric)], table[(best, metric)], draws)
                diff = (
                    None if value is None else 100 * value,
                    None if ci is None else (100 * ci[0], 100 * ci[1]),
                )
            rows[(s, metric)] = Row(est[s], ranks.get(s), best, diff)
    present = tuple(s for s in schemes if any((s, m) in rows for m in metrics))
    return Board(title, repos, present, tuple(metrics), rows)


def rq1_board(
    title: str,
    results: Path,
    labels: Sequence[str],
    schemes: Sequence[str] | None,
    *,
    exclude: frozenset[str] = frozenset(),
    prefix: str = "",
    resamples: int,
    seed: int,
) -> Board | None:
    wanted = [x for x in labels if (results / x / "summary.json").exists()]
    if not wanted:
        return None
    runs = load_runs(results, wanted, exclude, prefix)
    recorded = [
        s for s in runs[0].summary["schemes"] if all(s in r.summary["schemes"] for r in runs)
    ]
    chosen = [s for s in (schemes or scheme_order(recorded)) if s in recorded]
    draws = bootstrap_draws(len(runs), resamples, seed)
    table = repo_table(runs, chosen)
    return board_from_table(title, table, chosen, [m for m, _ in COLUMNS], draws, len(runs))


def scheme_order(recorded: Sequence[str]) -> list[str]:
    """The paper's schemes first, then whatever else the replay recorded."""
    return [
        *(s for s in TABLE_SCHEMES if s in recorded),
        *(s for s in recorded if s not in TABLE_SCHEMES),
    ]


def rq2_board(
    transform: Path,
    labels: Sequence[str],
    schemes: Sequence[str] | None,
    *,
    resamples: int,
    seed: int,
) -> tuple[Board, list[str]] | None:
    """The invariance matrix as a board: one metric per transformation (false new, or
    hidden for the duplicates)."""
    matrices = load_matrices(transform, labels)
    if not matrices:
        return None
    recorded = sorted({row["scheme"] for rows in matrices.values() for row in rows})
    chosen = [s for s in (schemes or scheme_order(recorded)) if s in recorded]
    est = rq2_estimates(matrices, chosen, resamples, seed)
    transforms = list(dict.fromkeys(k[0] for k in est))
    # Rebuild the per-repository pairs so that ranks and differences share the resamples.
    order = list(matrices)
    draws = bootstrap_draws(len(order), resamples, seed)
    table: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for i, label in enumerate(order):
        for row in matrices[label]:
            if row["scheme"] not in chosen:
                continue
            duplicate = row["transform"] in DUPLICATES
            num, den = ("hidden", "introduced") if duplicate else ("false_new", "target_known")
            pairs = table.setdefault((row["scheme"], row["transform"]), [(0, 0)] * len(order))
            pairs[i] = (int(row[num]), int(row[den]))
    board = board_from_table(
        "Controlled transformations", table, chosen, transforms, draws, len(order)
    )
    return board, transforms


def drift_board(
    drift: Path, schemes: Sequence[str] | None, *, resamples: int, seed: int
) -> tuple[Board, int] | None:
    """False-new and hidden rates at the longest span, ranked."""
    runs = drift_kit.load_drift_runs(drift)
    if not runs:
        return None
    first = next(iter(runs.values()))[0] / "summary.json"
    recorded = list(json.loads(first.read_text(encoding="utf-8"))["spans"][0]["totals"]["schemes"])
    chosen = [s for s in (schemes or scheme_order(recorded)) if s in recorded]
    labels, spans, table = drift_kit.repo_counts(runs, chosen)
    k = spans[-1]
    draws = bootstrap_draws(len(labels), resamples, seed)
    flat = {(s, m): table[(k, s, m)] for s in chosen for m in ("false_new", "hidden")}
    board = board_from_table(
        f"Long spans, k = {k}", flat, chosen, ["false_new", "hidden"], draws, len(labels)
    )
    return board, k


# -- markdown -------------------------------------------------------------------------


def _pct(x: float | None, digits: int = 2) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def _cell(row: Row | None) -> str:
    if row is None or row.estimate.rate is None:
        return "n/a"
    e = row.estimate
    text = _pct(e.rate)
    if e.ci:
        text += f" ({_pct(e.ci[0])}, {_pct(e.ci[1])})"
    return f"**{text}**" if row.is_best else text


def _diff_cell(row: Row | None) -> str:
    if row is None or row.rank is None:
        return "n/a"
    if row.is_best:
        return "best"
    if row.difference is None or row.difference[0] is None:
        return "n/a"
    value, ci = row.difference
    text = f"{value:+.2f}"
    if ci:
        text += f" [{ci[0]:+.2f}, {ci[1]:+.2f}]"
    return text + ("" if row.ties_best else " ✱")


def board_markdown(board: Board, headings: dict[str, str] | None = None) -> list[str]:
    headings = headings or dict(COLUMNS)
    head = "| scheme | " + " | ".join(headings.get(m, m) for m in board.metrics) + " | best on |"
    sep = "|---|" + "---:|" * len(board.metrics) + "---|"
    out = [f"## {board.title} ({board.repos} repositories)", "", head, sep]
    for s in board.schemes:
        best, ties, n = board.summary(s)
        cells = [_cell(board.rows.get((s, m))) for m in board.metrics]
        out.append(f"| `{s}` | " + " | ".join(cells) + f" | {best} of {n} (ties {ties}) |")
    out += [
        "",
        "Difference to the best scheme on the same findings, in points, with its paired",
        "95% interval; ✱: the interval excludes 0, so the scheme is worse than the best.",
        "",
        head.replace(" | best on |", " |"),
        "|---|" + "---:|" * len(board.metrics),
    ]
    for s in board.schemes:
        cells = [_diff_cell(board.rows.get((s, m))) for m in board.metrics]
        out.append(f"| `{s}` | " + " | ".join(cells) + " |")
    out.append("")
    return out


def markdown(boards: Sequence[tuple[Board, dict[str, str] | None]], sources: Sequence[str]) -> str:
    out = [
        "# Leaderboard",
        "",
        "Pooled rates in percent with 95% cluster-bootstrap intervals over repositories;",
        "lower is better everywhere. The best scheme per column is in bold. *Best on*: columns",
        "where the scheme ranks first; *ties*: columns where it is best or its paired difference",
        "to the best includes 0.",
        "",
        "Sources: " + "; ".join(sources) + ".",
        "",
    ]
    for board, headings in boards:
        out += board_markdown(board, headings)
    return "\n".join(out).rstrip("\n") + "\n"


# -- command line ---------------------------------------------------------------------


def read_labels(path: Path) -> list[str]:
    """Repository labels from a file, one per line; ``#`` starts a comment."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.split("#", 1)[0].strip()
        if text:
            out.append(text)
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m research.finding_identity.leaderboard")
    ap.add_argument("--codeguard", type=Path, help="replay results with CodeGuard findings")
    ap.add_argument("--bandit", type=Path, help="replay results with Bandit findings")
    ap.add_argument("--bandit-exclude", default="B101", help="Bandit rules left out")
    ap.add_argument("--semgrep", type=Path, help="replay results with Semgrep findings")
    ap.add_argument("--transform", type=Path, help="directory of transform-<label> results")
    ap.add_argument("--drift", type=Path, help="long-span results (drift_kit run)")
    ap.add_argument("--corpus", type=Path, default=HERE / "corpus.csv")
    ap.add_argument("--repos", type=Path, help="file of labels: score only these repositories")
    ap.add_argument("--schemes", help="comma-separated schemes (default: all recorded)")
    ap.add_argument("--resamples", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--out", type=Path, default=HERE / "paper" / "leaderboard.md")
    args = ap.parse_args(argv)

    labels = [e.label for e in load_corpus(args.corpus)]
    if args.repos:
        chosen = set(read_labels(args.repos))
        labels = [x for x in labels if x in chosen]
    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()] if args.schemes else None
    exclude = frozenset(x.strip() for x in args.bandit_exclude.split(",") if x.strip())
    boards: list[tuple[Board, dict[str, str] | None]] = []
    sources: list[str] = []
    opts = {"resamples": args.resamples, "seed": args.seed}
    jobs: list[tuple[str, Path | None, frozenset[str], str]] = [
        ("codeguard", args.codeguard, frozenset(), ""),
        ("codeguard_security", args.codeguard, frozenset(), CODEGUARD_SECURITY_PREFIX),
        ("bandit", args.bandit, exclude, ""),
        ("semgrep", args.semgrep, frozenset(), ""),
    ]
    for name, path, leave_out, prefix in jobs:
        if path is None:
            continue
        board = rq1_board(
            TITLES[name], path, labels, schemes, exclude=leave_out, prefix=prefix, **opts
        )
        if board is not None:
            boards.append((board, None))
            sources.append(f"{TITLES[name]}: `{path}`")
    if args.transform:
        rq2 = rq2_board(args.transform, labels, schemes, **opts)
        if rq2 is not None:
            board, transforms = rq2
            boards.append((board, {t: t.replace("_", " ") for t in transforms}))
            sources.append(f"transformations: `{args.transform}`")
    if args.drift:
        long = drift_board(args.drift, schemes, **opts)
        if long is not None:
            board, k = long
            boards.append(
                (board, {"false_new": f"false new, k = {k}", "hidden": f"hidden, k = {k}"})
            )
            sources.append(f"long spans: `{args.drift}`")
    if not boards:
        raise SystemExit(
            "nothing to rank: give --codeguard, --bandit, --semgrep, --transform or --drift"
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown(boards, sources), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
