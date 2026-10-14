"""End to end: build a tiny repository and replay it."""

import os
import subprocess
from pathlib import Path

from research.finding_identity.gitrepo import GitRepo
from research.finding_identity.replay import replay
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import ALL_SCHEMES

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}

V1 = "def handler(expr):\n    return eval(expr)\n"
# Lines inserted above: line numbers shift, nothing else changes.
V2 = "import os\n\n\ndef handler(expr):\n    return eval(expr)\n"
# Function renamed: the line is untouched but its enclosing scope changes.
V3 = "import os\n\n\ndef run(expr):\n    return eval(expr)\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=ENV, capture_output=True)


def _commit(repo: Path, text: str, msg: str) -> None:
    (repo / "app.py").write_text(text)
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-q", "-m", msg)


def test_replay_scores_schemes(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-q")
    for text, msg in ((V1, "v1"), (V2, "v2"), (V3, "v3")):
        _commit(repo_dir, text, msg)

    repo = GitRepo(repo_dir)
    try:
        summary = replay(
            repo,
            ref="HEAD",
            commits=2,
            scanner=Scanner(["CG-SEC-003"], ALL_SCHEMES),
            schemes=ALL_SCHEMES,
            out_dir=tmp_path / "out",
            label="tiny",
            categories=["security"],
            details=True,
        )
    finally:
        repo.close()

    gt = summary["totals"]["gt"]
    assert gt["known"] == 2 and gt["introduced"] == 0
    schemes = summary["totals"]["schemes"]
    # v1 -> v2 (move): only the line-number scheme loses the finding.
    # v2 -> v3 (rename): only the scope-based schemes lose it.
    assert schemes["line"]["false_new"] == 1
    assert schemes["codeguard"]["false_new"] == 1
    assert schemes["cg_no_scope"]["false_new"] == 0
    assert schemes["line_text"]["false_new"] == 0
    assert (tmp_path / "out" / "summary.json").exists()
    records = (tmp_path / "out" / "findings.jsonl").read_text().splitlines()
    assert len(records) == 2
