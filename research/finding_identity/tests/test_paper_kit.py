"""The paper's RQ1 numbers: the rename split and the estimates."""

import json
from pathlib import Path

from research.finding_identity.paper_kit import Run, _rename_split, estimate, latex_table


def _run(tmp_path: Path, records: list[dict[str, object]], commits: int = 1) -> Run:
    """A replay of *commits* pairs; records without a ``commit`` belong to the first."""
    path = tmp_path / "findings.jsonl"
    path.write_text("".join(json.dumps({"commit": "c0", **r}) + "\n" for r in records))
    pairs = "".join(json.dumps({"old": f"p{i}", "new": f"c{i}"}) + "\n" for i in range(commits))
    (tmp_path / "pairs.jsonl").write_text(pairs)
    return Run("x", {}, path)


def test_rename_split_counts_persisting_findings_only(tmp_path: Path) -> None:
    def rec(truth: str, status: str, outcome: str) -> dict[str, object]:
        return {"rule": "R", "truth": truth, "status": status, "outcomes": {"s": outcome}}

    run = _run(
        tmp_path,
        [
            rec("known", "M", "known_ok"),
            rec("known", "M", "false_new"),
            rec("known", "R", "false_new"),
            rec("new", "R", "false_known"),  # introduced: not part of the split
            rec("known", "A", "known_ok"),
        ],
    )
    assert _rename_split(run, "s") == {
        "false_new_same_path": (1, 3),
        "false_new_renamed": (1, 1),
    }


def test_estimate_pools_and_takes_the_median_of_repository_rates() -> None:
    pairs = [(1, 4), (3, 6), (0, 0)]
    draws = [[0, 1, 2], [0, 0, 1], [1, 1, 1]]
    e = estimate(pairs, draws)
    assert (e.num, e.den, e.rate) == (4, 10, 0.4)
    assert e.median == 0.375  # of 1/4 and 3/6; the repository without findings is left out
    assert e.ci is not None and e.ci[0] <= 0.4 <= e.ci[1]


def test_latex_table_marks_missing_schemes() -> None:
    facts = {"codeguard": {"repos": 1, "known": 10, "introduced": 2, "known_renamed": 0}}
    e = estimate([(1, 10)], [[0]])
    tex = latex_table({("line", "false_new"): e}, None, facts)
    assert "\\texttt{line} & 10.0 {\\scriptsize(10.0--10.0)} & -- &" in tex
    assert "\\texttt{sonar\\_branch} & -- &" in tex


def test_semgrep_table_has_a_row_for_semgreps_own_ids() -> None:
    from research.finding_identity.paper_kit import semgrep_table

    facts = {"semgrep": {"repos": 2, "known": 30, "introduced": 3, "known_renamed": 1}}
    sg = {
        ("line", "false_new"): estimate([(3, 30)], [[0]]),
        ("semgrep", "hidden"): estimate([(1, 4)], [[0]]),
    }
    tex = semgrep_table(sg, facts)
    assert "\\label{tab:rq1-semgrep}" in tex and "\\begin{tabular}{lrrr}" in tex
    assert "\\texttt{line} & 10.0 {\\scriptsize(10.0--10.0)} & -- & -- \\\\" in tex
    assert "\\texttt{semgrep} & -- & 25.0 {\\scriptsize(25.0--25.0)} & -- \\\\" in tex
    assert "2 repositories, 30 persisting and 3 introduced findings, 1 of" in tex


def test_rq2_pools_counts_over_repositories(tmp_path: Path) -> None:
    from research.finding_identity.paper_kit import load_matrices, rq2_estimates

    def write(label: str, false_new: int, known: int) -> None:
        d = tmp_path / f"transform-{label}"
        d.mkdir()
        head = "transform,scheme,false_new,target_known,hidden,introduced\n"
        rows = f"insert_top,line,{false_new},{known},0,0\ninsert_top,other,0,{known},0,0\n"
        (d / "matrix.csv").write_text(head + rows)

    write("a", 2, 4)
    write("b", 1, 6)
    matrices = load_matrices(tmp_path, ["a", "b", "missing"])
    assert list(matrices) == ["a", "b"]
    table = rq2_estimates(matrices, ["line"], resamples=50, seed=1)
    fn = table[("insert_top", "line", "false_new")]
    assert (fn.num, fn.den, fn.rate) == (3, 10, 0.3)
    assert table[("insert_top", "line", "hidden")].rate is None  # nothing introduced
    assert not any(key[1] == "other" for key in table)


def test_excluded_rules_leave_every_count(tmp_path: Path) -> None:
    from research.finding_identity.paper_kit import _record_counts, repo_counts

    def rec(rule: str, truth: str, outcome: str) -> dict[str, object]:
        return {"rule": rule, "truth": truth, "status": "M", "outcomes": {"s": outcome}}

    records = [
        rec("B101", "known", "false_new"),
        rec("B101", "new", "false_known"),
        rec("B602", "known", "known_ok"),
        rec("B602", "known", "mispaired"),
        rec("B602", "new", "false_known"),
        rec("B602", "new", "new_ok"),
    ]
    run = _run(tmp_path, records)
    run = type(run)(run.label, run.summary, run.findings, frozenset({"B101"}))
    assert _record_counts(run, "s") == {
        "false_new": (0, 2),
        "hidden": (1, 2),
        "mispair": (1, 2),
    }
    counts = repo_counts([run], "s")
    assert counts["false_new_same_path"] == [(0, 2)]
    assert counts["collision"] == [(0, 0)]  # not computable from the records
