"""The observation cache: round trip, and a rescore that reproduces a live replay."""

import gzip
import json
import os
import subprocess
from pathlib import Path

from research.finding_identity.analyzers import RawFinding
from research.finding_identity.gitrepo import Change, GitRepo
from research.finding_identity.observations import ObservationReader, ObservationWriter
from research.finding_identity.replay import replay
from research.finding_identity.rescore import check, merge, rescore_one
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import ALL_SCHEMES, FindingMeta

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}

V1 = "def handler(expr):\n    return eval(expr)\n"
V2 = "import os\n\n\ndef handler(expr):\n    return eval(expr)\n"
V3 = "import os\n\n\ndef run(expr):\n    return eval(expr)\n"
JS = "const x = eval(y);\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=ENV, capture_output=True)


def _commit(repo: Path, files: dict[str, str], msg: str) -> None:
    for name, text in files.items():
        (repo / name).write_text(text)
        _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", msg)


def test_writer_and_reader_round_trip(tmp_path: Path) -> None:
    w = ObservationWriter(tmp_path / "rec")
    found = [
        RawFinding("R1", 2, 5, FindingMeta(message="m", severity="HIGH", semgrep_id="abc")),
        RawFinding("R2", 3, 1, FindingMeta()),
    ]
    w.version("a" * 40, "x.py", "ok", found)
    w.version("a" * 40, "x.py", "ok", [])  # the same version again: ignored
    w.version("b" * 40, "x.py", "parse", [])
    w.version("c" * 40, "y.js", "unsupported", [])
    w.pair("c1", "c2", [Change("M", "x.py", "x.py", "a" * 40, "b" * 40)])
    w.close({"label": "t", "head": "c2", "analyzer": {"analyzer": "codeguard"}})

    r = ObservationReader(tmp_path / "rec")
    assert len(r) == 3 and r.analyzer == "codeguard" and r.history == ["c1", "c2"]
    rec = r.version("a" * 40, "x.py")
    assert rec.status == "ok" and rec.findings == tuple(found)
    assert r.version("b" * 40, "x.py").status == "parse"
    assert r.version("c" * 40, "y.js").findings == ()
    assert r.changes("c1", "c2")[0].new_sha == "b" * 40
    with gzip.open(tmp_path / "rec" / "versions.jsonl.gz", "rt") as fh:
        first = json.loads(fh.readline())
    assert "semgrep_id" in first["findings"][0] and "cwe" not in first["findings"][1]


def _tiny_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-q")
    _commit(repo_dir, {"app.py": V1, "web.js": JS}, "v1")
    _commit(repo_dir, {"app.py": V2}, "v2")
    _commit(repo_dir, {"app.py": V3, "web.js": JS + "\n"}, "v3")
    return repo_dir


def _live(tmp_path: Path, repo_dir: Path, analyzer: str) -> Path:
    out = tmp_path / f"live-{analyzer}" / "tiny"
    writer = ObservationWriter(tmp_path / f"obs-{analyzer}" / "tiny")
    repo = GitRepo(repo_dir)
    scanner = Scanner(["CG-SEC-003"], ALL_SCHEMES, analyzer=analyzer, record_to=writer)
    try:
        replay(
            repo,
            ref="HEAD",
            commits=2,
            scanner=scanner,
            schemes=ALL_SCHEMES,
            out_dir=out,
            label="tiny",
            categories=["security"],
            details=True,
            observations=writer,
        )
    finally:
        repo.close()
    return out


def _same(a: Path, b: Path) -> None:
    sa = json.loads((a / "summary.json").read_text())
    sb = json.loads((b / "summary.json").read_text())
    for key in ("totals", "collisions", "by_category", "versions_scanned", "parse_failures"):
        assert sa[key] == sb[key], key
    for name in ("pairs.jsonl", "findings.jsonl"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_rescore_reproduces_a_live_replay(tmp_path: Path) -> None:
    repo_dir = _tiny_repo(tmp_path)
    live = _live(tmp_path, repo_dir, "codeguard")
    meta = json.loads((tmp_path / "obs-codeguard" / "tiny" / "meta.json").read_text())
    assert meta["versions"] == 5 and meta["pairs"] == 2  # app.py x3, web.js x2

    out = tmp_path / "rescored" / "tiny"
    rescore_one(tmp_path / "obs-codeguard" / "tiny", out, None, workdir=tmp_path)
    _same(out, live)
    assert check(out, live) == []
    described = json.loads((out / "analyzer.json").read_text())
    assert described["analyzer"] == "codeguard" and "observations" in described

    # A subset of schemes, scored without the analyzer, still agrees on those schemes.
    subset = tmp_path / "subset" / "tiny"
    rescore_one(
        tmp_path / "obs-codeguard" / "tiny", subset, ["line", "codeguard"], workdir=tmp_path
    )
    s = json.loads((subset / "summary.json").read_text())
    assert s["schemes"] == ["line", "codeguard"]
    assert s["totals"]["schemes"]["codeguard"]["false_new"] == 1
    assert check(subset, live) == []


def test_rescore_reproduces_bandit_with_unsupported_files(tmp_path: Path) -> None:
    repo_dir = _tiny_repo(tmp_path)
    live = _live(tmp_path, repo_dir, "bandit")
    out = tmp_path / "rescored-bandit" / "tiny"
    rescore_one(tmp_path / "obs-bandit" / "tiny", out, None, workdir=tmp_path)
    _same(out, live)
    reader = ObservationReader(tmp_path / "obs-bandit" / "tiny")
    assert {r.status for r in (reader.version(sha, p) for (sha, p) in reader._versions)} >= {
        "ok",
        "unsupported",
    }


def test_check_reports_a_changed_count(tmp_path: Path) -> None:
    repo_dir = _tiny_repo(tmp_path)
    live = _live(tmp_path, repo_dir, "codeguard")
    out = tmp_path / "rescored" / "tiny"
    rescore_one(tmp_path / "obs-codeguard" / "tiny", out, None, workdir=tmp_path)
    summary = json.loads((live / "summary.json").read_text())
    summary["totals"]["schemes"]["line"]["false_new"] += 1
    (live / "summary.json").write_text(json.dumps(summary))
    assert "totals differ" in check(out, live)


def test_merge_takes_the_other_schemes_from_an_earlier_run(tmp_path: Path) -> None:
    repo_dir = _tiny_repo(tmp_path)
    live = _live(tmp_path, repo_dir, "codeguard")
    out = tmp_path / "one-scheme" / "tiny"
    rescore_one(tmp_path / "obs-codeguard" / "tiny", out, ["cg_no_scope"], workdir=tmp_path)
    summary = merge(out, live)
    assert summary["schemes"] == list(ALL_SCHEMES) and summary["merged_from"] == str(live)
    _same(out, live)
    assert check(out, live) == []
    # A run whose ground truth differs cannot be merged.
    other = json.loads((live / "summary.json").read_text())
    other["totals"]["gt"]["known"] += 1
    (live / "summary.json").write_text(json.dumps(other))
    try:
        merge(out, live)
    except ValueError as exc:
        assert "ground truth differs" in str(exc)
    else:
        raise AssertionError("merge accepted a different ground truth")
