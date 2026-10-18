# SPDX-License-Identifier: Apache-2.0

"""Long-span baselines over the corpus: fetch deep clones, run drift mode, report.

The consecutive replays compare each commit with its parent. A baseline is usually
created once and compared with code many commits later, so this module runs drift mode
(:mod:`drift`) over the whole corpus, from several anchors per repository:

``python -m research.finding_identity.drift_kit fetch``
    makes clones deep enough for the oldest anchor (``.repos/deep/<label>``); the
    replay clones are shallow (202 first-parent commits) and are left alone.
``python -m research.finding_identity.drift_kit run``
    for each repository and each anchor *a* (first-parent commits behind the pinned
    commit), compares the anchor with the commits *k* steps after it, for every span
    *k*. With anchors 200, 300 and 400 and a window of 200, the three windows end 0, 100
    and 200 commits before the pinned commit.
``python -m research.finding_identity.drift_kit report``
    pools the anchors of each repository, then reports each scheme's rates per span
    with cluster-bootstrap intervals over repositories (``drift.csv``,
    ``numbers_drift.md``, ``fig_drift.pdf``).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import CorpusEntry, load_corpus
from .drift import DEFAULT_SPANS, drift
from .gitrepo import GitRepo
from .scan import Scanner, rule_ids_for
from .schemes import ALL_SCHEMES
from .stats import bootstrap_draws, cluster_bootstrap

HERE = Path(__file__).parent
DEFAULT_WORKDIR = HERE / ".repos" / "deep"
DEFAULT_ANCHORS = (200, 300, 400)
DEFAULT_WINDOW = 200
#: The schemes the paper reports, in its order.
REPORT_SCHEMES = ("line", "line_text", "github", "codeguard", "sonar", "sonar_branch", "bandit")
#: ``metric: (numerator, denominator)``; the ``_same_path`` and ``_renamed`` splits come
#: from the per-finding records.
METRICS = {
    "false_new": ("false_new", "known"),
    "false_new_edited": ("false_new_edited", "known_edited"),
    "hidden": ("false_known", "introduced"),
    "mispair": ("mispaired", "known"),
}
SPLITS = ("false_new_same_path", "false_new_renamed")


# -- fetch ------------------------------------------------------------------------


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True
    ).stdout


def first_parent_count(path: Path, sha: str) -> int:
    """First-parent commits behind and including *sha* in the clone at *path*."""
    return int(_git(path, "rev-list", "--first-parent", "--count", sha).strip())


def fetch(label: str, url: str, sha: str, workdir: Path, depth: int) -> int:
    """Clone *url* at *sha* with *depth* commits into ``workdir/label``.

    Fetches the pinned commit itself (GitHub serves commits by id), so the clone does not
    depend on where the branch has moved since. Returns the first-parent history length.
    """
    target = workdir / label
    if (target / ".git").exists():
        try:
            if first_parent_count(target, sha) >= depth:
                return first_parent_count(target, sha)
        except subprocess.CalledProcessError:
            pass
    else:
        target.mkdir(parents=True, exist_ok=True)
        _git(target, "init", "--quiet")
    _git(target, "fetch", "--quiet", "--no-tags", f"--depth={depth}", url, sha)
    _git(target, "update-ref", "refs/heads/pinned", sha)
    return first_parent_count(target, sha)


# -- run --------------------------------------------------------------------------


@dataclass(frozen=True)
class Task:
    label: str
    sha: str
    anchor: int
    window: int
    spans: tuple[int, ...]


def run_task(task: Task, workdir: Path, out: Path, categories: Sequence[str]) -> dict[str, Any]:
    """Drift mode for one anchor; returns a status record (``ok`` or ``skipped``)."""
    target = out / task.label / f"a{task.anchor}"
    if (target / "summary.json").exists():
        return {"label": task.label, "anchor": task.anchor, "status": "ok", "cached": True}
    repo = GitRepo(workdir / task.label)
    started = time.monotonic()
    try:
        history = repo.first_parent_history(task.sha, task.anchor + 1)
        if len(history) < task.anchor + 1:
            return {
                "label": task.label,
                "anchor": task.anchor,
                "status": "skipped",
                "reason": f"only {len(history) - 1} first-parent commits behind the pin",
            }
        end = history[task.window]  # the anchor is history[0]
        drift(
            repo,
            ref=end,
            anchor_back=task.window,
            spans=task.spans,
            scanner=Scanner(rule_ids_for(categories), ALL_SCHEMES),
            schemes=ALL_SCHEMES,
            out_dir=target,
            label=task.label,
            categories=categories,
            details=True,
        )
    finally:
        repo.close()
    return {
        "label": task.label,
        "anchor": task.anchor,
        "status": "ok",
        "seconds": round(time.monotonic() - started, 1),
    }


def tasks_for(
    corpus: Iterable[CorpusEntry],
    anchors: Sequence[int],
    window: int,
    spans: Sequence[int],
) -> list[Task]:
    if any(a < window for a in anchors) or max(spans) > window:
        raise ValueError("every anchor must be at least the window, and spans at most it")
    return [
        Task(r.label, r.sha, a, window, tuple(sorted(spans)))
        for r in corpus
        for a in sorted(anchors)
    ]


# -- report -----------------------------------------------------------------------


@dataclass
class Estimate:
    num: int
    den: int
    rate: float | None
    ci: tuple[float, float] | None
    repos: int


def load_drift_runs(results: Path) -> dict[str, list[Path]]:
    """``{label: [anchor result dirs]}`` for every finished anchor under *results*."""
    runs: dict[str, list[Path]] = {}
    for summary in sorted(results.glob("*/a*/summary.json")):
        runs.setdefault(summary.parent.parent.name, []).append(summary.parent)
    return runs


def _split_counts(run_dir: Path, scheme: str) -> dict[tuple[int, str], list[int]]:
    """``{(span, split): [false_new, known]}`` from one anchor's findings.jsonl."""
    out: dict[tuple[int, str], list[int]] = {}
    path = run_dir / "findings.jsonl"
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["truth"] != "known":
                continue
            split = SPLITS[1] if rec["old_path"] != rec["path"] else SPLITS[0]
            cell = out.setdefault((rec["span"], split), [0, 0])
            cell[0] += rec["outcomes"][scheme] == "false_new"
            cell[1] += 1
    return out


