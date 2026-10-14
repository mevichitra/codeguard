"""Statistics over many replays: confidence intervals, per-repository spread, CSV tables.

For every scope (all findings, and each requested rule category such as ``security``),
scheme and metric this reports:

- the **pooled** (micro) rate, sum of numerators over sum of denominators, with a
  **Wilson** 95% interval. Wilson treats findings as independent, which they are not
  (findings in one repository are correlated), so it is too narrow for the corpus;
- a **cluster bootstrap** 95% interval: repositories are resampled with replacement and
  the pooled rate recomputed, which respects the correlation within a repository;
- the **macro** rate, the mean of the per-repository rates, with its own cluster
  bootstrap interval;
- the **median** and **interquartile range** of the per-repository rates.

Repositories whose denominator is zero have no rate: they count towards the pooled sums
(adding nothing) but not towards the macro rate, median or quartiles.

Metrics (numerator / denominator):

- ``false_new``         false_new / known            persisting findings reported as new
- ``false_new_moved``   false_new_equal / known_equal   ...whose line was unchanged
- ``false_new_edited``  false_new_edited / known_edited ...whose line was edited
- ``hidden``            false_known / introduced     new findings the scheme hides
- ``mispair``           mispaired / known            persisting findings tied to the wrong one
- ``collision``         colliding / observations     findings sharing a key in a file version
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Z95 = 1.959963984540054

METRICS: dict[str, tuple[str, str]] = {
    "false_new": ("false_new", "known"),
    "false_new_moved": ("false_new_equal", "known_equal"),
    "false_new_edited": ("false_new_edited", "known_edited"),
    "hidden": ("false_known", "introduced"),
    "mispair": ("mispaired", "known"),
    "collision": ("collisions", "observations"),
}

ALL = "all"


# ---------------------------------------------------------------------------
# Elementary statistics
# ---------------------------------------------------------------------------


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval for *k* successes in *n* trials (``None`` if ``n == 0``)."""
    if n <= 0:
        return None
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def quantile(values: Sequence[float], q: float) -> float:
    """The *q* quantile with linear interpolation (Hyndman and Fan type 7, numpy's default)."""
    if not values:
        raise ValueError("quantile of an empty sequence")
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def pooled_rate(pairs: Iterable[tuple[int, int]]) -> float | None:
    """Micro average: total numerator over total denominator."""
    nums, dens = 0, 0
    for n, d in pairs:
        nums += n
        dens += d
    return ratio(nums, dens)


def macro_rate(pairs: Iterable[tuple[int, int]]) -> float | None:
    """Mean of the per-repository rates, over repositories with a non-zero denominator."""
    rates = [n / d for n, d in pairs if d]
    return sum(rates) / len(rates) if rates else None


def bootstrap_draws(n_clusters: int, n_resamples: int, seed: int) -> list[list[int]]:
    """Index lists for a cluster bootstrap; shared by every table so draws are paired."""
    rng = random.Random(seed)  # noqa: S311  (reproducible resampling, not security)
    return [[rng.randrange(n_clusters) for _ in range(n_clusters)] for _ in range(n_resamples)]


def cluster_bootstrap(
    pairs: Sequence[tuple[int, int]],
    draws: Sequence[Sequence[int]],
    *,
    level: float = 0.95,
) -> dict[str, tuple[float, float] | None]:
    """Percentile intervals of the pooled and macro rates over resampled repositories.

    Resamples in which the statistic is undefined (no denominator) are dropped.
    """
    pooled: list[float] = []
    macro: list[float] = []
    for draw in draws:
        chosen = [pairs[i] for i in draw]
        p = pooled_rate(chosen)
        if p is not None:
            pooled.append(p)
        m = macro_rate(chosen)
        if m is not None:
            macro.append(m)
    tail = (1 - level) / 2

    def interval(xs: list[float]) -> tuple[float, float] | None:
        return (quantile(xs, tail), quantile(xs, 1 - tail)) if xs else None

    return {"pooled": interval(pooled), "macro": interval(macro)}


