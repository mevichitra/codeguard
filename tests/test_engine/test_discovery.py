# SPDX-License-Identifier: Apache-2.0
"""Tests for file discovery."""

from __future__ import annotations

from pathlib import Path

from codeguard.engine.discovery import DiscoveryConfig, discover


def _make(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def test_finds_supported_extensions_only(tmp_path: Path) -> None:
    _make(tmp_path, {"a.py": "x=1\n", "b.txt": "nope\n", "c.md": "# no\n"})
    found = discover([tmp_path], root=tmp_path)
    assert [p.name for p in found] == ["a.py"]


def test_prunes_default_skip_dirs(tmp_path: Path) -> None:
    _make(
        tmp_path,
        {
            "src/app.py": "x=1\n",
            ".venv/lib/evil.py": "x=1\n",
            "node_modules/pkg/index.py": "x=1\n",
            "__pycache__/cached.py": "x=1\n",
        },
    )
    found = {p.relative_to(tmp_path).as_posix() for p in discover([tmp_path], root=tmp_path)}
    assert found == {"src/app.py"}


def test_respects_root_gitignore(tmp_path: Path) -> None:
    _make(
        tmp_path,
        {
            ".gitignore": "ignored/\n*.gen.py\n",
            "keep.py": "x=1\n",
            "ignored/skip.py": "x=1\n",
            "thing.gen.py": "x=1\n",
        },
    )
    found = {p.name for p in discover([tmp_path], root=tmp_path)}
    assert found == {"keep.py"}


def test_gitignore_can_be_disabled(tmp_path: Path) -> None:
    _make(tmp_path, {".gitignore": "secret.py\n", "secret.py": "x=1\n", "ok.py": "x=1\n"})
    cfg = DiscoveryConfig(respect_gitignore=False)
    found = {p.name for p in discover([tmp_path], cfg, root=tmp_path)}
    assert found == {"secret.py", "ok.py"}


def test_exclude_and_include_globs(tmp_path: Path) -> None:
    _make(tmp_path, {"src/a.py": "x=1\n", "src/b.py": "x=1\n", "tests/t.py": "x=1\n"})
    cfg = DiscoveryConfig(include=["src/**"], exclude=["src/b.py"])
    found = {p.relative_to(tmp_path).as_posix() for p in discover([tmp_path], cfg, root=tmp_path)}
    assert found == {"src/a.py"}


def test_named_file_bypasses_filters(tmp_path: Path) -> None:
    _make(tmp_path, {".gitignore": "*.py\n", "explicit.py": "x=1\n"})
    found = discover([tmp_path / "explicit.py"], root=tmp_path)
    assert [p.name for p in found] == ["explicit.py"]


def test_dedupes_and_sorts(tmp_path: Path) -> None:
    _make(tmp_path, {"b.py": "x=1\n", "a.py": "x=1\n"})
    found = discover([tmp_path, tmp_path / "a.py"], root=tmp_path)
    assert [p.name for p in found] == ["a.py", "b.py"]


def test_symlinked_dir_not_followed(tmp_path: Path) -> None:
    _make(tmp_path, {"real/mod.py": "x=1\n"})
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    found = {p.relative_to(tmp_path).as_posix() for p in discover([tmp_path], root=tmp_path)}
    assert found == {"real/mod.py"}