def repo_counts(
    runs: dict[str, list[Path]], schemes: Sequence[str]
) -> tuple[list[str], list[int], dict[tuple[int, str, str], list[tuple[int, int]]]]:
    """Counts per repository, pooled over its anchors.

    Returns the labels, the spans every anchor has, and
    ``{(span, scheme, metric): [(num, den) per repository]}``.
    """
    labels = sorted(runs)
    summaries = {
        label: [json.loads((d / "summary.json").read_text(encoding="utf-8")) for d in runs[label]]
        for label in labels
    }
    spans = sorted(
        set.intersection(
            *({e["span"] for e in s["spans"]} for ss in summaries.values() for s in ss)
        )
    )
    table: dict[tuple[int, str, str], list[tuple[int, int]]] = {}
    for label in labels:
        splits = {s: [_split_counts(d, s) for d in runs[label]] for s in schemes}
        for k in spans:
            entries = [e for s in summaries[label] for e in s["spans"] if e["span"] == k]
            for scheme in schemes:
                for metric, (num_key, den_key) in METRICS.items():
                    num = sum(e["totals"]["schemes"][scheme][num_key] for e in entries)
                    den = sum(e["totals"]["gt"][den_key] for e in entries)
                    table.setdefault((k, scheme, metric), []).append((num, den))
                for split in SPLITS:
                    cells = [c.get((k, split), [0, 0]) for c in splits[scheme]]
                    pair = (sum(c[0] for c in cells), sum(c[1] for c in cells))
                    table.setdefault((k, scheme, split), []).append(pair)
            gt_rows = {
                "anchor_findings": sum(e["totals"]["gt"]["old"] for e in entries),
                "persisting": sum(e["totals"]["gt"]["known"] for e in entries),
                "persisting_edited": sum(e["totals"]["gt"]["known_edited"] for e in entries),
                "introduced": sum(e["totals"]["gt"]["introduced"] for e in entries),
                "chains_alive": sum(e["chains"]["alive"] for e in entries),
                "renamed_files": sum(e["totals"]["renamed_files"] for e in entries),
                "anchors": len(entries),
            }
            for key, value in gt_rows.items():
                table.setdefault((k, "_gt", key), []).append((value, 1))
    return labels, spans, table


def estimate(pairs: Sequence[tuple[int, int]], draws: Sequence[Sequence[int]]) -> Estimate:
    num = sum(n for n, _ in pairs)
    den = sum(d for _, d in pairs)
    return Estimate(
        num,
        den,
        num / den if den else None,
        cluster_bootstrap(pairs, draws)["pooled"],
        sum(1 for _, d in pairs if d),
    )


def estimates(
    table: dict[tuple[int, str, str], list[tuple[int, int]]],
    n_repos: int,
    resamples: int,
    seed: int,
) -> dict[tuple[int, str, str], Estimate]:
    draws = bootstrap_draws(n_repos, resamples, seed)
    return {
        key: estimate(pairs, draws) for key, pairs in table.items() if not key[1].startswith("_")
    }


