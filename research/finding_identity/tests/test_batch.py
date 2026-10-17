"""The batch runner: resume logic, failure isolation, and one real end-to-end run."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from research.finding_identity.batch import BatchOptions, is_done, run_batch
from research.finding_identity.corpus import (
    CorpusEntry,
    classify_license,
    count_source_files,
    load_corpus,
    save_corpus,
)

SHA_A = "a" * 40
SHA_B = "b" * 40


def _entry(label: str, sha: str, url: str = "https://example.invalid/x") -> CorpusEntry:
    return CorpusEntry(
        label=label,
        url=url,
        branch="main",
        sha=sha,
        pinned="2026-10-14",
        language="python",
        framework="Flask",
        license="MIT",
        rationale="test",
    )


def _write_summary(opts: BatchOptions, label: str, head: str, pairs: int) -> None:
    d = opts.out / label
    d.mkdir(parents=True, exist_ok=True)
    (d / "summary.json").write_text(json.dumps({"head": head, "commit_pairs": pairs}))


def test_is_done_requires_matching_sha_and_enough_pairs(tmp_path: Path) -> None:
    opts = BatchOptions(commits=200, out=tmp_path, workdir=tmp_path / "repos")
    entry = _entry("x", SHA_A)
    assert not is_done(entry, opts)
    _write_summary(opts, "x", SHA_A, 200)
    assert is_done(entry, opts)
    _write_summary(opts, "x", SHA_B, 200)  # pinned SHA changed since that run
    assert not is_done(entry, opts)
    _write_summary(opts, "x", SHA_A, 50)  # an earlier, shorter run
    assert not is_done(entry, opts)
    (opts.out / "x" / "summary.json").write_text("{not json")
    assert not is_done(entry, opts)


def test_is_done_requires_the_same_analyzer(tmp_path: Path) -> None:
    entry = _entry("x", SHA_A)
    codeguard = BatchOptions(commits=10, out=tmp_path, workdir=tmp_path / "repos")
    bandit = BatchOptions(commits=10, out=tmp_path, workdir=tmp_path, analyzer="bandit")
    _write_summary(codeguard, "x", SHA_A, 10)
    # Replays from before analyzer.json was written all used CodeGuard.
    assert is_done(entry, codeguard) and not is_done(entry, bandit)
    (tmp_path / "x" / "analyzer.json").write_text(json.dumps({"analyzer": "bandit"}))
    assert is_done(entry, bandit) and not is_done(entry, codeguard)
    (tmp_path / "x" / "analyzer.json").write_text("{not json")
    assert not is_done(entry, bandit) and not is_done(entry, codeguard)


def test_resume_skips_done_and_survives_failures(tmp_path: Path) -> None:
    opts = BatchOptions(commits=10, out=tmp_path / "out", workdir=tmp_path / "repos")
    entries = [_entry("done", SHA_A), _entry("stale", SHA_A), _entry("new", SHA_A)]
    entries.append(_entry("broken", SHA_A))
    _write_summary(opts, "done", SHA_A, 10)
    _write_summary(opts, "stale", SHA_B, 10)
    calls: list[str] = []

    def fake_runner(entry: CorpusEntry, o: BatchOptions) -> None:
        calls.append(entry.label)
        if entry.label == "broken":
            raise RuntimeError("clone failed")
        _write_summary(o, entry.label, entry.sha, o.commits)

    statuses = run_batch(entries, opts, jobs=2, runner=fake_runner)
    assert sorted(calls) == ["broken", "new", "stale"]
    assert [(s["label"], s["status"]) for s in statuses] == [
        ("done", "skipped"),
        ("stale", "ok"),
        ("new", "ok"),
        ("broken", "failed"),
    ]
    broken = statuses[3]
    assert "clone failed" in broken["error"]
    assert "RuntimeError" in (opts.out / "_logs" / "broken.log").read_text()
    journal = [json.loads(x) for x in (opts.out / "batch.jsonl").read_text().splitlines()]
    assert sorted(j["label"] for j in journal) == ["broken", "new", "stale"]

    # Second run: only the failed repository is retried.
    calls.clear()
    run_batch(entries, opts, jobs=2, runner=fake_runner)
    assert calls == ["broken"]

    # --force reruns everything.
    calls.clear()
    run_batch(entries, opts, jobs=1, force=True, runner=fake_runner)
    assert sorted(calls) == ["broken", "done", "new", "stale"]


ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, env=ENV, capture_output=True, text=True
    ).stdout


def test_run_one_end_to_end(tmp_path: Path) -> None:
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q")
    versions = [
        "def handler(expr):\n    return eval(expr)\n",
        "import os\n\n\ndef handler(expr):\n    return eval(expr)\n",
        "import os\n\n\ndef run(expr):\n    return eval(expr)\n",
    ]
    for i, text in enumerate(versions):
        (upstream / "app.py").write_text(text)
        _git(upstream, "add", "app.py")
        _git(upstream, "commit", "-q", "-m", f"v{i}")
    head = _git(upstream, "rev-parse", "HEAD").strip()
    # A commit after the pinned one must not be replayed.
    (upstream / "app.py").write_text("x = 1\n")
    _git(upstream, "commit", "-qam", "later")

    opts = BatchOptions(
        commits=2,
        out=tmp_path / "out",
        workdir=tmp_path / "repos",
        categories="security",
        delete_clones=True,
    )
    entry = _entry("tiny", head, url=upstream.as_uri())
    statuses = run_batch([entry], opts)
    assert statuses[0]["status"] == "ok", (opts.out / "_logs" / "tiny.log").read_text()
    summary = json.loads((opts.out / "tiny" / "summary.json").read_text())
    assert summary["head"] == head and summary["commit_pairs"] == 2
    sec = summary["by_category"]["security"]["totals"]
    assert sec["gt"]["known"] == 2
    assert sec["schemes"]["line"]["false_new"] == 1
    assert not (opts.workdir / "tiny").exists()
    assert run_batch([entry], opts)[0]["status"] == "skipped"


def test_run_one_with_bandit(tmp_path: Path) -> None:
    pytest.importorskip("bandit")
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q")
    versions = [
        "import subprocess\n\n\ndef run(cmd):\n    subprocess.call(cmd, shell=True)\n",
        "import os\nimport subprocess\n\n\ndef run(cmd):\n    subprocess.call(cmd, shell=True)\n",
    ]
    for i, text in enumerate(versions):
        (upstream / "app.py").write_text(text)
        _git(upstream, "add", "app.py")
        _git(upstream, "commit", "-q", "-m", f"v{i}")
    head = _git(upstream, "rev-parse", "HEAD").strip()

    opts = BatchOptions(
        commits=1, out=tmp_path / "out", workdir=tmp_path / "repos", analyzer="bandit"
    )
    entry = _entry("tiny", head, url=upstream.as_uri())
    statuses = run_batch([entry], opts)
    assert statuses[0]["status"] == "ok", (opts.out / "_logs" / "tiny.log").read_text()
    analyzer = json.loads((opts.out / "tiny" / "analyzer.json").read_text())
    assert analyzer["analyzer"] == "bandit"
    summary = json.loads((opts.out / "tiny" / "summary.json").read_text())
    assert summary["label"] == "tiny"  # no "-bandit" suffix: the batch names the run
    assert summary["totals"]["gt"]["known"] >= 1
    assert "sonar" in summary["totals"]["schemes"]


# ---------------------------------------------------------------------------
# Corpus helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "spdx"),
    [
        ("MIT License\n\nPermission is hereby granted, free of charge, to any person", "MIT"),
        ("Apache License\n  Version 2.0, January 2004", "Apache-2.0"),
        ("GNU AFFERO GENERAL PUBLIC LICENSE\n Version 3, 19 November 2007", "AGPL-3.0"),
        ("GNU GENERAL PUBLIC LICENSE\n Version 3, 29 June 2007", "GPL-3.0"),
        (
            "GNU GENERAL PUBLIC LICENSE\n Version 3\n"
            + "x " * 400
            + "GNU Affero General Public License",
            "GPL-3.0",
        ),
        ("GNU GENERAL PUBLIC LICENSE\n Version 2, June 1991", "GPL-2.0"),
        (
            "Redistribution and use in source and binary forms ... Neither the name of",
            "BSD-3-Clause",
        ),
        ("Redistribution and use in source and binary forms, with or without", "BSD-2-Clause"),
        ("This program is under the GNU General Public License, v. 3.0.", "GPL-3.0"),
        (
            "Portions of this software are licensed as follows: ee/ ... Permission is "
            "hereby granted, free of charge",
            "mixed (MIT)",
        ),
        ("Business Source License 1.1", "non-osi (business source license)"),
        ("All rights reserved.", "unknown"),
    ],
)
def test_classify_license(text: str, spdx: str) -> None:
    assert classify_license(text) == spdx


def test_count_source_files_skips_vendored_code() -> None:
    paths = ["app/views.py", "web/src/a.ts", "web/node_modules/x/index.js", "static/a.min.js"]
    assert count_source_files([*paths, "README.md"]) == (1, 1)


def test_corpus_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "corpus.csv"
    save_corpus(path, [_entry("a", SHA_A), _entry("b", SHA_B)])
    assert [e.sha for e in load_corpus(path)] == [SHA_A, SHA_B]
    save_corpus(path, [_entry("a", SHA_A), _entry("a", SHA_B)])
    with pytest.raises(ValueError, match="duplicate"):
        load_corpus(path)
