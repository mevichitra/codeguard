# SPDX-License-Identifier: Apache-2.0

"""Tables, figures and numbers for the paper: RQ1 from corpus replays, RQ2 from the
transformation experiment.

``python -m research.finding_identity.paper_kit --codeguard <results> --bandit <results>
--semgrep <results> --transform <results>`` reads one batch of replays per analyzer
(``--bandit`` and ``--semgrep`` are optional; Semgrep's findings add the ``semgrep``
scheme, Semgrep's own ``match_based_id``), and the
``transform-<label>`` directories of the experiment, and writes to ``--out``:

- ``rq1.csv``: per analyzer, scheme and metric, the pooled rate with its cluster
  bootstrap 95% CI over repositories, and the per-repository median;
- ``table_rq1.tex``: Table II of the paper (LaTeX, ``booktabs``);
- ``table_rq1_semgrep.tex``, with ``--semgrep``: the rates on Semgrep's findings, a
  one-column table (``tab:rq1-semgrep``), since Table II has no room for more columns;
- ``numbers.md``: every number the RQ1 section cites, with its source;
- ``rq2.csv`` and ``fig_rq2.pdf``: the invariance matrix pooled over repositories, with
  cluster-bootstrap intervals, and Fig. 1 of the paper (needs matplotlib).

Besides the metrics of :mod:`stats`, the false-new rate is split by whether the file was
renamed in the commit, from each replay's ``findings.jsonl`` (``--details``). Every
estimate of one analyzer uses the same bootstrap draws, so their intervals are paired.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import load_corpus
from .stats import bootstrap_draws, cluster_bootstrap, counts, load_summaries, quantile

HERE = Path(__file__).parent

#: Schemes in the paper's table, from the naive baseline to the shipped tools.
TABLE_SCHEMES = ("line", "line_text", "github", "codeguard", "sonar", "sonar_branch", "bandit")
ANALYZER_NAMES = {
    "codeguard": "CodeGuard",
    "bandit": "Bandit",
    "bandit_all_rules": "Bandit (all rules)",
    "semgrep": "Semgrep",
}
#: Metrics computed for every scheme: (name, description).
METRICS = (
    ("false_new", "persisting findings reported as new"),
    ("false_new_same_path", "of those in files that kept their path"),
    ("false_new_renamed", "of those in renamed files"),
    ("hidden", "introduced findings matched to an old one"),
    ("mispair", "persisting findings matched to the wrong old one"),
    ("collision", "findings sharing a key with another in the same file version"),
)


@dataclass(frozen=True)
class Run:
    """One repository's replay: its summary and its per-finding records."""

    label: str
    summary: dict[str, Any]
    findings: Path
    #: Rules left out. The metrics are then counted from ``findings.jsonl``, which does
    #: not hold what collisions need, so the collision rate is not computed.
    exclude: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Estimate:
    num: int
    den: int
    rate: float | None
    ci: tuple[float, float] | None
    median: float | None


def load_runs(
    results: Path, labels: Sequence[str] | None, exclude: frozenset[str] = frozenset()
) -> list[Run]:
    runs = []
    for summary in load_summaries([results], labels):
        label = summary["label"]
        findings = results / label / "findings.jsonl"
        if not findings.exists():
            raise SystemExit(f"{findings} is missing: replay with --details")
        runs.append(Run(label, summary, findings, exclude))
    return runs


def _rename_split(run: Run, scheme: str) -> dict[str, tuple[int, int]]:
    """``(false_new, known)`` among persisting findings, by whether the file was renamed."""
    split = {"false_new_same_path": [0, 0], "false_new_renamed": [0, 0]}
    with run.findings.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["truth"] != "known" or rec["rule"] in run.exclude:
                continue
            renamed = str(rec.get("status", "")).startswith("R")
            cell = split["false_new_renamed" if renamed else "false_new_same_path"]
            cell[0] += rec["outcomes"][scheme] == "false_new"
            cell[1] += 1
    return {k: (v[0], v[1]) for k, v in split.items()}


