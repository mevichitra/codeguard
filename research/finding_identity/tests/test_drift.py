"""Drift mode: chained ground truth and per-span outcomes on a tiny repository.

History (one change per commit, c0 is the anchor):

c1  three lines inserted above both findings in app.py      (moves E and X)
c2  the eval line E is edited                                (E becomes "edited")
c3  lib.py renamed to pkg/lib.py, content unchanged          (moves L to a new path)
c4  the function around the exec line X is renamed           (changes X's scope)
c5  a new function whose line equals E's original text       (a new finding N)
"""

import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from research.finding_identity.drift import chain_lines, drift, trace_files
from research.finding_identity.gitrepo import Change, GitRepo
from research.finding_identity.linemap import map_lines
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import ALL_SCHEMES
from research.finding_identity.summarize import summarize_drift

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}

APP_C0 = "def handler(expr):\n    return eval(expr)\n\n\ndef runner(code):\n    exec(code)\n"
APP_C1 = "import os\n\n\n" + APP_C0
APP_C2 = APP_C1.replace("eval(expr)", "eval(expr.strip())")
APP_C4 = APP_C2.replace("def runner", "def execute")
APP_C5 = APP_C4 + "\n\ndef other(expr):\n    return eval(expr)\n"
LIB = "def load(data):\n    return eval(data)\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=ENV, capture_output=True)


def _commit(repo: Path, files: dict[str, str], msg: str) -> None:
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
        _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", msg)


@pytest.fixture(scope="module")
def repo_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("drift") / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _commit(repo, {"app.py": APP_C0, "lib.py": LIB}, "c0")
    _commit(repo, {"app.py": APP_C1}, "c1")
    _commit(repo, {"app.py": APP_C2}, "c2")
    (repo / "pkg").mkdir()
    _git(repo, "mv", "lib.py", "pkg/lib.py")
    _git(repo, "commit", "-q", "-m", "c3")
    _commit(repo, {"app.py": APP_C4}, "c4")
    _commit(repo, {"app.py": APP_C5}, "c5")
    return repo