# ---------------------------------------------------------------------------
# Reading summaries
# ---------------------------------------------------------------------------


def load_summaries(
    paths: Sequence[Path], labels: Sequence[str] | None = None
) -> list[dict[str, Any]]:
    """Summaries from result directories, or from directories of result directories.

    With *labels*, keep only those repositories, in that order.
    """
    found: dict[str, dict[str, Any]] = {}
    for path in paths:
        candidates = [path] if (path / "summary.json").exists() else sorted(path.iterdir())
        for d in candidates:
            f = d / "summary.json"
            if d.is_dir() and not d.name.startswith("_") and f.exists():
                s = json.loads(f.read_text(encoding="utf-8"))
                found[s.get("label") or d.name] = s
    if labels is None:
        return list(found.values())
    missing = [x for x in labels if x not in found]
    if missing:
        print(f"no results for: {', '.join(missing)}", file=sys.stderr)
    return [found[x] for x in labels if x in found]


def scope_block(summary: dict[str, Any], scope: str) -> dict[str, Any] | None:
    """The ``{"totals", "collisions"}`` block of *scope*, or ``None`` if not recorded."""
    if scope == ALL:
        return summary
    block: dict[str, Any] | None = summary.get("by_category", {}).get(scope)
    return block


def counts(block: dict[str, Any], scheme: str, metric: str) -> tuple[int, int]:
    """``(numerator, denominator)`` of *metric* for *scheme* in a summary block."""
    num_key, den_key = METRICS[metric]
    if metric == "collision":
        coll = block["collisions"]
        return int(coll["by_scheme"][scheme]), int(coll["observations"])
    totals = block["totals"]
    return int(totals["schemes"][scheme][num_key]), int(totals["gt"][den_key])


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


@dataclass
class Tables:
    pooled: list[dict[str, Any]]
    per_repo: list[dict[str, Any]]
    repos: list[dict[str, Any]]


def build_tables(
    summaries: Sequence[dict[str, Any]],
    *,
    scopes: Sequence[str] = (ALL, "security"),
    resamples: int = 10_000,
    seed: int = 20261014,
) -> Tables:
    schemes = list(summaries[0]["totals"]["schemes"]) if summaries else []
    draws = bootstrap_draws(len(summaries), resamples, seed) if summaries else []
    pooled_rows: list[dict[str, Any]] = []
    per_repo_rows: list[dict[str, Any]] = []
    for scope in scopes:
        blocks = [scope_block(s, scope) for s in summaries]
        missing = [s["label"] for s, b in zip(summaries, blocks, strict=True) if b is None]
        if missing:
            print(
                f"scope {scope!r} not recorded for {', '.join(missing)}; skipping it",
                file=sys.stderr,
            )
            continue
        for scheme in schemes:
            for metric in METRICS:
                pairs = [counts(b, scheme, metric) for b in blocks if b is not None]
                for s, (num, den) in zip(summaries, pairs, strict=True):
                    per_repo_rows.append(
                        {
                            "scope": scope,
                            "label": s["label"],
                            "scheme": scheme,
                            "metric": metric,
                            "num": num,
                            "den": den,
                            "rate": ratio(num, den),
                        }
                    )
                pooled_rows.append(_pooled_row(scope, scheme, metric, pairs, draws))
    return Tables(pooled_rows, per_repo_rows, _repo_rows(summaries, scopes))


def _pooled_row(
    scope: str,
    scheme: str,
    metric: str,
    pairs: Sequence[tuple[int, int]],
    draws: Sequence[Sequence[int]],
) -> dict[str, Any]:
    num = sum(n for n, _ in pairs)
    den = sum(d for _, d in pairs)
    rates = [n / d for n, d in pairs if d]
    ci = wilson(num, den)
    boot = cluster_bootstrap(pairs, draws)
    return {
        "scope": scope,
        "scheme": scheme,
        "metric": metric,
        "repos": len(pairs),
        "repos_with_rate": len(rates),
        "num": num,
        "den": den,
        "pooled": ratio(num, den),
        "wilson_lo": ci[0] if ci else None,
        "wilson_hi": ci[1] if ci else None,
        "boot_lo": boot["pooled"][0] if boot["pooled"] else None,
        "boot_hi": boot["pooled"][1] if boot["pooled"] else None,
        "macro": macro_rate(pairs),
        "macro_boot_lo": boot["macro"][0] if boot["macro"] else None,
        "macro_boot_hi": boot["macro"][1] if boot["macro"] else None,
        "median": quantile(rates, 0.5) if rates else None,
        "q1": quantile(rates, 0.25) if rates else None,
        "q3": quantile(rates, 0.75) if rates else None,
    }