def write_csv(path: Path, est: dict[tuple[int, str, str], Estimate]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["span", "scheme", "metric", "num", "den", "rate", "ci_lo", "ci_hi", "repos"])
        for (k, scheme, metric), e in sorted(est.items()):
            lo, hi = e.ci if e.ci else (None, None)
            w.writerow([k, scheme, metric, e.num, e.den, e.rate, lo, hi, e.repos])


def _pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def _cell(e: Estimate | None) -> str:
    if e is None or e.rate is None:
        return "n/a"
    ci = f" [{_pct(e.ci[0])}, {_pct(e.ci[1])}]" if e.ci else ""
    return f"{_pct(e.rate)}{ci}"


def numbers_markdown(
    labels: Sequence[str],
    spans: Sequence[int],
    table: dict[tuple[int, str, str], list[tuple[int, int]]],
    est: dict[tuple[int, str, str], Estimate],
    schemes: Sequence[str],
    source: Path,
) -> str:
    anchors = sum(n for n, _ in table[(spans[0], "_gt", "anchors")])
    out = [
        "# Long-span numbers",
        "",
        "Generated by `research/finding_identity/drift_kit.py`; do not edit by hand. Rates in",
        "percent: pooled over repositories (each repository's anchors summed first), with the",
        "95% cluster-bootstrap interval over repositories.",
        "",
        f"Source: `{source}`. {len(labels)} repositories, {anchors} anchors.",
        "",
        "## Ground truth per span",
        "",
        "| span | anchor findings | persisting | of them edited | introduced | renamed files |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for k in spans:

        def total(key: str, k: int = k) -> int:
            return sum(n for n, _ in table[(k, "_gt", key)])

        edited = total("persisting_edited")
        persisting = total("persisting")
        share = f" ({100 * edited / persisting:.1f}%)" if persisting else ""
        out.append(
            f"| {k} | {total('anchor_findings'):,} | {persisting:,} | {edited:,}{share} | "
            f"{total('introduced'):,} | {total('renamed_files'):,} |"
        )
    for metric, title in (
        ("false_new", "False-new rate"),
        ("false_new_same_path", "False-new rate, files that kept their path"),
        ("false_new_renamed", "False-new rate, renamed files"),
        ("false_new_edited", "False-new rate, persisting findings whose line was edited"),
        ("hidden", "Hidden rate"),
        ("mispair", "Mispair rate"),
    ):
        out += [
            "",
            f"## {title}",
            "",
            "| scheme | " + " | ".join(f"k = {k}" for k in spans) + " |",
            "|---|" + "---:|" * len(spans),
        ]
        for scheme in schemes:
            cells = [_cell(est.get((k, scheme, metric))) for k in spans]
            out.append(f"| `{scheme}` | " + " | ".join(cells) + " |")
        dens = [est[(k, schemes[0], metric)].den for k in spans if (k, schemes[0], metric) in est]
        out += ["", "Denominators: " + ", ".join(f"{d:,}" for d in dens) + "."]
    return "\n".join(out) + "\n"


#: Categorical slots 1-7 of the reference palette (light mode), in fixed order.
_SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6")
_MARKERS = ("o", "s", "^", "D", "v", "P", "X")
_INK = "#0b0b0b"
_INK_SECONDARY = "#52514e"
_GRID = "#e1e0d9"
_AXIS = "#c3c2b7"


def figure(
    est: dict[tuple[int, str, str], Estimate],
    spans: Sequence[int],
    schemes: Sequence[str],
    path: Path,
) -> bool:
    """False-new and hidden rate against span, one line per scheme; False without
    matplotlib. The y axes are linear up to 1% and logarithmic above, so that ``line``
    (about half of all findings) and rates of zero fit on the same axes."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
    except ImportError:
        print("matplotlib is not installed; skipping fig_drift.pdf", file=sys.stderr)
        return False
    matplotlib.rcParams.update({"pdf.fonttype": 42, "font.size": 7, "axes.linewidth": 0.6})
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 2.0), sharex=True)
    xs = list(range(len(spans)))
    for ax, metric, title in (
        (axes[0], "false_new", "false new (%)"),
        (axes[1], "hidden", "hidden (%)"),
    ):
        for s, scheme in enumerate(schemes):
            ys = []
            for k in spans:
                e = est.get((k, scheme, metric))
                ys.append(100 * e.rate if e and e.rate is not None else float("nan"))
            # sonar_branch differs from sonar only on renamed files: dashed, so that
            # sonar stays visible where the two coincide.
            dashed = scheme == "sonar_branch"
            ax.plot(
                xs,
                ys,
                color=_SERIES[s % len(_SERIES)],
                marker=_MARKERS[s % len(_MARKERS)],
                markersize=2.6 if dashed else 3.2,
                linewidth=0.9 if dashed else 1.0,
                linestyle=(0, (2.5, 1.5)) if dashed else "-",
                label=scheme,
                zorder=3 if dashed else 2,
            )
        ax.set_yscale("symlog", linthresh=1, linscale=0.6)
        ax.set_ylim(-0.08, 130)
        ax.yaxis.set_major_locator(FixedLocator([0, 1, 3, 10, 30, 100]))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.set_xticks(xs, [str(k) for k in spans])
        ax.set_title(title, color=_INK, fontsize=7, loc="left")
        ax.grid(axis="y", color=_GRID, linewidth=0.5)
        ax.set_axisbelow(True)
        ax.tick_params(colors=_INK_SECONDARY, length=2)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(_AXIS)
    for ax in axes:
        ax.set_xlabel("span k (commits)", color=_INK_SECONDARY, labelpad=2)
    handles, names = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        names,
        loc="upper center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 0.02),
        handlelength=2.2,
        columnspacing=1.0,
        labelcolor=_INK,
    )
    fig.tight_layout(w_pad=1.0, rect=(0, 0.02, 1, 1))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return True


def report(results: Path, out: Path, *, resamples: int, seed: int) -> None:
    runs = load_drift_runs(results)
    if not runs:
        raise SystemExit(f"no drift results under {results}")
    labels, spans, table = repo_counts(runs, REPORT_SCHEMES)
    est = estimates(table, len(labels), resamples, seed)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "drift.csv", est)
    text = numbers_markdown(labels, spans, table, est, REPORT_SCHEMES, results)
    (out / "numbers_drift.md").write_text(text, encoding="utf-8")
    figure(est, spans, REPORT_SCHEMES, out / "fig_drift.pdf")
    print(f"wrote drift.csv, numbers_drift.md and fig_drift.pdf to {out}")


# -- command line -----------------------------------------------------------------


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m research.finding_identity.drift_kit")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("fetch", "run"):
        p = sub.add_parser(name)
        p.add_argument("--corpus", type=Path, default=HERE / "corpus.csv")
        p.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR)
        p.add_argument("--labels", help="comma-separated subset of the corpus")
        p.add_argument("--anchors", default=",".join(map(str, DEFAULT_ANCHORS)))
        p.add_argument("--jobs", type=int, default=4)
    run_p = sub.choices["run"]
    run_p.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    run_p.add_argument("--spans", default=",".join(map(str, DEFAULT_SPANS)))
    run_p.add_argument("--categories", default="security,performance,quality")
    run_p.add_argument("--out", type=Path, required=True)
    rep = sub.add_parser("report")
    rep.add_argument("results", type=Path)
    rep.add_argument("--out", type=Path, default=HERE / "paper")
    rep.add_argument("--resamples", type=int, default=10_000)
    rep.add_argument("--seed", type=int, default=20261014)
    args = ap.parse_args(argv)

    if args.command == "report":
        report(args.results, args.out, resamples=args.resamples, seed=args.seed)
        return
    corpus = load_corpus(args.corpus)
    if args.labels:
        wanted = set(args.labels.split(","))
        corpus = [r for r in corpus if r.label in wanted]
    anchors = _ints(args.anchors)
    if args.command == "fetch":
        depth = max(anchors) + 2
        with ProcessPoolExecutor(args.jobs) as pool:
            futures = {
                pool.submit(fetch, r.label, r.url, r.sha, args.workdir, depth): r for r in corpus
            }
            for fut in as_completed(futures):
                label = futures[fut].label
                try:
                    print(f"{label}: {fut.result()} first-parent commits", flush=True)
                except subprocess.CalledProcessError as exc:
                    print(f"{label}: fetch failed: {exc.stderr}", file=sys.stderr, flush=True)
        return
    tasks = tasks_for(corpus, anchors, args.window, _ints(args.spans))
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    statuses = []
    with ProcessPoolExecutor(args.jobs) as pool:
        runs = [pool.submit(run_task, t, args.workdir, args.out, categories) for t in tasks]
        for done in as_completed(runs):
            status = done.result()
            statuses.append(status)
            print(json.dumps(status), flush=True)
    statuses.sort(key=lambda s: (s["label"], s["anchor"]))
    (args.out / "status.json").write_text(json.dumps(statuses, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
