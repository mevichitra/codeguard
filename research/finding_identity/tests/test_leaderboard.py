"""The leaderboard: ranks, the best scheme, and the paired difference to it."""

import json
from pathlib import Path

from research.finding_identity.leaderboard import (
    Row,
    _rank,
    board_from_table,
    board_markdown,
    read_labels,
    rq1_board,
)
from research.finding_identity.paper_kit import estimate

SCHEMES = ("a", "b", "c")


def _summary(label: str, false_new: dict[str, int], known: int) -> dict[str, object]:
    schemes = {
        s: {
            "known_ok": known - false_new[s],
            "mispaired": 0,
            "false_new": false_new[s],
            "false_known": 0,
            "new_ok": 1,
        }
        for s in SCHEMES
    }
    return {
        "label": label,
        "schemes": list(SCHEMES),
        "totals": {
            "gt": {"known": known, "introduced": 1, "old": known, "new": known + 1},
            "schemes": schemes,
        },
        "collisions": {"observations": known + 1, "by_scheme": {s: 0 for s in SCHEMES}},
    }


def _write_repo(root: Path, label: str, false_new: dict[str, int], known: int) -> None:
    d = root / label
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps(_summary(label, false_new, known)))
    records = []
    for i in range(known):
        outcomes = {s: "false_new" if i < false_new[s] else "known_ok" for s in SCHEMES}
        records.append(
            {"commit": "c1", "rule": "R", "truth": "known", "status": "M", "outcomes": outcomes}
        )
    records.append(
        {
            "commit": "c1",
            "rule": "R",
            "truth": "new",
            "status": "M",
            "outcomes": dict.fromkeys(SCHEMES, "new_ok"),
        }
    )
    (d / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (d / "pairs.jsonl").write_text(json.dumps({"old": "c0", "new": "c1"}) + "\n")


def test_rank_is_dense_and_ties_share_a_rank() -> None:
    ranks, best = _rank({"a": 0.2, "b": 0.1, "c": 0.2})
    assert best == "b" and ranks == {"b": 1, "a": 2, "c": 2}
    assert _rank({}) == ({}, None)


def test_board_marks_the_best_and_a_scheme_that_ties_it() -> None:
    table = {
        ("a", "m"): [(1, 10), (2, 10)],  # 15%
        ("b", "m"): [(2, 10), (1, 10)],  # 15%, the same findings the other way round
        ("c", "m"): [(5, 10), (6, 10)],  # 55%
    }
    draws = [[0, 1], [1, 0], [0, 0], [1, 1]]
    board = board_from_table("t", table, SCHEMES, ["m"], draws, 2)
    assert board.rows[("a", "m")].is_best and board.rows[("b", "m")].rank == 1
    worst = board.rows[("c", "m")]
    assert worst.rank == 2 and worst.difference is not None
    value, ci = worst.difference
    assert value is not None and abs(value - 40) < 1e-9 and ci is not None and ci[0] > 0
    assert not worst.ties_best
    assert board.summary("c") == (0, 0, 1) and board.summary("a") == (1, 1, 1)
    text = "\n".join(board_markdown(board, {"m": "metric"}))
    assert "| `a` | **15.00 (" in text and "| 1 of 1 (ties 1) |" in text
    assert "| `c` | +40.00 [+40.00, +40.00] ✱ |" in text


def test_rq1_board_reads_replays_and_filters_repositories(tmp_path: Path) -> None:
    _write_repo(tmp_path, "x", {"a": 1, "b": 3, "c": 5}, 10)
    _write_repo(tmp_path, "y", {"a": 2, "b": 2, "c": 9}, 10)
    board = rq1_board("t", tmp_path, ["x", "y", "missing"], None, resamples=20, seed=1)
    assert board is not None and board.repos == 2 and board.schemes == SCHEMES
    row = board.rows[("a", "false_new")]
    assert row.is_best and row.estimate.num == 3 and row.estimate.den == 20
    assert board.rows[("c", "gate_false_alarm")].estimate.den == 0  # every pair introduces one
    only_y = rq1_board("t", tmp_path, ["y"], ["b", "a"], resamples=20, seed=1)
    assert only_y is not None and only_y.schemes == ("b", "a")
    assert only_y.rows[("a", "false_new")].rank == 1 and only_y.rows[("b", "false_new")].rank == 1


def test_read_labels_skips_comments(tmp_path: Path) -> None:
    f = tmp_path / "dev.txt"
    f.write_text("# dev split\nflask\n\nzulip # big\n")
    assert read_labels(f) == ["flask", "zulip"]


def test_row_without_an_interval_does_not_tie() -> None:
    row = Row(estimate([(1, 2)], [[0]]), 2, "a", (1.0, None))
    assert not row.ties_best
