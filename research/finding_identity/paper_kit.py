"""Tables and numbers for the paper, from corpus replays (RQ1).

``python -m research.finding_identity.paper_kit --codeguard <results> --bandit <results>``
reads one batch of replays per analyzer and writes, to ``--out``:

- ``rq1.csv``: per analyzer, scheme and metric, the pooled rate with its cluster
  bootstrap 95% CI over repositories, and the per-repository median;
- ``table_rq1.tex``: Table II of the paper (LaTeX, ``booktabs``);
- ``numbers.md``: every number the RQ1 section cites, with its source.

Besides the metrics of :mod:`stats`, the false-new rate is split by whether the file was
renamed in the commit, from each replay's ``findings.jsonl`` (``--details``). Every
estimate of one analyzer uses the same bootstrap draws, so their intervals are paired.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .corpus import load_corpus
from .stats import bootstrap_draws, cluster_bootstrap, counts, load_summaries, quantile

HERE = Path(__file__).parent

#: Schemes in the paper's table, from the naive baseline to the shipped tools.
TABLE_SCHEMES = ("line", "line_text", "github", "codeguard", "sonar", "sonar_branch", "bandit")
ANALYZER_NAMES = {"codeguard": "CodeGuard", "bandit": "Bandit", "semgrep": "Semgrep"}
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


@dataclass(frozen=True)
class Estimate:
    num: int
    den: int
    rate: float | None
    ci: tuple[float, float] | None
    median: float | None


def load_runs(results: Path, labels: Sequence[str] | None) -> list[Run]:
    runs = []
    for summary in load_summaries([results], labels):
        label = summary["label"]
        findings = results / label / "findings.jsonl"
        if not findings.exists():
            raise SystemExit(f"{findings} is missing: replay with --details")
        runs.append(Run(label, summary, findings))
    return runs


def _rename_split(run: Run, scheme: str) -> dict[str, tuple[int, int]]:
    """``(false_new, known)`` among persisting findings, by whether the file was renamed."""
    split = {"false_new_same_path": [0, 0], "false_new_renamed": [0, 0]}
    with run.findings.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["truth"] != "known":
                continue
            renamed = str(rec.get("status", "")).startswith("R")
            cell = split["false_new_renamed" if renamed else "false_new_same_path"]
            cell[0] += rec["outcomes"][scheme] == "false_new"
            cell[1] += 1
    return {k: (v[0], v[1]) for k, v in split.items()}


def repo_counts(runs: Sequence[Run], scheme: str) -> dict[str, list[tuple[int, int]]]:
    """Per metric, one ``(numerator, denominator)`` per repository, in *runs* order."""
    out: dict[str, list[tuple[int, int]]] = {name: [] for name, _ in METRICS}
    for run in runs:
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
        caption += (
            f" Bandit findings: {bd['repos']} Python repositories, {bd['known']:,} "
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


def facts_for(runs: Sequence[Run]) -> dict[str, Any]:
    gt = [r.summary["totals"]["gt"] for r in runs]
    split = [_rename_split(r, "line") for r in runs]
    return {
        "repos": len(runs),
        "commit_pairs": sum(int(r.summary["commit_pairs"]) for r in runs),
        "known": sum(int(g["known"]) for g in gt),
        "introduced": sum(int(g["introduced"]) for g in gt),
        "known_renamed": sum(s["false_new_renamed"][1] for s in split),
        "repos_with_renamed": sum(1 for s in split if s["false_new_renamed"][1]),
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
            f"Source: `{sources[analyzer]}`. {f['repos']} repositories, "
            f"{f['commit_pairs']:,} commit pairs, {f['known']:,} persisting and "
            f"{f['introduced']:,} introduced findings; {f['known_renamed']:,} persisting "
            f"findings in renamed files, in {f['repos_with_renamed']} repositories.",
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
        out.append("")
    out += ["Metrics:", ""] + [f"- `{name}`: {desc}." for name, desc in METRICS]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m research.finding_identity.paper_kit")
    ap.add_argument("--codeguard", type=Path, required=True, help="batch results, CodeGuard")
    ap.add_argument("--bandit", type=Path, help="batch results, Bandit")
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
    for analyzer, path in sources.items():
        wanted = [x for x in labels if (path / x / "summary.json").exists()]
        runs = load_runs(path, wanted)
        facts[analyzer] = facts_for(runs)
        present = [s for s in TABLE_SCHEMES if all(s in r.summary["schemes"] for r in runs)]
        results[analyzer] = estimates(runs, present, args.resamples, args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "rq1.csv", results)
    (args.out / "table_rq1.tex").write_text(
        latex_table(results["codeguard"], results.get("bandit"), facts), encoding="utf-8"
    )
    (args.out / "numbers.md").write_text(
        numbers_markdown(results, facts, sources), encoding="utf-8"
    )
    print(f"wrote rq1.csv, table_rq1.tex and numbers.md to {args.out}")


if __name__ == "__main__":
    main()