@pytest.fixture(scope="module")
def summary(repo_dir: Path, tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    out = tmp_path_factory.mktemp("out")
    repo = GitRepo(repo_dir)
    try:
        return drift(
            repo,
            ref="HEAD",
            anchor_back=5,
            spans=[1, 2, 3, 4, 5],
            scanner=Scanner(["CG-SEC-003"], ALL_SCHEMES),
            schemes=ALL_SCHEMES,
            out_dir=out,
            label="tiny",
            categories=["security"],
            details=True,
        )
    finally:
        repo.close()


def _span(summary: dict[str, Any], k: int) -> dict[str, Any]:
    return next(e for e in summary["spans"] if e["span"] == k)


def _outcomes(entry: dict[str, Any], scheme: str) -> dict[str, int]:
    counts = entry["totals"]["schemes"][scheme]
    return {k: v for k, v in counts.items() if v and not k.startswith("false_new_")}


def test_chained_ground_truth(summary: dict[str, Any]) -> None:
    # Span 1 and 2 compare app.py only: lib.py is unchanged until c3.
    gt = [_span(summary, k)["totals"]["gt"] for k in (1, 2, 3, 4, 5)]
    assert [g["old"] for g in gt] == [2, 2, 3, 3, 3]
    assert [g["known"] for g in gt] == [2, 2, 3, 3, 3]
    # E's line was edited at c2; the flag stays set for every later span.
    assert [g["known_edited"] for g in gt] == [0, 1, 1, 1, 1]
    assert [g["introduced"] for g in gt] == [0, 0, 0, 0, 1]
    renamed = [_span(summary, k)["totals"]["renamed_files"] for k in (1, 2, 3, 4, 5)]
    assert renamed == [0, 0, 1, 1, 1]  # lib.py -> pkg/lib.py, followed from c3 on
    assert _span(summary, 5)["chains"] == {"tracked": 3, "alive": 3, "alive_edited": 1}


def test_span_1_insertion_only_breaks_line_numbers(summary: dict[str, Any]) -> None:
    entry = _span(summary, 1)
    assert _outcomes(entry, "line") == {"false_new": 2}
    for scheme in ALL_SCHEMES[1:]:
        assert _outcomes(entry, scheme) == {"known_ok": 2}, scheme


def test_span_2_edit_loses_the_edited_finding(summary: dict[str, Any]) -> None:
    entry = _span(summary, 2)
    for scheme in ALL_SCHEMES[1:]:
        assert _outcomes(entry, scheme) == {"known_ok": 1, "false_new": 1}, scheme
        assert entry["totals"]["schemes"][scheme]["false_new_edited"] == 1


def test_span_3_file_rename_breaks_every_path_based_key(summary: dict[str, Any]) -> None:
    entry = _span(summary, 3)
    # The ground truth follows lib.py -> pkg/lib.py, but every key includes the path.
    for scheme in ALL_SCHEMES[1:]:
        assert _outcomes(entry, scheme) == {"known_ok": 1, "false_new": 2}, scheme


def test_span_4_function_rename_breaks_scoped_keys(summary: dict[str, Any]) -> None:
    entry = _span(summary, 4)
    for scheme in ("codeguard", "cg_no_mask", "cg_raw"):
        assert _outcomes(entry, scheme) == {"false_new": 3}, scheme
    for scheme in ("line_text", "github", "cg_no_scope"):
        assert _outcomes(entry, scheme) == {"known_ok": 1, "false_new": 2}, scheme


def test_span_5_new_finding_hidden_by_text_keys(summary: dict[str, Any]) -> None:
    entry = _span(summary, 5)
    # N's line equals E's text at c0: keys without a scope match N to E and hide it.
    for scheme in ("line_text", "cg_no_scope"):
        assert _outcomes(entry, scheme) == {"known_ok": 1, "false_new": 2, "false_known": 1}
    # The scope tells N apart from E.
    assert _outcomes(entry, "codeguard") == {"false_new": 3, "new_ok": 1}
    # GitHub's hash reads the text after the line, and code was appended after X.
    assert _outcomes(entry, "github") == {"false_new": 3, "new_ok": 1}


def test_summary_metadata(summary: dict[str, Any]) -> None:
    assert summary["mode"] == "drift" and summary["anchor_back"] == 5
    assert [e["span"] for e in summary["spans"]] == [1, 2, 3, 4, 5]
    assert summary["spans"][-1]["commit"] == summary["head"]


def test_details_and_drift_summary(
    repo_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = GitRepo(repo_dir)
    try:
        drift(
            repo,
            ref="HEAD",
            anchor_back=5,
            spans=[3, 5],
            scanner=Scanner(["CG-SEC-003"], ALL_SCHEMES),
            schemes=ALL_SCHEMES,
            out_dir=tmp_path / "run",
            label="tiny",
            categories=["security"],
            details=True,
        )
    finally:
        repo.close()
    records = [
        json.loads(line) for line in (tmp_path / "run" / "findings.jsonl").read_text().splitlines()
    ]
    renamed = [r for r in records if r["path"] == "pkg/lib.py"]
    assert [(r["span"], r["old_path"], r["truth"]) for r in renamed] == [
        (3, "lib.py", "known"),
        (5, "lib.py", "known"),
    ]
    summarize_drift([tmp_path / "run", tmp_path / "run"], tmp_path / "rates.csv")
    printed = capsys.readouterr().out
    assert "span 5" in printed and "false-new %" in printed and "ALL: pooled" in printed
    with (tmp_path / "rates.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3 * 2 * len(ALL_SCHEMES)  # (tiny, tiny, ALL) x spans x schemes
    line_k3 = next(
        r for r in rows if r["label"] == "ALL" and r["span"] == "3" and r["scheme"] == "line"
    )
    assert float(line_k3["false_new_rate"]) == 1.0


def test_spans_must_fit_the_anchor(repo_dir: Path, tmp_path: Path) -> None:
    repo = GitRepo(repo_dir)
    try:
        with pytest.raises(ValueError, match="spans"):
            drift(
                repo,
                ref="HEAD",
                anchor_back=3,
                spans=[5],
                scanner=Scanner(["CG-SEC-003"], ALL_SCHEMES),
                schemes=ALL_SCHEMES,
                out_dir=tmp_path,
                label="tiny",
                categories=["security"],
            )
        with pytest.raises(ValueError, match="first-parent commits"):
            drift(
                repo,
                ref="HEAD",
                anchor_back=9,
                spans=[1],
                scanner=Scanner(["CG-SEC-003"], ALL_SCHEMES),
                schemes=ALL_SCHEMES,
                out_dir=tmp_path,
                label="tiny",
                categories=["security"],
            )
    finally:
        repo.close()


# -- chaining without git ---------------------------------------------------------


def _m(path: str, old: str, new: str) -> Change:
    return Change("M", path, path, old, new)


def test_chain_follows_a_gradual_rewrite_a_direct_diff_loses() -> None:
    blobs = {
        "v0": ["a = 1", "result = eval(expr)", "b = 2"],
        "v1": ["a = 1", "result = eval(expr, scope)", "b = 2"],
        "v2": ["a = 1", "value = safe_eval(expr, scope)", "b = 2"],
    }
    # Each step is a small edit, but v0 and v2 are too different to pair directly.
    assert 2 not in map_lines(blobs["v0"], blobs["v2"])
    steps = [[_m("f.py", "v0", "v1")], [_m("f.py", "v1", "v2")]]
    positions = chain_lines(steps, {"f.py": [1, 2]}, [1, 2], blobs.__getitem__)
    assert positions[1][("f.py", 2)] == ("f.py", 2, True)
    assert positions[2][("f.py", 2)] == ("f.py", 2, True)
    assert positions[2][("f.py", 1)] == ("f.py", 1, False)


def test_chain_breaks_on_delete_and_follows_renames() -> None:
    blobs = {"a0": ["x", "y"], "a1": ["new", "x", "y"]}
    steps = [
        [Change("R", "a.py", "b.py", "a0", "a0")],  # pure rename: no blob read
        [_m("b.py", "a0", "a1")],
        [Change("D", "b.py", None, "a1", None)],
    ]
    positions = chain_lines(steps, {"a.py": [2]}, [1, 2, 3], blobs.__getitem__)
    assert positions[1][("a.py", 2)] == ("b.py", 2, False)
    assert positions[2][("a.py", 2)] == ("b.py", 3, False)
    assert positions[3][("a.py", 2)] is None


def test_trace_files_handles_a_rename_swap() -> None:
    steps = [
        [Change("R", "a.py", "b.py", "1", "1"), Change("R", "b.py", "a.py", "2", "2")],
        [_m("c.py", "3", "4")],
        [Change("A", None, "d.py", None, "5")],
    ]
    first_touch, origins = trace_files(["a.py", "b.py", "c.py", "e.py"], steps, [1, 3])
    assert first_touch == {"a.py": 1, "b.py": 1, "c.py": 2}
    assert origins[1] == {"b.py": "a.py", "a.py": "b.py", "c.py": "c.py", "e.py": "e.py"}
    assert "d.py" not in origins[3]  # added after the anchor: no lineage
