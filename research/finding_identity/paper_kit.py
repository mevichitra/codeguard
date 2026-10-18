# SPDX-License-Identifier: Apache-2.0

"""Tables, figures and numbers for the paper: RQ1 from corpus replays, RQ2 from the
transformation experiment.

``python -m research.finding_identity.paper_kit --codeguard <results> --bandit <results>
--transform <results>`` reads one batch of replays per analyzer, and the
``transform-<label>`` directories of the experiment, and writes to ``--out``:

- ``rq1.csv``: per analyzer, scheme and metric, the pooled rate with its cluster
  bootstrap 95% CI over repositories, and the per-repository median;
- ``table_rq1.tex``: Table II of the paper (LaTeX, ``booktabs``);
- ``table_gate.tex``: the gate table (what a CI gate that fails on new findings does
  with each scheme, from :mod:`gate`);
- ``numbers.md``: every number the RQ1 section cites, with its source, the paired
  differences between schemes and the bootstrap resamples dropped for an empty
  denominator;
- ``rq2.csv`` and ``fig_rq2.pdf``: the invariance matrix pooled over repositories, with
  cluster-bootstrap intervals, and Fig. 1 of the paper (needs matplotlib).

Besides the metrics of :mod:`stats`, the false-new rate is split by whether the file was
renamed in the commit, from each replay's ``findings.jsonl`` (``--details``), and the
gate metrics of :mod:`gate` come from ``findings.jsonl`` and ``pairs.jsonl``. Every
estimate of one analyzer uses the same bootstrap draws, so their intervals are paired,
and differences between schemes get their own intervals from those draws.
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
from .gate import GATE_METRICS, gate_counts
from .stats import bootstrap_draws, cluster_bootstrap, counts, load_summaries, quantile

HERE = Path(__file__).parent

#: Schemes in the paper's table, from the naive baseline to the shipped tools.
TABLE_SCHEMES = ("line", "line_text", "github", "codeguard", "sonar", "sonar_branch", "bandit")
ANALYZER_NAMES = {
    "codeguard": "CodeGuard",
    "bandit": "Bandit",
    "bandit_all_rules": "Bandit (all rules)",
    "codeguard_security": "CodeGuard (security rules)",
    "semgrep": "Semgrep",
}
#: Rule-ID prefix of CodeGuard's security rules, for the security-only variant.
CODEGUARD_SECURITY_PREFIX = "CG-SEC"
#: Metrics computed for every scheme: (name, description).
METRICS = (
    ("false_new", "persisting findings reported as new"),
    ("false_new_same_path", "of those in files that kept their path"),
    ("false_new_renamed", "of those in renamed files"),
    ("hidden", "introduced findings matched to an old one"),
    ("mispair", "persisting findings matched to the wrong old one"),
    ("collision", "findings sharing a key with another in the same file version"),
    *GATE_METRICS,
)
#: Differences between schemes on the same findings: (metric, scheme a, scheme b), for
#: a - b. Pairs whose schemes an analyzer lacks are skipped.
DIFFERENCES = (
    ("false_new", "sonar", "codeguard"),
    ("false_new", "codeguard", "line_text"),
    ("false_new", "github", "codeguard"),
    ("false_new", "sonar", "sonar_branch"),
    ("false_new", "sonar", "github"),
    ("false_new_same_path", "codeguard", "sonar"),
    ("false_new_same_path", "github", "codeguard"),
    ("false_new_same_path", "codeguard", "line_text"),
    ("hidden", "bandit", "line"),
    ("hidden", "bandit", "line_text"),
    ("hidden", "bandit", "github"),
    ("hidden", "bandit", "codeguard"),
    ("hidden", "bandit", "sonar"),
    ("hidden", "codeguard", "github"),
    ("gate_miss", "bandit", "line"),
    ("gate_miss", "bandit", "line_text"),
    ("gate_miss", "bandit", "github"),
    ("gate_miss", "bandit", "codeguard"),
    ("gate_miss", "bandit", "sonar"),
    ("gate_miss", "sonar", "codeguard"),
    ("gate_false_alarm", "github", "codeguard"),
    ("gate_false_alarm", "codeguard", "sonar"),
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
    #: Only rules whose ID starts with this, counted the same way as with *exclude*.
    prefix: str = ""

    @property
    def filtered(self) -> bool:
        return bool(self.exclude or self.prefix)

    @property
    def pairs(self) -> Path:
        return self.findings.parent / "pairs.jsonl"

    def keeps(self, rule: str) -> bool:
        return rule not in self.exclude and rule.startswith(self.prefix)


@dataclass(frozen=True)
class Estimate:
    num: int
    den: int
    rate: float | None
    ci: tuple[float, float] | None
    median: float | None
    #: Bootstrap resamples left out because their denominator was zero.
    dropped: int = 0


@dataclass(frozen=True)
class Difference:
    """``rate(a) - rate(b)`` on the same findings, with its paired bootstrap interval."""

    metric: str
    a: str
    b: str
    value: float | None
    ci: tuple[float, float] | None


def load_runs(
    results: Path,
    labels: Sequence[str] | None,
    exclude: frozenset[str] = frozenset(),
    prefix: str = "",
) -> list[Run]:
    runs = []
    for summary in load_summaries([results], labels):
        label = summary["label"]
        findings = results / label / "findings.jsonl"
        if not findings.exists():
            raise SystemExit(f"{findings} is missing: replay with --details")
        if not (findings.parent / "pairs.jsonl").exists():
            raise SystemExit(f"{findings.parent / 'pairs.jsonl'} is missing")
        runs.append(Run(label, summary, findings, exclude, prefix))
    return runs


def _rename_split(run: Run, scheme: str) -> dict[str, tuple[int, int]]:
    """``(false_new, known)`` among persisting findings, by whether the file was renamed."""
    split = {"false_new_same_path": [0, 0], "false_new_renamed": [0, 0]}
    with run.findings.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["truth"] != "known" or not run.keeps(rec["rule"]):
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
            if not run.keeps(rec["rule"]):
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


RepoTable = dict[tuple[str, str], list[tuple[int, int]]]


def repo_table(runs: Sequence[Run], schemes: Sequence[str]) -> RepoTable:
    """``{(scheme, metric): one (numerator, denominator) per repository}``, in *runs*
    order."""
    out: RepoTable = {(s, name): [] for s in schemes for name, _ in METRICS}
    for run in runs:
        gate = gate_counts(run.pairs, run.findings, schemes, run.keeps)
        for scheme in schemes:
            if run.filtered:
                for name, pair in _record_counts(run, scheme).items():
                    out[(scheme, name)].append(pair)
                out[(scheme, "collision")].append((0, 0))
            else:
                for name in ("false_new", "hidden", "mispair", "collision"):
                    out[(scheme, name)].append(counts(run.summary, scheme, name))
            for name, pair in _rename_split(run, scheme).items():
                out[(scheme, name)].append(pair)
            for name, pair in gate[scheme].items():
                out[(scheme, name)].append(pair)
    return out


def repo_counts(runs: Sequence[Run], scheme: str) -> dict[str, list[tuple[int, int]]]:
    """Per metric, one ``(numerator, denominator)`` per repository, in *runs* order."""
    return {m: pairs for (_, m), pairs in repo_table(runs, [scheme]).items()}


def dropped_resamples(pairs: Sequence[tuple[int, int]], draws: Sequence[Sequence[int]]) -> int:
    """How many *draws* have a zero denominator, so that the rate is undefined there."""
    empty = {i for i, (_, d) in enumerate(pairs) if not d}
    if not empty:
        return 0
    return sum(1 for draw in draws if all(i in empty for i in draw))


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
        dropped_resamples(pairs, draws),
    )


def paired_difference(
    a: Sequence[tuple[int, int]],
    b: Sequence[tuple[int, int]],
    draws: Sequence[Sequence[int]],
    *,
    level: float = 0.95,
) -> tuple[float | None, tuple[float, float] | None]:
    """``rate(a) - rate(b)`` and its percentile interval over the same resamples.

    *a* and *b* are per-repository ``(numerator, denominator)`` pairs of two schemes on
    the same findings. Resamples where either rate is undefined are left out.
    """

    def rate(pairs: Sequence[tuple[int, int]], idx: Sequence[int]) -> float | None:
        num = sum(pairs[i][0] for i in idx)
        den = sum(pairs[i][1] for i in idx)
        return num / den if den else None

    every = range(len(a))
    ra, rb = rate(a, every), rate(b, every)
    value = None if ra is None or rb is None else ra - rb
    diffs = []
    for draw in draws:
        x, y = rate(a, draw), rate(b, draw)
        if x is not None and y is not None:
            diffs.append(x - y)
    tail = (1 - level) / 2
    ci = (quantile(diffs, tail), quantile(diffs, 1 - tail)) if diffs else None
    return value, ci


def estimates(
    runs: Sequence[Run], schemes: Sequence[str], resamples: int, seed: int
) -> dict[tuple[str, str], Estimate]:
    """``{(scheme, metric): estimate}`` over *runs*."""
    return estimates_and_differences(runs, schemes, resamples, seed)[0]


def estimates_and_differences(
    runs: Sequence[Run], schemes: Sequence[str], resamples: int, seed: int
) -> tuple[dict[tuple[str, str], Estimate], list[Difference]]:
    """The estimates of :func:`estimates`, and the :data:`DIFFERENCES` among *schemes*."""
    draws = bootstrap_draws(len(runs), resamples, seed)
    table = repo_table(runs, schemes)
    out = {key: estimate(pairs, draws) for key, pairs in table.items()}
    diffs = []
    for metric, a, b in DIFFERENCES:
        if (a, metric) in table and (b, metric) in table:
            value, ci = paired_difference(table[(a, metric)], table[(b, metric)], draws)
            diffs.append(Difference(metric, a, b, value, ci))
    return out, diffs


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def _pct(x: float | None, digits: int = 2) -> str:
    return "n/a" if x is None else f"{100 * x:.{digits}f}"


def write_csv(path: Path, results: dict[str, dict[tuple[str, str], Estimate]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "findings", "scheme", "metric", "num", "den", "rate", "ci_lo", "ci_hi",
                "median", "dropped_resamples",
            ]
        )  # fmt: skip
        for analyzer, table in results.items():
            for (scheme, metric), e in table.items():
                lo, hi = e.ci if e.ci else (None, None)
                w.writerow(
                    [analyzer, scheme, metric, e.num, e.den, e.rate, lo, hi, e.median, e.dropped]
                )


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
    cg_cols = (
        "false_new", "false_new_same_path", "false_new_renamed", "mispair", "hidden", "collision"
    )  # fmt: skip
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
        "\\setlength{\\tabcolsep}{3pt}",
        "\\begin{tabular}{l" + "r" * n_cols + "}",
        "\\toprule",
    ]
    head = f" & \\multicolumn{{{len(cg_cols)}}}{{c}}{{CodeGuard findings}}"
    rule = f"\\cmidrule(lr){{2-{1 + len(cg_cols)}}}"
    if bandit:
        head += f" & \\multicolumn{{{len(bd_cols)}}}{{c}}{{Bandit findings}}"
        rule += f" \\cmidrule(lr){{{2 + len(cg_cols)}-{1 + n_cols}}}"
    lines += [head + " \\\\", rule]
    sub = " & \\multicolumn{3}{c}{False new} & Mispaired & Hidden & Collisions"
    if bandit:
        sub += " & False new & Hidden"
    lines += [sub + " \\\\", "\\cmidrule(lr){2-4}"]
    sub2 = "Scheme & all & same path & renamed & & & "
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


def _tex_stacked(e: Estimate | None) -> str:
    """The rate above its interval, in one cell of a narrow column."""
    if e is None or e.rate is None:
        return "--"
    if e.ci is None:
        return f"{100 * e.rate:.1f}"
    lo, hi = e.ci
    return (
        f"\\begin{{tabular}}[t]{{@{{}}r@{{}}}}{100 * e.rate:.1f}\\\\"
        f"{{\\scriptsize({100 * lo:.1f}--{100 * hi:.1f})}}\\end{{tabular}}"
    )


#: Columns of the gate table: (analyzer, metric, heading).
GATE_COLUMNS = (
    ("codeguard", "gate_miss", "Miss"),
    ("codeguard", "gate_false_alarm", "Alarm"),
    ("codeguard_security", "gate_miss", "Miss"),
    ("bandit", "gate_miss", "Miss"),
    ("bandit", "gate_false_alarm", "Alarm"),
)


def latex_gate_table(
    results: dict[str, dict[tuple[str, str], Estimate]], facts: dict[str, dict[str, Any]]
) -> str:
    """The gate table: per scheme, how often a gate that fails on new findings stays
    silent on a commit pair that introduced one (miss) and fails on one that did not
    (false alarm)."""
    columns = [c for c in GATE_COLUMNS if c[0] in results]
    groups: list[tuple[str, int]] = []
    for analyzer, _, _ in columns:
        if groups and groups[-1][0] == analyzer:
            groups[-1] = (analyzer, groups[-1][1] + 1)
        else:
            groups.append((analyzer, 1))
    titles = {
        "codeguard": "CodeGuard",
        "codeguard_security": "CG security",
        "bandit": "Bandit",
    }
    parts = []
    for analyzer, _ in groups:
        f = facts[analyzer]
        intro = results[analyzer][(TABLE_SCHEMES[0], "gate_miss")].den
        parts.append(
            f"{titles[analyzer]}: {intro:,} of {f['commit_pairs']:,} commit pairs "
            "introduce a finding"
        )
    bd = facts.get("bandit")
    without = f" other than {', '.join(bd['excluded'])}" if bd and bd["excluded"] else ""
    caption = (
        "A CI gate that fails when the scheme reports any finding as new, run on each "
        "commit pair, in percent with 95\\% cluster-bootstrap intervals. Miss: share of "
        "the commit pairs that introduce a finding on which the gate stays silent. Alarm: "
        "false alarms, the share of the other commit pairs on which it fails. CG security: "
        f"CodeGuard's security rules only. Bandit: Bandit's rules{without}. "
        + "; ".join(parts)
        + "."
    )
    lines = [
        "% Generated by research/finding_identity/paper_kit.py; do not edit by hand.",
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        "\\label{tab:gate}",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{1.2pt}",
        "\\begin{tabular}{@{}l" + "r" * len(columns) + "@{}}",
        "\\toprule",
    ]
    head, rules, col = "", [], 2
    for analyzer, n in groups:
        head += f" & \\multicolumn{{{n}}}{{c}}{{{titles[analyzer]}}}"
        rules.append(f"\\cmidrule(lr){{{col}-{col + n - 1}}}")
        col += n
    lines += [head + " \\\\", " ".join(rules)]
    lines += ["Scheme & " + " & ".join(c[2] for c in columns) + " \\\\", "\\midrule"]
    for scheme in TABLE_SCHEMES:
        cells = [_tex_stacked(results[a].get((scheme, m))) for a, m, _ in columns]
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
                if not run.keeps(rec["rule"]):
                    continue
                row = rows.setdefault(rec["rule"], {"known": 0, "introduced": 0, "in_tests": 0})
                row["known" if rec["truth"] == "known" else "introduced"] += 1
                row["in_tests"] += any(p in rec["path"].lower() for p in TEST_PATH_PARTS)
    ranked = sorted(rows.items(), key=lambda kv: -kv[1]["known"])[:top]
    return [{"rule": rule, **row} for rule, row in ranked]


def facts_for(runs: Sequence[Run]) -> dict[str, Any]:
    split = [_rename_split(r, "line") for r in runs]
    if any(r.filtered for r in runs):
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
        "prefix": runs[0].prefix if runs else "",
        "known_renamed": sum(s["false_new_renamed"][1] for s in split),
        "repos_with_renamed": sum(1 for s in split if s["false_new_renamed"][1]),
        "rules": rule_breakdown(runs),
    }


def _differences_markdown(diffs: Sequence[Difference]) -> list[str]:
    out = [
        "Paired differences between schemes on the same findings (percentage points, "
        "a - b), with 95% intervals from the same resamples. *Excludes 0*: the interval "
        "lies wholly on one side of zero.",
        "",
        "| metric | a | b | a - b | 95% CI | excludes 0 |",
        "|---|---|---|---:|---|---|",
    ]
    for d in diffs:
        ci = f"[{_pct(d.ci[0])}, {_pct(d.ci[1])}]" if d.ci else "n/a"
        excludes = "yes" if d.ci and (d.ci[0] > 0 or d.ci[1] < 0) else "no"
        out.append(f"| {d.metric} | `{d.a}` | `{d.b}` | {_pct(d.value)} | {ci} | {excludes} |")
    return [*out, ""]


def _dropped_markdown(table: dict[tuple[str, str], Estimate], resamples: int) -> list[str]:
    """Per metric, the resamples dropped for a zero denominator (the same for every
    scheme, since the denominator does not depend on the scheme)."""
    dropped: dict[str, int] = {}
    for (_, metric), e in table.items():
        if e.den:  # metrics not computed for these findings (no denominator) are left out
            dropped[metric] = max(dropped.get(metric, 0), e.dropped)
    out = [
        f"Bootstrap resamples (of {resamples:,}) left out because they hold no repository "
        "with a non-zero denominator:",
        "",
        "| metric | dropped |",
        "|---|---:|",
    ]
    out += [f"| {m} | {n:,} |" for m, n in dropped.items()]
    return [*out, ""]


def numbers_markdown(
    results: dict[str, dict[tuple[str, str], Estimate]],
    facts: dict[str, dict[str, Any]],
    sources: dict[str, Path],
    differences: dict[str, list[Difference]] | None = None,
    resamples: int = 10_000,
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
            + (f", only rules starting with {f['prefix']}" if f.get("prefix") else "")
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
        out.append("")
        if differences and differences.get(analyzer):
            out += _differences_markdown(differences[analyzer])
        out += _dropped_markdown(table, resamples)
        out += [
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
    differences: dict[str, list[Difference]] = {}
    exclude = frozenset(x.strip() for x in args.bandit_exclude.split(",") if x.strip())
    jobs: list[tuple[str, Path, frozenset[str], str]] = [
        ("codeguard", args.codeguard, frozenset(), ""),
        ("codeguard_security", args.codeguard, frozenset(), CODEGUARD_SECURITY_PREFIX),
    ]
    sources["codeguard_security"] = args.codeguard
    if args.bandit:
        jobs.append(("bandit", args.bandit, exclude, ""))
        if exclude:
            jobs.append(("bandit_all_rules", args.bandit, frozenset(), ""))
            sources["bandit_all_rules"] = args.bandit
    for analyzer, path, leave_out, prefix in jobs:
        wanted = [x for x in labels if (path / x / "summary.json").exists()]
        runs = load_runs(path, wanted, leave_out, prefix)
        facts[analyzer] = facts_for(runs)
        present = [s for s in TABLE_SCHEMES if all(s in r.summary["schemes"] for r in runs)]
        results[analyzer], differences[analyzer] = estimates_and_differences(
            runs, present, args.resamples, args.seed
        )

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "rq1.csv", results)
    (args.out / "table_rq1.tex").write_text(
        latex_table(results["codeguard"], results.get("bandit"), facts), encoding="utf-8"
    )
    (args.out / "table_gate.tex").write_text(latex_gate_table(results, facts), encoding="utf-8")
    (args.out / "numbers.md").write_text(
        numbers_markdown(results, facts, sources, differences, args.resamples),
        encoding="utf-8",
    )
    written = ["rq1.csv", "table_rq1.tex", "table_gate.tex", "numbers.md"]
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
