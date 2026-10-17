"""The paper's RQ1 numbers: the rename split and the estimates."""

import json
from pathlib import Path

from research.finding_identity.paper_kit import Run, _rename_split, estimate, latex_table


def _run(tmp_path: Path, records: list[dict[str, object]]) -> Run:
    path = tmp_path / "findings.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return Run("x", {}, path)


def test_rename_split_counts_persisting_findings_only(tmp_path: Path) -> None:
    def rec(truth: str, status: str, outcome: str) -> dict[str, object]:
        return {"truth": truth, "status": status, "outcomes": {"s": outcome}}

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