def _repo_rows(summaries: Sequence[dict[str, Any]], scopes: Sequence[str]) -> list[dict[str, Any]]:
    rows = []
    for s in summaries:
        row: dict[str, Any] = {
            "label": s["label"],
            "head": s.get("head", ""),
            "commit_pairs": s.get("commit_pairs", 0),
            "versions_scanned": s.get("versions_scanned", 0),
            "elapsed_seconds": s.get("elapsed_seconds", 0),
        }
        for scope in scopes:
            block = scope_block(s, scope)
            if block is None:
                continue
            gt = block["totals"]["gt"]
            row[f"{scope}_observations"] = block["collisions"]["observations"]
            row[f"{scope}_known"] = gt["known"]
            row[f"{scope}_introduced"] = gt["introduced"]
        rows.append(row)
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        columns += [k for k in row if k not in columns]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_value(row.get(k)) for k in columns})


def _csv_value(x: object) -> object:
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{x:.6f}"
    return x


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.2f}"


def _ci(lo: float | None, hi: float | None) -> str:
    return "" if lo is None or hi is None else f"[{100 * lo:.2f}, {100 * hi:.2f}]"


SCOPE_TITLES = {ALL: "All findings"}


def markdown_tables(tables: Tables) -> str:
    """The pooled tables as Markdown: per scope, false-new in detail, then the rest."""
    out: list[str] = []
    scopes = list(dict.fromkeys(r["scope"] for r in tables.pooled))
    for scope in scopes:
        rows = [r for r in tables.pooled if r["scope"] == scope]
        by = {(r["scheme"], r["metric"]): r for r in rows}
        schemes = list(dict.fromkeys(r["scheme"] for r in rows))
        title = SCOPE_TITLES.get(scope, f"{scope.capitalize()} findings")
        out.append(f"### {title}\n")
        if schemes:
            fn, hd = by[(schemes[0], "false_new")], by[(schemes[0], "hidden")]
            out.append(
                f"{fn['repos']} repositories, {fn['repos_with_rate']} of them with persisting "
                f"findings: {fn['den']} persisting findings, {hd['den']} introduced. "
                "Rates in %.\n"
            )
        out.append(
            "| scheme | false-new (pooled) | Wilson 95% CI | cluster bootstrap 95% CI "
            "| macro (bootstrap CI) | median [IQR] |"
        )
        out.append("|---|---:|---|---|---|---|")
        for scheme in schemes:
            f = by[(scheme, "false_new")]
            out.append(
                f"| `{scheme}` | {_pct(f['pooled'])} | {_ci(f['wilson_lo'], f['wilson_hi'])} "
                f"| {_ci(f['boot_lo'], f['boot_hi'])} "
                f"| {_pct(f['macro'])} {_ci(f['macro_boot_lo'], f['macro_boot_hi'])} "
                f"| {_pct(f['median'])} [{_pct(f['q1'])}, {_pct(f['q3'])}] |"
            )
        out.append("")
        others = ("false_new_moved", "false_new_edited", "hidden", "mispair", "collision")
        out.append(
            "| scheme | false-new, moved | false-new, edited | hidden | mispair | collision |"
        )
        out.append("|---|---|---|---|---|---|")
        for scheme in schemes:
            cells = [
                f"{_pct(x['pooled'])} {_ci(x['boot_lo'], x['boot_hi'])}"
                for x in (by[(scheme, m)] for m in others)
            ]
            out.append(f"| `{scheme}` | " + " | ".join(cells) + " |")
        out.append("")
    out.append(
        "Pooled = total numerator over total denominator. Brackets after a pooled rate are "
        "the cluster bootstrap 95% CI over repositories; macro = mean of per-repository "
        "rates; IQR over per-repository rates.\n"
    )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Box plot (optional dependency)