def _record_counts(run: Run, scheme: str) -> dict[str, tuple[int, int]]:
    """False-new, hidden and mispair counts from ``findings.jsonl``, without excluded rules."""
    c = {"false_new": [0, 0], "hidden": [0, 0], "mispair": [0, 0]}
    with run.findings.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["rule"] in run.exclude:
                continue
            outcome = rec["outcomes"][scheme]
            if rec["truth"] == "known":
                for name, hit in (("false_new", "false_new"), ("mispair", "mispaired")):
                    c[name][0] += outcome == hit
                    c[name][1] += 1
            else:
                c["hidden"][0] += outcome == "false_known"
                c["hidden"][1] += 1
    return {k: (v[0], v[1]) for k, v in c.items()}


def repo_counts(runs: Sequence[Run], scheme: str) -> dict[str, list[tuple[int, int]]]:
    """Per metric, one ``(numerator, denominator)`` per repository, in *runs* order."""
    out: dict[str, list[tuple[int, int]]] = {name: [] for name, _ in METRICS}
    for run in runs:
        if run.exclude:
            for name, pair in _record_counts(run, scheme).items():
                out[name].append(pair)
            out["collision"].append((0, 0))
        else:
            for name in ("false_new", "hidden", "mispair", "collision"):
                out[name].append(counts(run.summary, scheme, name))
        for name, pair in _rename_split(run, scheme).items():
            out[name].append(pair)
    return out


def estimate(pairs: Sequence[tuple[int, int]], draws: Sequence[Sequence[int]]) -> Estimate:
    num = sum(n for n, _ in pairs)
    den = sum(d for _, d in pairs)
    rates = [n / d for n, d in pairs if d]
    return Estimate(
        num,
        den,
        num / den if den else None,
        cluster_bootstrap(pairs, draws)["pooled"],
        quantile(rates, 0.5) if rates else None,
    )


