"""End to end: run the transformation experiment on a small fixture directory."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("libcst")

from research.finding_identity.cli import main
from research.finding_identity.experiment import ground_truth_map, run_experiment
from research.finding_identity.matching import Observation
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import ALL_SCHEMES
from research.finding_identity.transforms import Edit, deterministic_transforms

HANDLERS = '''\
"""Request handlers."""
import subprocess


def parse(expr):
    value = eval(expr)
    return value


def run(cmd):
    code = subprocess.call(cmd, shell=True)
    return code
'''
MODELS = """\
class Model:
    def load(self, blob):
        data = eval(blob)
        return data


def unused():
    return 1
"""
NO_FINDINGS = "def ok():\n    return 1\n"


def _fixture(root: Path) -> None:
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "handlers.py").write_text(HANDLERS)
    (root / "pkg" / "models.py").write_text(MODELS)
    (root / "pkg" / "clean.py").write_text(NO_FINDINGS)
    (root / "pkg" / "broken.py").write_text("def broken(:\n")


def _rows(out: Path) -> dict[tuple[str, str], dict[str, Any]]:
    with (out / "matrix.csv").open() as fh:
        return {(r["transform"], r["scheme"]): r for r in csv.DictReader(fh)}


def test_invariance_matrix(tmp_path: Path) -> None:
    _fixture(tmp_path / "src")
    out = tmp_path / "out"
    summary = run_experiment(
        tmp_path / "src",
        label="fixture",
        transforms=deterministic_transforms(),
        scanner=Scanner(["CG-SEC-003", "CG-SEC-005"], ALL_SCHEMES),
        schemes=ALL_SCHEMES,
        samples=10,
        seed=1,
        out_dir=out,
    )
    assert summary["files_with_findings"] == 2
    rows = _rows(out)

    def rate(transform: str, scheme: str, key: str = "false_new_rate") -> float:
        return float(rows[(transform, scheme)][key])

    # Lines inserted at the top move every finding: only the line number breaks.
    assert rate("insert_top", "line") == 1.0
    assert all(rate("insert_top", s) == 0.0 for s in ALL_SCHEMES if s != "line")
    # A comment right below the finding changes the text GitHub's hash reads.
    assert rate("insert_below", "github") == 1.0 and rate("insert_below", "codeguard") == 0.0
    # Renaming the enclosing function breaks exactly the schemes that include the scope.
    assert rate("rename_function", "codeguard") == 1.0
    assert rate("rename_function", "cg_raw") == 1.0
    assert rate("rename_function", "cg_no_scope") == 0.0
    assert rate("rename_function", "line_text") == 0.0
    # Extracting into a helper changes the scope and the position, not the statement.
    assert rate("extract_helper", "cg_no_scope") == 0.0
    assert rate("extract_helper", "codeguard") == 1.0
    # A copy below the finding takes over its GitHub hash: the new finding is hidden.
    assert rate("duplicate_below", "github", "hidden_rate") == 1.0
    assert rate("duplicate_below", "codeguard", "hidden_rate") == 0.0
    # A copy above it is paired first by every key scheme and by the line number.
    assert rate("duplicate_above", "line", "hidden_rate") == 1.0
    assert rate("duplicate_above", "codeguard", "hidden_rate") == 1.0
    assert rate("duplicate_above", "github", "hidden_rate") == 0.0
    assert float(rows[("duplicate_above", "codeguard")]["collision_rate"]) > 0

    cases = [json.loads(line) for line in (out / "cases.jsonl").read_text().splitlines()]
    assert {c["transform"] for c in cases} >= {"insert_top", "duplicate_below"}
    assert all(c["status"] == "scored" for c in cases)
    assert (out / "summary.json").exists() and (out / "matrix.md").exists()


def test_cli_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _fixture(tmp_path / "src")
    out = tmp_path / "out"
    argv = ["transform", str(tmp_path / "src"), "--transforms", "insert_top,rename_local"]
    main([*argv, "--samples", "1", "--categories", "security", "--out", str(out)])
    assert set(row[0] for row in _rows(out)) == {"insert_top", "rename_local"}
    assert "false-new %" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        main(["transform", str(tmp_path / "src"), "--transforms", "ai_refactor"])


def test_ground_truth_follows_the_finding_into_a_split_line() -> None:
    old = [Observation("R", 1, 1, {})]
    new = [Observation("R", 3, 5, {})]
    edit = Edit("a\nb\nc\n", {1: 1}, alternatives={1: (1, 3)})
    assert ground_truth_map(edit, "a\n", "a\nb\nc\n", old, new) == {1: (3, "edited")}


LOOP = """\
def join(items):
    out = ""
    for item in items:
        out += str(item)
    return out
"""


def test_a_finding_the_change_makes_undetectable_is_lost_not_scored(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "loop.py").write_text(LOOP)
    summary = run_experiment(
        tmp_path / "src",
        label="loop",
        transforms={"extract_helper": deterministic_transforms()["extract_helper"]},
        scanner=Scanner(["CG-PERF-002"], ALL_SCHEMES),
        schemes=ALL_SCHEMES,
        samples=1,
        seed=0,
        out_dir=tmp_path / "out",
    )
    totals = summary["totals"]["extract_helper"]
    # Outside its loop, `out += ...` is no longer a finding: lost, and nothing scored.
    assert totals["target_lost"] == 1 and totals["target_lost_rules"] == {"CG-PERF-002": 1}
    assert totals["cases"] == 0 and totals["not_applicable"] == {"target lost": 1}
