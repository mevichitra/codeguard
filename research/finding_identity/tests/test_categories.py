"""Per-category totals: each category is scored on its own and they add up."""

import json
from pathlib import Path

from research.finding_identity.categories import UNKNOWN, category_of, split_by_category
from research.finding_identity.gitrepo import GitRepo
from research.finding_identity.matching import Observation
from research.finding_identity.replay import replay
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import ALL_SCHEMES
from research.finding_identity.tests.test_replay import _commit, _git

V1 = "def handler(expr):\n    try:\n        return eval(expr)\n    except:\n        pass\n"
# Lines inserted above both findings.
V2 = "import os\n\n\n" + V1
# eval() line edited; the bare except is untouched.
V3 = V2.replace("eval(expr)", "eval(expr.strip())")


def test_category_of() -> None:
    assert category_of("CG-SEC-003") == "security"
    assert category_of("CG-QUAL-002") == "quality"
    assert category_of("NOT-A-RULE") == UNKNOWN
    obs = [Observation("CG-SEC-003", 1, 0, {}), Observation("CG-QUAL-002", 2, 0, {})]
    assert {k: len(v) for k, v in split_by_category(obs).items()} == {
        "security": 1,
        "quality": 1,
    }


def test_replay_records_categories_that_add_up(tmp_path: Path) -> None:
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
            scanner=Scanner(["CG-SEC-003", "CG-QUAL-002"], ALL_SCHEMES),
            schemes=ALL_SCHEMES,
            out_dir=tmp_path / "out",
            label="tiny",
            categories=["security", "quality", "performance"],
        )
    finally:
        repo.close()

    by_cat = summary["by_category"]
    assert set(by_cat) == {"security", "quality", "performance"}
    assert by_cat["performance"]["totals"]["gt"]["new"] == 0
    sec, qual = by_cat["security"], by_cat["quality"]
    assert sec["totals"]["gt"]["known"] == 2 and qual["totals"]["gt"]["known"] == 2
    assert sec["totals"]["gt"]["known_edited"] == 1 and qual["totals"]["gt"]["known_edited"] == 0
    # line_text loses the edited eval() line, a security finding only.
    assert sec["totals"]["schemes"]["line_text"]["false_new"] == 1
    assert qual["totals"]["schemes"]["line_text"]["false_new"] == 0

    total = summary["totals"]
    for key, value in total["gt"].items():
        assert value == sum(c["totals"]["gt"][key] for c in by_cat.values())
    for scheme, outcome_counts in total["schemes"].items():
        for key, value in outcome_counts.items():
            assert value == sum(c["totals"]["schemes"][scheme][key] for c in by_cat.values())
    assert summary["collisions"]["observations"] == sum(
        c["collisions"]["observations"] for c in by_cat.values()
    )
    on_disk = json.loads((tmp_path / "out" / "summary.json").read_text())
    assert on_disk["by_category"] == by_cat