def estimates(
    runs: Sequence[Run], schemes: Sequence[str], resamples: int, seed: int
) -> dict[tuple[str, str], Estimate]:
    """``{(scheme, metric): estimate}`` over *runs*."""
    draws = bootstrap_draws(len(runs), resamples, seed)
    out = {}
    for scheme in schemes:
        for metric, pairs in repo_counts(runs, scheme).items():
            out[(scheme, metric)] = estimate(pairs, draws)
    return out


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def _pct(x: float | None, digits: int = 2) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def write_csv(path: Path, results: dict[str, dict[tuple[str, str], Estimate]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["findings", "scheme", "metric", "num", "den", "rate", "ci_lo", "ci_hi", "median"]
        )
        for analyzer, table in results.items():
            for (scheme, metric), e in table.items():
                lo, hi = e.ci if e.ci else (None, None)
                w.writerow([analyzer, scheme, metric, e.num, e.den, e.rate, lo, hi, e.median])


def _tex_cell(e: Estimate | None) -> str:
    if e is None or e.rate is None:
        return "--"
    if e.ci is None:
        return f"{100 * e.rate:.1f}"
    lo, hi = e.ci
    return f"{100 * e.rate:.1f} {{\\scriptsize({100 * lo:.1f}--{100 * hi:.1f})}}"


def _tex_name(scheme: str) -> str:
    return "\\texttt{" + scheme.replace("_", "\\_") + "}"


def latex_table(
    codeguard: dict[tuple[str, str], Estimate],
    bandit: dict[tuple[str, str], Estimate] | None,
    facts: dict[str, Any],
) -> str:
    cg_cols = ("false_new", "false_new_same_path", "false_new_renamed", "hidden", "collision")
    bd_cols = ("false_new", "hidden")
    n_cols = len(cg_cols) + (len(bd_cols) if bandit else 0)
    cg = facts["codeguard"]
    caption = (
        "Identity errors over 200 consecutive commit pairs per repository, in percent: "
        "pooled rate with its 95\\% cluster-bootstrap interval over repositories. "
        f"CodeGuard findings: {cg['repos']} repositories, {cg['known']:,} persisting and "
        f"{cg['introduced']:,} introduced findings, {cg['known_renamed']:,} of the "
        "persisting ones in renamed files."
    )
    if bandit:
        bd = facts["bandit"]
        without = f" other than {', '.join(bd['excluded'])}" if bd["excluded"] else ""
        caption += (
            f" Bandit findings{without}: {bd['repos']} Python repositories, {bd['known']:,} "
            f"persisting and {bd['introduced']:,} introduced findings."
        )
    lines = [
        "% Generated by research/finding_identity/paper_kit.py; do not edit by hand.",
        "\\begin{table*}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        "\\label{tab:rq1}",
        "\\begin{tabular}{l" + "r" * n_cols + "}",
        "\\toprule",
    ]
    head = f" & \\multicolumn{{{len(cg_cols)}}}{{c}}{{CodeGuard findings}}"
    rule = f"\\cmidrule(lr){{2-{1 + len(cg_cols)}}}"
    if bandit:
        head += f" & \\multicolumn{{{len(bd_cols)}}}{{c}}{{Bandit findings}}"
        rule += f" \\cmidrule(lr){{{2 + len(cg_cols)}-{1 + n_cols}}}"
    lines += [head + " \\\\", rule]
    sub = " & \\multicolumn{3}{c}{False new} & Hidden & Collisions"
    if bandit:
        sub += " & False new & Hidden"
    lines += [sub + " \\\\", "\\cmidrule(lr){2-4}"]
    sub2 = "Scheme & all & same path & renamed & & "
    if bandit:
        sub2 += " & & "
    lines += [sub2.rstrip(" &") + " \\\\", "\\midrule"]
    for scheme in TABLE_SCHEMES:
        cells = [_tex_cell(codeguard.get((scheme, m))) for m in cg_cols]
        if bandit:
            cells += [_tex_cell(bandit.get((scheme, m))) for m in bd_cols]
        lines.append(_tex_name(scheme) + " & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""]
    return "\n".join(lines)


#: Columns of the Semgrep table: the table is one column wide, so no rename split.
SEMGREP_COLS = ("false_new", "hidden", "collision")


def semgrep_table(semgrep: dict[tuple[str, str], Estimate], facts: dict[str, Any]) -> str:
    """The Semgrep findings' rates, as a one-column table next to Table II."""
    sg = facts["semgrep"]
    caption = (
        "Identity errors on Semgrep's findings, in percent, as in Table~\\ref{tab:rq1}: "
        f"{sg['repos']} repositories, {sg['known']:,} persisting and {sg['introduced']:,} "
        f"introduced findings, {sg['known_renamed']:,} of the persisting ones in renamed "
        "files. \\texttt{semgrep} is Semgrep's own \\texttt{match\\_based\\_id}."
    )
    lines = [
        "% Generated by research/finding_identity/paper_kit.py; do not edit by hand.",
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        "\\label{tab:rq1-semgrep}",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{3pt}",
        "\\begin{tabular}{l" + "r" * len(SEMGREP_COLS) + "}",
        "\\toprule",
        "Scheme & False new & Hidden & Collisions \\\\",
        "\\midrule",
    ]
    for scheme in (*TABLE_SCHEMES, "semgrep"):
        cells = [_tex_cell(semgrep.get((scheme, m))) for m in SEMGREP_COLS]
        lines.append(_tex_name(scheme) + " & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    return "\n".join(lines)


#: A path with one of these parts counts as test code in the rule breakdown.
TEST_PATH_PARTS = ("test", "conftest")


def rule_breakdown(runs: Sequence[Run], top: int = 5) -> list[dict[str, Any]]:
    """The *top* rules by persisting findings: counts, and how many are in test code."""
    rows: dict[str, dict[str, int]] = {}
    for run in runs:
        with run.findings.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec["rule"] in run.exclude:
                    continue
                row = rows.setdefault(rec["rule"], {"known": 0, "introduced": 0, "in_tests": 0})
                row["known" if rec["truth"] == "known" else "introduced"] += 1
                row["in_tests"] += any(p in rec["path"].lower() for p in TEST_PATH_PARTS)
    ranked = sorted(rows.items(), key=lambda kv: -kv[1]["known"])[:top]
    return [{"rule": rule, **row} for rule, row in ranked]


def facts_for(runs: Sequence[Run]) -> dict[str, Any]:
    split = [_rename_split(r, "line") for r in runs]
    if any(r.exclude for r in runs):
        rc = [_record_counts(r, "line") for r in runs]
        known = sum(c["false_new"][1] for c in rc)
        introduced = sum(c["hidden"][1] for c in rc)
    else:
        known = sum(int(r.summary["totals"]["gt"]["known"]) for r in runs)
        introduced = sum(int(r.summary["totals"]["gt"]["introduced"]) for r in runs)
    return {
        "repos": len(runs),
        "commit_pairs": sum(int(r.summary["commit_pairs"]) for r in runs),
        "known": known,
        "introduced": introduced,
        "excluded": sorted(set().union(*(r.exclude for r in runs))),
        "known_renamed": sum(s["false_new_renamed"][1] for s in split),
        "repos_with_renamed": sum(1 for s in split if s["false_new_renamed"][1]),
        "rules": rule_breakdown(runs),
    }


def numbers_markdown(
    results: dict[str, dict[tuple[str, str], Estimate]],
    facts: dict[str, dict[str, Any]],
    sources: dict[str, Path],
) -> str:
    out = [
        "# RQ1 numbers",
        "",
        "Generated by `research/finding_identity/paper_kit.py`; do not edit by hand. Rates",
        "in percent: pooled rate, 95% cluster-bootstrap interval over repositories, and",
        "the median of the per-repository rates.",
        "",
    ]
    for analyzer, table in results.items():
        f = facts[analyzer]
        out += [
            f"## {ANALYZER_NAMES[analyzer]} findings",
            "",
            f"Source: `{sources[analyzer]}`"
            + (f", without rules {', '.join(f['excluded'])}" if f["excluded"] else "")
            + f". {f['repos']} repositories, "
            f"{f['commit_pairs']:,} commit pairs, {f['known']:,} persisting and "
            f"{f['introduced']:,} introduced findings; {f['known_renamed']:,} persisting "
            f"findings in renamed files, in {f['repos_with_renamed']} "
            + ("repository." if f["repos_with_renamed"] == 1 else "repositories."),
            "",
            "| scheme | metric | rate | 95% CI | median | n |",
            "|---|---|---:|---|---:|---:|",
        ]
        for (scheme, metric), e in table.items():
            ci = f"[{_pct(e.ci[0])}, {_pct(e.ci[1])}]" if e.ci else "n/a"
            out.append(
                f"| `{scheme}` | {metric} | {_pct(e.rate)} | {ci} | {_pct(e.median)} | "
                f"{e.num:,}/{e.den:,} |"
            )
        out += [
            "",
            "Rules with the most persisting findings (share of all; findings in test code):",
            "",
            "| rule | persisting | introduced | in test code |",
            "|---|---:|---:|---:|",
        ]
        for r in f["rules"]:
            total = r["known"] + r["introduced"]
            out.append(
                f"| `{r['rule']}` | {r['known']:,} ({100 * r['known'] / f['known']:.1f}%) | "
                f"{r['introduced']:,} ({100 * r['introduced'] / max(f['introduced'], 1):.1f}%) | "
                f"{100 * r['in_tests'] / total:.0f}% |"
            )
        out.append("")
    out += ["Metrics:", ""] + [f"- `{name}`: {desc}." for name, desc in METRICS]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# RQ2: the invariance matrix
# ---------------------------------------------------------------------------

#: Transformations that introduce a finding: their row shows the hidden rate.
DUPLICATES = ("duplicate_above", "duplicate_below")


def load_matrices(results: Path, labels: Sequence[str]) -> dict[str, list[dict[str, str]]]:
    """``{label: matrix.csv rows}`` for each ``transform-<label>`` under *results*."""
    out = {}
    for label in labels:
        path = results / f"transform-{label}" / "matrix.csv"
        if path.exists():
            with path.open(newline="", encoding="utf-8") as f:
                out[label] = list(csv.DictReader(f))
    return out


def rq2_estimates(
    matrices: dict[str, list[dict[str, str]]],
    schemes: Sequence[str],
    resamples: int,
    seed: int,
) -> dict[tuple[str, str, str], Estimate]:
    """``{(transform, scheme, metric): estimate}``, metric ``false_new`` or ``hidden``."""
    labels = list(matrices)
    draws = bootstrap_draws(len(labels), resamples, seed)
    cells: dict[tuple[str, str, str], list[tuple[int, int]]] = {}
    for i, label in enumerate(labels):
        for row in matrices[label]:
            if row["scheme"] not in schemes:
                continue
            for metric, num, den in (
                ("false_new", "false_new", "target_known"),
                ("hidden", "hidden", "introduced"),
            ):
                key = (row["transform"], row["scheme"], metric)
                pairs = cells.setdefault(key, [(0, 0)] * len(labels))
                pairs[i] = (int(row[num]), int(row[den]))
    return {key: estimate(pairs, draws) for key, pairs in cells.items()}


def write_rq2_csv(path: Path, table: dict[tuple[str, str, str], Estimate]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["transform", "scheme", "metric", "num", "den", "rate", "ci_lo", "ci_hi"])
        for (transform, scheme, metric), e in table.items():
            lo, hi = e.ci if e.ci else (None, None)
            w.writerow([transform, scheme, metric, e.num, e.den, e.rate, lo, hi])


#: Sequential blue ramp, light to dark (steps 100 to 700 of the reference palette).
_RAMP = (
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
)  # fmt: skip
_INK = "#0b0b0b"
_INK_SECONDARY = "#52514e"
_EMPTY = "#f0efec"


def heatmap(
    table: dict[tuple[str, str, str], Estimate],
    transforms: Sequence[str],
    schemes: Sequence[str],
    path: Path,
) -> bool:
    """Fig. 1: false-new rate per transformation and scheme, and the hidden rate for the
    duplicating transformations, as one heatmap. False without matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import BoundaryNorm, ListedColormap
        from matplotlib.patches import Rectangle
    except ImportError:
        print("matplotlib is not installed; skipping fig_rq2.pdf", file=sys.stderr)
        return False
    matplotlib.rcParams.update({"pdf.fonttype": 42, "font.size": 7})
    upper = [t for t in transforms if t not in DUPLICATES]
    lower = [t for t in transforms if t in DUPLICATES]
    cmap = ListedColormap(list(_RAMP))
    norm = BoundaryNorm([i * 100 / len(_RAMP) for i in range(len(_RAMP) + 1)], len(_RAMP))
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(3.5, 0.24 * (len(upper) + len(lower)) + 1.0),
        gridspec_kw={"height_ratios": [len(upper), len(lower)], "hspace": 0.08},
        sharex=True,
    )
    panels = ((axes[0], upper, "false_new"), (axes[1], lower, "hidden"))
    for ax, rows, metric in panels:
        for y, transform in enumerate(rows):
            for x, scheme in enumerate(schemes):
                e = table.get((transform, scheme, metric))
                if e is None or e.rate is None:
                    ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, color=_EMPTY))
                    ax.text(x, y, "n/a", ha="center", va="center", color=_INK_SECONDARY)
                    continue
                value = 100 * e.rate
                colour = cmap(norm(min(value, 99.999)))
                ax.add_patch(
                    Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=colour, edgecolor="white", lw=1)
                )
                ink = "white" if value >= 50 else _INK
                ax.text(x, y, f"{value:.0f}", ha="center", va="center", color=ink)
        ax.set_xlim(-0.5, len(schemes) - 0.5)
        ax.set_ylim(len(rows) - 0.5, -0.5)
        ax.set_yticks(range(len(rows)), [t.replace("_", " ") for t in rows])
        ax.tick_params(length=0, colors=_INK)
        for spine in ax.spines.values():
            spine.set_visible(False)
        label = "false new (%)" if metric == "false_new" else "hidden (%)"
        ax.set_ylabel(label, color=_INK_SECONDARY)
    axes[0].xaxis.set_ticks_position("top")
    axes[0].set_xticks(range(len(schemes)), schemes, rotation=35, ha="left")
    axes[1].tick_params(labelbottom=False)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return True


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m research.finding_identity.paper_kit")
    ap.add_argument("--codeguard", type=Path, required=True, help="batch results, CodeGuard")
    ap.add_argument("--bandit", type=Path, help="batch results, Bandit")
    ap.add_argument(
        "--bandit-exclude",
        default="",
        help="comma-separated Bandit rules to leave out of the table (all rules stay in "
        "numbers.md as 'bandit_all_rules')",
    )
    ap.add_argument(
        "--semgrep",
        type=Path,
        help="batch results, Semgrep (adds the semgrep scheme, which needs Semgrep's IDs)",
    )
    ap.add_argument("--transform", type=Path, help="directory of transform-<label> results")
    ap.add_argument("--corpus", type=Path, default=HERE / "corpus.csv")
    ap.add_argument("--out", type=Path, default=HERE / "paper")
    ap.add_argument("--resamples", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=20261014)
    args = ap.parse_args(argv)

    labels = [e.label for e in load_corpus(args.corpus)]
    sources = {"codeguard": args.codeguard}
    if args.bandit:
        sources["bandit"] = args.bandit
    results: dict[str, dict[tuple[str, str], Estimate]] = {}
    facts: dict[str, dict[str, Any]] = {}
    exclude = frozenset(x.strip() for x in args.bandit_exclude.split(",") if x.strip())
    jobs: list[tuple[str, Path, frozenset[str]]] = [("codeguard", args.codeguard, frozenset())]
    if args.bandit:
        jobs.append(("bandit", args.bandit, exclude))
        if exclude:
            jobs.append(("bandit_all_rules", args.bandit, frozenset()))
            sources["bandit_all_rules"] = args.bandit
    if args.semgrep:
        jobs.append(("semgrep", args.semgrep, frozenset()))
        sources["semgrep"] = args.semgrep
    for analyzer, path, leave_out in jobs:
        wanted = [x for x in labels if (path / x / "summary.json").exists()]
        runs = load_runs(path, wanted, leave_out)
        facts[analyzer] = facts_for(runs)
        candidates = (*TABLE_SCHEMES, "semgrep") if analyzer == "semgrep" else TABLE_SCHEMES
        present = [s for s in candidates if all(s in r.summary["schemes"] for r in runs)]
        results[analyzer] = estimates(runs, present, args.resamples, args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "rq1.csv", results)
    (args.out / "table_rq1.tex").write_text(
        latex_table(results["codeguard"], results.get("bandit"), facts), encoding="utf-8"
    )
    (args.out / "numbers.md").write_text(
        numbers_markdown(results, facts, sources), encoding="utf-8"
    )
    written = ["rq1.csv", "table_rq1.tex", "numbers.md"]
    if "semgrep" in results:
        (args.out / "table_rq1_semgrep.tex").write_text(
            semgrep_table(results["semgrep"], facts), encoding="utf-8"
        )
        written.append("table_rq1_semgrep.tex")
    if args.transform:
        matrices = load_matrices(args.transform, labels)
        if not matrices:
            raise SystemExit(f"no transform-<label>/matrix.csv under {args.transform}")
        from .transforms import DETERMINISTIC  # needs libcst, so only for RQ2

        rq2 = rq2_estimates(matrices, TABLE_SCHEMES, args.resamples, args.seed)
        write_rq2_csv(args.out / "rq2.csv", rq2)
        written.append(f"rq2.csv ({len(matrices)} repositories)")
        present = [t for t in DETERMINISTIC if any(k[0] == t for k in rq2)]
        # No transformation renames a file, so the two SonarQube modes agree: one column.
        columns = [s for s in TABLE_SCHEMES if s != "sonar_branch"]
        if heatmap(rq2, present, columns, args.out / "fig_rq2.pdf"):
            heatmap(rq2, present, columns, args.out / "fig_rq2.png")
            written.append("fig_rq2.pdf")
    print(f"wrote {', '.join(written)} to {args.out}")


if __name__ == "__main__":
    main()
