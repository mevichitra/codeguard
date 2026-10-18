"""Gate-level metrics, paired differences and dropped resamples."""

import json
from pathlib import Path

from research.finding_identity.gate import gate_counts
from research.finding_identity.paper_kit import (
    Estimate,
    Run,
    dropped_resamples,
    latex_gate_table,
    paired_difference,
    repo_counts,
)


def _write(tmp_path: Path, records: list[dict[str, object]], commits: list[str]) -> None:
    (tmp_path / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (tmp_path / "pairs.jsonl").write_text(
        "".join(json.dumps({"old": "o" + c, "new": c}) + "\n" for c in commits)
    )


def _rec(commit: str, truth: str, outcome: str, rule: str = "CG-SEC-001") -> dict[str, object]:
    return {"commit": commit, "rule": rule, "truth": truth, "outcomes": {"s": outcome}}


def test_gate_scores_each_commit_pair(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [
            # a: the introduced finding is caught
            _rec("a", "new", "new_ok"),
            # b: hidden, and nothing else is reported new: the gate misses it
            _rec("b", "new", "false_known"),
            _rec("b", "known", "known_ok"),
            # c: hidden, but an old finding is reported new: the gate fails anyway
            _rec("c", "new", "false_known"),
            _rec("c", "known", "false_new"),
            # d: nothing introduced, an old finding reported new: a false alarm
            _rec("d", "known", "false_new"),
            # e: nothing introduced, nothing reported new
            _rec("e", "known", "mispaired"),
        ],
        ["a", "b", "c", "d", "e", "f"],  # f: no findings in the changed files at all
    )
    got = gate_counts(tmp_path / "pairs.jsonl", tmp_path / "findings.jsonl", ["s"])["s"]
    assert got["gate_miss"] == (1, 3)  # b, of a, b, c
    assert got["gate_wrong_reason"] == (1, 3)  # c
    assert got["gate_false_alarm"] == (1, 3)  # d, of d, e, f
    assert got["hidden_masked"] == (1, 3)  # c
    assert got["hidden_silent"] == (1, 3)  # b


def test_gate_checks_only_the_kept_rules(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [_rec("a", "new", "false_known"), _rec("a", "known", "false_new", rule="CG-QUAL-001")],
        ["a"],
    )
    paths = (tmp_path / "pairs.jsonl", tmp_path / "findings.jsonl")
    every = gate_counts(*paths, ["s"])["s"]
    security = gate_counts(*paths, ["s"], keep=lambda r: r.startswith("CG-SEC"))["s"]
    assert every["gate_miss"] == (0, 1)  # the quality finding makes the gate fail
    assert security["gate_miss"] == (1, 1)  # without it the hidden finding slips through


def test_run_prefix_filters_rules_in_repo_counts(tmp_path: Path) -> None:
    _write(
        tmp_path,
        [_rec("a", "new", "false_known"), _rec("a", "known", "false_new", rule="CG-QUAL-001")],
        ["a"],
    )
    run = Run("x", {}, tmp_path / "findings.jsonl", prefix="CG-SEC")
    c = repo_counts([run], "s")
    assert c["hidden"] == [(1, 1)]
    assert c["false_new"] == [(0, 0)]  # the quality finding is left out
    assert c["gate_miss"] == [(1, 1)]


def test_paired_difference_uses_the_same_resamples() -> None:
    a = [(2, 10), (0, 10)]
    b = [(1, 10), (0, 10)]
    draws = [[0, 0], [1, 1], [0, 1]]
    value, ci = paired_difference(a, b, draws)
    assert value is not None and abs(value - 0.05) < 1e-12
    # Per draw: 0.2 - 0.1, 0 - 0, 0.1 - 0.05; the interval lies within their range.
    assert ci is not None and 0.0 <= ci[0] < 0.05 < ci[1] <= 0.1


def test_dropped_resamples_counts_draws_without_a_denominator() -> None:
    pairs = [(0, 0), (1, 5), (0, 0)]
    draws = [[0, 2, 0], [0, 1, 2], [2, 2, 2]]
    assert dropped_resamples(pairs, draws) == 2
    assert dropped_resamples([(1, 1)], draws[:1]) == 0


def test_gate_table_has_a_column_per_analyzer_and_metric() -> None:
    e = Estimate(1, 4, 0.25, (0.1, 0.4), 0.25)
    results = {
        "codeguard": {("line", "gate_miss"): e, ("line", "gate_false_alarm"): e},
        "bandit": {("line", "gate_miss"): e, ("line", "gate_false_alarm"): e},
    }
    facts = {
        "codeguard": {"commit_pairs": 10, "excluded": []},
        "bandit": {"commit_pairs": 8, "excluded": ["B101"]},
    }
    tex = latex_gate_table(results, facts)
    assert "\\multicolumn{2}{c}{CodeGuard} & \\multicolumn{2}{c}{Bandit}" in tex
    assert "CG security" not in tex.split("\\caption")[0]
    assert "rules other than B101" in tex
    assert "\\texttt{line} & \\begin{tabular}[t]{@{}r@{}}25.0\\\\{\\scriptsize(10.0--40.0)}" in tex
    assert "\\texttt{sonar\\_branch} & -- & -- & -- & --" in tex
