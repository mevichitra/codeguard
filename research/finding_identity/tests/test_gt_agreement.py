# SPDX-License-Identifier: Apache-2.0

"""Scoring the manual ground-truth check."""

import json
from pathlib import Path

from research.finding_identity.gt_agreement import (
    cohen_kappa,
    judgement,
    load_labels,
    precision_rows,
    report,
)


def test_cohen_kappa_against_hand_computed_values() -> None:
    # 4 of 6 agree; marginals a = {x: 3, y: 3}, b = {x: 3, y: 3}: pe = 0.5, kappa = 1/3.
    a = ["x", "x", "x", "y", "y", "y"]
    b = ["x", "x", "y", "y", "y", "x"]
    assert abs(cohen_kappa(a, b) - 1 / 3) < 1e-12  # type: ignore[operator]
    assert cohen_kappa(a, a) == 1.0
    assert cohen_kappa(["x", "x"], ["x", "x"]) is None  # chance agreement is total
    assert cohen_kappa([], []) is None


def test_judgement_maps_both_question_kinds() -> None:
    assert judgement("same") == judgement("new") == "confirms"
    assert judgement("different") == judgement("existed") == "contradicts"
    assert judgement("unclear") == judgement(None) == "unclear"


def test_load_labels_from_a_file_and_from_exported_documents(tmp_path: Path) -> None:
    f = tmp_path / "agent.json"
    f.write_text(json.dumps({"F001": {"verdict": "same", "reason": "r"}, "F002": {}}))
    assert load_labels(f) == {"F001": "same"}
    d = tmp_path / "export" / "data" / "labels" / "items"
    d.mkdir(parents=True)
    (d / "F001.json").write_text(json.dumps({"verdict": "new", "note": ""}))
    (d / "F002.json").write_text(json.dumps({"data": {"verdict": "existed"}, "version": 3}))
    assert load_labels(tmp_path / "export") == {"F001": "new", "F002": "existed"}


def test_precision_rows_and_report() -> None:
    key = [
        {"item": "F001", "stratum": "a", "truth": "known (equal)"},
        {"item": "F002", "stratum": "a", "truth": "new"},
        {"item": "F003", "stratum": "b", "truth": "known (edited)"},
    ]
    human = {"F001": "same", "F002": "existed", "F003": "unclear"}
    rows = precision_rows(key, human, "stratum")
    assert rows == [("a", 1, 1, 0), ("b", 0, 0, 1), ("all", 1, 1, 1)]
    text = report(key, {"Human rater": human, "Agent rater": {"F001": "same", "F002": "new"}})
    assert "| a | 1 | 1 | 0 | 50.0% |" in text
    assert "1 agree (50.0%)" in text and "Items to adjudicate: F002." in text


def test_corresponding_old_line_follows_the_line_map() -> None:
    from research.finding_identity.gt_sample import corresponding_old_line

    old = ["a", "b", "c", "d"]
    new = ["a", "b", "x = eval(y)", "c", "d"]
    # The flagged line was inserted after "b": its place before the commit is old line 3.
    assert corresponding_old_line(old, new, 3) == (3, False)
    # An unchanged line maps back to itself.
    assert corresponding_old_line(old, new, 4) == (3, True)
    # A line added at the very top has no line above it.
    assert corresponding_old_line(old, ["new", *old], 1) == (1, False)


def test_corrected_hidden_scales_by_the_confirmed_share(tmp_path: Path) -> None:
    from research.finding_identity.gt_agreement import corrected_hidden

    run = tmp_path / "repo"
    run.mkdir()
    base = {"line_text": "new_ok", "github": "new_ok", "codeguard": "new_ok"}
    records = [
        {"truth": "new", "outcomes": {**base, "sonar": "false_known"}},
        {"truth": "new", "outcomes": {**base, "sonar": "false_known"}},
        {"truth": "new", "outcomes": {**base, "sonar": "new_ok"}},
        {"truth": "new", "outcomes": {**base, "sonar": "new_ok"}},
        {"truth": "known", "outcomes": {**base, "sonar": "known_ok"}},
    ]
    (run / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    key = [
        {"item": "A", "stratum": "new_but_matched", "disagreeing_schemes": "sonar"},
        {"item": "B", "stratum": "new_but_matched", "disagreeing_schemes": "sonar"},
    ]
    lines = corrected_hidden(key, {"A": "new", "B": "existed"}, tmp_path)
    # Hidden 2 of 4 introduced (50%); half the sampled matches are truly new: 25%.
    row = next(x for x in lines if x.startswith("| `sonar`"))
    assert row.startswith("| `sonar` | 50.00% (2) | 2 | 1 | 25.00% |")


def test_a_newer_replay_is_looked_up_item_by_item(tmp_path: Path) -> None:
    from research.finding_identity.gt_agreement import corrected_hidden, truth_agreement

    run = tmp_path / "repo"
    run.mkdir()
    where = {"commit": "c1", "path": "a.py", "rule": "R"}
    base = {"line_text": "new_ok", "github": "new_ok", "codeguard": "new_ok"}
    records = [
        # A: the newer ground truth says it persisted (it moved), so it is not hidden.
        {
            **where,
            "line": 5,
            "truth": "known",
            "old_line": 9,
            "outcomes": {**base, "sonar": "known_ok"},
        },
        # B: still introduced and still hidden by sonar.
        {**where, "line": 7, "truth": "new", "outcomes": {**base, "sonar": "false_known"}},
        {**where, "line": 8, "truth": "new", "outcomes": {**base, "sonar": "new_ok"}},
    ]
    (run / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    common = {
        "repository": "repo",
        **where,
        "stratum": "new_but_matched",
        "truth": "new",
        "old_line": "",
        "disagreeing_schemes": "sonar",
    }
    key = [{**common, "item": "A", "line": "5"}, {**common, "item": "B", "line": "7"}]
    verdicts = {"A": "existed", "B": "new"}
    lines = corrected_hidden(key, verdicts, tmp_path)
    # Hidden 1 of 2 introduced; the one sampled finding still hidden is truly new.
    row = next(x for x in lines if x.startswith("| `sonar`"))
    assert row.startswith("| `sonar` | 50.00% (1) | 1 | 1 | 50.00% |")
    agreement = "\n".join(truth_agreement(key, verdicts, tmp_path))
    assert "| introduced | 2 | 0 | 0 | 100.0% |" in agreement
