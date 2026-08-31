# SPDX-License-Identifier: Apache-2.0
"""File discovery -- decide which files a scan should look at.

Rules never touch the filesystem; the runner asks this module for a list of
files.  Discovery honours ``.gitignore`` (repo root), a built-in skip list for
directories that never contain first-party source, and user ``--include`` /
``--exclude`` globs.  Directory symlinks are not followed and every file is
de-duplicated by real path.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pathspec

from codeguard.lang.registry import language_for_path

#: Directory names that never hold first-party source.  Pruned before globbing.
DEFAULT_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".bzr",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".env",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".tox",
        ".nox",
        ".eggs",
        "dist",
        "build",
        "site-packages",
        ".cache",
        ".idea",
        ".vscode",
    }
)

#: Filename globs skipped by default (generated / vendored artefacts).
DEFAULT_SKIP_FILES: tuple[str, ...] = ("*.min.js", "*.bundle.js", "*.d.ts")


@dataclass
class DiscoveryConfig:
    """Inputs that shape a discovery pass."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    respect_gitignore: bool = True
    skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS
    skip_files: tuple[str, ...] = DEFAULT_SKIP_FILES


def _load_gitignore(root: Path) -> pathspec.PathSpec[Any] | None:
    patterns: list[str] = []
    for rel in (".gitignore", ".git/info/exclude"):
        p = root / rel
        if p.is_file():
            patterns.extend(p.read_text(encoding="utf-8", errors="replace").splitlines())
    if not patterns:
        return None
    return pathspec.PathSpec.from_lines("gitignore", patterns)


def _spec(patterns: Iterable[str]) -> pathspec.PathSpec[Any] | None:
    patterns = [p for p in patterns if p.strip()]
    return pathspec.PathSpec.from_lines("gitignore", patterns) if patterns else None


def discover(
    paths: Sequence[str | Path],
    config: DiscoveryConfig | None = None,
    *,
    root: str | Path | None = None,
) -> list[Path]:
    """Return the sorted, de-duplicated list of files to scan.

    Parameters
    ----------
    paths:
        Files or directories given on the command line.
    config:
        Discovery settings.  Defaults are used when omitted.
    root:
        Base directory for ``.gitignore`` lookup and relative-path matching.
        Defaults to the current working directory.
    """
    cfg = config or DiscoveryConfig()
    base = Path(root or os.getcwd()).resolve()

    gitignore = _load_gitignore(base) if cfg.respect_gitignore else None
    include_spec = _spec(cfg.include)
    exclude_spec = _spec([*cfg.exclude, *cfg.skip_files])

    seen: set[Path] = set()
    out: list[Path] = []

    def rel(p: Path) -> str:
        try:
            return p.resolve().relative_to(base).as_posix()
        except ValueError:
            return p.name

    def want(p: Path) -> bool:
        if language_for_path(p) is None:
            return False
        r = rel(p)
        if exclude_spec and exclude_spec.match_file(r):
            return False
        if gitignore and gitignore.match_file(r):
            return False
        if include_spec and not include_spec.match_file(r):
            return False
        return True

    def add(p: Path) -> None:
        real = p.resolve()
        if real in seen:
            return
        seen.add(real)
        out.append(p)

    for raw in paths:
        start = Path(raw)
        if start.is_file():
            # An explicitly named file bypasses include/exclude/gitignore
            # (the user asked for it) but still must be a supported language.
            if language_for_path(start) is not None:
                add(start)
            continue
        if not start.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
            d = Path(dirpath)
            dirnames[:] = [
                name
                for name in dirnames
                if name not in cfg.skip_dirs
                and not (d / name).is_symlink()
                and not (gitignore and gitignore.match_file(rel(d / name) + "/"))
            ]
            for name in filenames:
                fp = d / name
                if not fp.is_symlink() and want(fp):
                    add(fp)

    out.sort(key=lambda p: p.as_posix())
    return out