# ---------------------------------------------------------------------------

_INK = "#0b0b0b"
_INK_SECONDARY = "#52514e"
_GRID = "#e4e3df"
_SERIES = "#2a78d6"


def box_plot(tables: Tables, path: Path, metric: str = "false_new") -> bool:
    """Per-repository *metric* rates per scheme, one panel per scope. False without matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping the box plot", file=sys.stderr)
        return False
    scopes = list(dict.fromkeys(r["scope"] for r in tables.per_repo))
    schemes = list(dict.fromkeys(r["scheme"] for r in tables.per_repo))
    fig, axes = plt.subplots(
        1, len(scopes), figsize=(4.2 * len(scopes), 3.6), sharey=True, squeeze=False
    )
    rng = random.Random(0)  # noqa: S311  (jitter for plotted points)
    for ax, scope in zip(axes[0], scopes, strict=True):
        data = []
        for scheme in schemes:
            data.append(
                [
                    100 * r["rate"]
                    for r in tables.per_repo
                    if r["scope"] == scope
                    and r["scheme"] == scheme
                    and r["metric"] == metric
                    and r["rate"] is not None
                ]
            )
        positions = range(1, len(schemes) + 1)
        ax.boxplot(
            data,
            positions=list(positions),
            widths=0.5,
            showfliers=False,
            medianprops={"color": _SERIES, "linewidth": 2},
            boxprops={"color": _INK_SECONDARY, "linewidth": 1},
            whiskerprops={"color": _INK_SECONDARY, "linewidth": 1},
            capprops={"color": _INK_SECONDARY, "linewidth": 1},
        )
        for x, values in zip(positions, data, strict=True):
            xs = [x + rng.uniform(-0.15, 0.15) for _ in values]
            ax.scatter(xs, values, s=10, color=_SERIES, alpha=0.6, linewidths=0, zorder=3)
        n = max((len(v) for v in data), default=0)
        title = SCOPE_TITLES.get(scope, f"{scope.capitalize()} findings")
        ax.set_title(f"{title} ({n} repositories)", color=_INK, fontsize=10, loc="left")
        ax.set_xticks(list(positions), schemes, rotation=30, ha="right", fontsize=8)
        ax.tick_params(colors=_INK_SECONDARY, labelsize=8)
        # Most schemes lose a few percent and `line` loses half: a symmetric log scale
        # (linear below 1%) keeps both readable.
        ax.set_yscale("symlog", linthresh=1, linscale=0.5)
        ticks = [0, 0.5, 1, 2, 5, 10, 20, 50, 100]
        ax.set_yticks(ticks, [f"{t:g}" for t in ticks])
        ax.set_ylim(-0.1, 100)
        ax.grid(axis="y", color=_GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(_GRID)
    axes[0][0].set_ylabel(f"{metric.replace('_', '-')} rate per repository (%, symlog)", color=_INK)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_stats(
    paths: Sequence[Path],
    out_dir: Path,
    *,
    labels: Sequence[str] | None = None,
    scopes: Sequence[str] = (ALL, "security"),
    resamples: int = 10_000,
    seed: int = 20261014,
    plot: bool = False,
) -> Tables:
    summaries = load_summaries(paths, labels)
    if not summaries:
        raise SystemExit("no summary.json found")
    tables = build_tables(summaries, scopes=scopes, resamples=resamples, seed=seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "pooled.csv", tables.pooled)
    write_csv(out_dir / "per_repo.csv", tables.per_repo)
    write_csv(out_dir / "repos.csv", tables.repos)
    md = markdown_tables(tables)
    (out_dir / "tables.md").write_text(md, encoding="utf-8")
    print(md)
    if plot:
        box_plot(tables, out_dir / "false_new_by_repo.png")
    return tables
