# SPDX-License-Identifier: Apache-2.0
"""Tests for the git diff helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from codeguard.engine.gitdiff import changed_files, default_base, is_git_repo


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_is_git_repo(repo: Path, tmp_path: Path) -> None:
    assert is_git_repo(repo)
    assert not is_git_repo(tmp_path.parent / "definitely-not-a-repo-xyz")


def test_default_base(repo: Path) -> None:
    assert default_base(repo) == "main"


def test_changed_files_committed(repo: Path) -> None:
    _git(repo, "checkout", "-b", "feature")
    (repo / "b.py").write_text("y = 2\n", encoding="utf-8")
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "work")

    changed = {p.name for p in changed_files("main", root=repo)}
    assert changed == {"a.py", "b.py"}


def test_changed_files_includes_untracked(repo: Path) -> None:
    (repo / "new.py").write_text("z = 3\n", encoding="utf-8")
    changed = {p.name for p in changed_files("main", root=repo)}
    assert "new.py" in changed


def test_changed_files_excludes_deleted(repo: Path) -> None:
    _git(repo, "checkout", "-b", "feature")
    _git(repo, "rm", "a.py")
    _git(repo, "commit", "-m", "remove")
    changed = {p.name for p in changed_files("main", root=repo)}
    assert "a.py" not in changed
