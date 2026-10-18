"""drift_kit: corpus runs of drift mode, pooled over anchors, with bootstrap intervals."""

import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from research.finding_identity.drift_kit import (
    REPORT_SCHEMES,
    Task,
    estimates,
    fetch,
    first_parent_count,
    load_drift_runs,
    main,
    repo_counts,
    run_task,
    tasks_for,
)

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _scheme_counts(false_new: int, false_known: int = 0) -> dict[str, int]:
    return {
        "known_ok": 0,
        "mispaired": 0,
        "false_new": false_new,
        "false_known": false_known,
        "new_ok": 0,
        "false_new_equal": false_new,
        "false_new_edited": 0,
    }


def _entry(span: int, known: int, introduced: int, false_new: int, hidden: int) -> dict[str, Any]:
    return {
        "span": span,
        "commit": "c",
        "totals": {
            "gt": {
                "old": known,
                "new": known + introduced,
                "known": known,
                "known_equal": known,
                "known_edited": 0,
                "introduced": introduced,
                "removed": 0,
            },
            "schemes": {s: _scheme_counts(false_new, hidden) for s in REPORT_SCHEMES},
            "files": 1,
            "renamed_files": 0,
            "skipped_files": 0,
        },
        "collisions": {"observations": 0, "by_scheme": dict.fromkeys(REPORT_SCHEMES, 0)},
        "chains": {"tracked": known, "alive": known, "alive_edited": 0},
    }


def _write_run(root: Path, label: str, anchor: int, entries: list[dict[str, Any]]) -> Path:
    d = root / label / f"a{anchor}"
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps({"spans": entries}))
    records = [
        {
            "span": entries[0]["span"],
            "truth": "known",
            "path": "b.py" if i == 0 else "a.py",
            "old_path": "a.py",
            "outcomes": dict.fromkeys(REPORT_SCHEMES, "false_new" if i == 0 else "known_ok"),
        }
        for i in range(2)
    ]
    (d / "findings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    return d


@pytest.fixture
def results(tmp_path: Path) -> Path:
    root = tmp_path / "results"
    # Repository "a" has two anchors, which are pooled before the bootstrap.
    _write_run(root, "a", 200, [_entry(1, 10, 2, 1, 0), _entry(10, 10, 2, 3, 1)])
    _write_run(root, "a", 300, [_entry(1, 30, 0, 2, 0), _entry(10, 30, 0, 6, 0)])
    _write_run(root, "b", 200, [_entry(1, 20, 4, 0, 0), _entry(10, 20, 4, 4, 2)])
    return root


def test_counts_pool_the_anchors_of_a_repository(results: Path) -> None:
    runs = load_drift_runs(results)
    assert sorted(runs) == ["a", "b"] and len(runs["a"]) == 2
    labels, spans, table = repo_counts(runs, REPORT_SCHEMES)
    assert labels == ["a", "b"] and spans == [1, 10]
    assert table[(10, "codeguard", "false_new")] == [(9, 40), (4, 20)]
    assert table[(10, "codeguard", "hidden")] == [(1, 2), (2, 4)]
    assert table[(1, "_gt", "anchors")] == [(2, 1), (1, 1)]
    # The renamed split comes from the records: one renamed, one same-path per anchor.
    assert table[(1, "line", "false_new_renamed")] == [(2, 2), (1, 1)]
    assert table[(1, "line", "false_new_same_path")] == [(0, 2), (0, 1)]
    est = estimates(table, len(labels), 200, 1)
    e = est[(10, "codeguard", "false_new")]
    assert (e.num, e.den, e.repos) == (13, 60, 2)
    assert e.rate == pytest.approx(13 / 60)
    assert e.ci is not None and e.ci[0] <= e.rate <= e.ci[1]
    assert not any(k[1] == "_gt" for k in est)


def test_report_writes_the_paper_files(results: Path, tmp_path: Path) -> None:
    out = tmp_path / "paper"
    main(["report", str(results), "--out", str(out), "--resamples", "100"])
    with (out / "drift.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    row = next(
        r for r in rows if (r["span"], r["scheme"], r["metric"]) == ("10", "bandit", "hidden")
    )
    assert (row["num"], row["den"]) == ("3", "6")
    text = (out / "numbers_drift.md").read_text()
    assert "2 repositories, 3 anchors" in text and "## Hidden rate" in text
    assert "| `codeguard` | 5.0 [" in text  # span 1: 3 of 60, pooled over both repos
    pytest.importorskip("matplotlib")
    assert (out / "fig_drift.pdf").stat().st_size > 0


def test_tasks_need_anchors_at_least_the_window() -> None:
    with pytest.raises(ValueError, match="window"):
        tasks_for([], [100], 200, [1, 10])
    with pytest.raises(ValueError, match="window"):
        tasks_for([], [200], 100, [1, 200])


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, env=ENV, capture_output=True, text=True
    ).stdout


@pytest.fixture(scope="module")
def tiny(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = tmp_path_factory.mktemp("kit") / "tiny"
    repo.mkdir()
    _git(repo, "init", "-q")
    for i in range(4):
        (repo / "app.py").write_text("\n" * i + "def f(x):\n    return eval(x)\n")
        _git(repo, "add", "app.py")
        _git(repo, "commit", "-q", "-m", f"c{i}")
    return repo


def test_run_task_runs_an_anchor_and_skips_short_histories(tiny: Path, tmp_path: Path) -> None:
    sha = _git(tiny, "rev-parse", "HEAD").strip()
    workdir = tiny.parent
    ok = run_task(Task("tiny", sha, 3, 2, (1, 2)), workdir, tmp_path, ["security"])
    assert ok["status"] == "ok"
    summary = json.loads((tmp_path / "tiny" / "a3" / "summary.json").read_text())
    # The window ends 3 - 2 = 1 commit before the pin.
    assert summary["head"] == _git(tiny, "rev-parse", "HEAD~1").strip()
    assert [e["span"] for e in summary["spans"]] == [1, 2]
    again = run_task(Task("tiny", sha, 3, 2, (1, 2)), workdir, tmp_path, ["security"])
    assert again.get("cached") is True
    short = run_task(Task("tiny", sha, 9, 2, (1, 2)), workdir, tmp_path, ["security"])
    assert short["status"] == "skipped" and "only 3" in short["reason"]


def test_fetch_pins_the_commit_at_depth(tiny: Path, tmp_path: Path) -> None:
    sha = _git(tiny, "rev-parse", "HEAD").strip()
    assert fetch("copy", f"file://{tiny}", sha, tmp_path, 2) == 2
    assert first_parent_count(tmp_path / "copy", sha) == 2
    assert _git(tmp_path / "copy", "rev-parse", "pinned").strip() == sha
    # Deep enough already: no fetch, same answer.
    assert fetch("copy", f"file://{tiny}", sha, tmp_path, 2) == 2
