# SPDX-License-Identifier: Apache-2.0
"""Git helpers for diff-aware scanning.

``scan --diff <ref>`` and ``codeguard ci`` only look at files that changed, so a
pull request is checked in seconds and only *new* problems surface.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_CANDIDATE_BASES = (
    "origin/main",
    "origin/master",
    "main",
    "master",
    "origin/HEAD",
)


def _git(args: list[str], *, root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def is_git_repo(root: Path) -> bool:
    return _git(["rev-parse", "--git-dir"], root=root) is not None


def default_base(root: Path) -> str | None:
    """Best guess at the branch a PR would target."""
    for ref in _CANDIDATE_BASES:
        if _git(["rev-parse", "--verify", "--quiet", ref], root=root) is not None:
            return ref
    return None


def changed_files(
    ref: str,
    *,
    root: Path,
    use_merge_base: bool = True,
    include_untracked: bool = True,
) -> list[Path]:
    """Return the files that changed relative to *ref* (added / modified, not deleted).

    ``use_merge_base`` compares against ``git merge-base ref HEAD`` (``ref...HEAD``),
    which is what you want for a pull request.  Set it False to diff against the
    literal *ref*.
    """
    spec = f"{ref}...HEAD" if use_merge_base else f"{ref}..HEAD"
    names: set[str] = set()

    committed = _git(["diff", "--name-only", "--diff-filter=d", spec], root=root)
    if committed:
        names.update(line for line in committed.splitlines() if line)

    # Uncommitted (working tree + index) changes vs HEAD, so a local run before
    # committing still sees the edits.
    working = _git(["diff", "--name-only", "--diff-filter=d", "HEAD"], root=root)
    if working:
        names.update(line for line in working.splitlines() if line)

    if include_untracked:
        untracked = _git(["ls-files", "--others", "--exclude-standard"], root=root)
        if untracked:
            names.update(line for line in untracked.splitlines() if line)

    return sorted((root / name) for name in names if (root / name).is_file())
