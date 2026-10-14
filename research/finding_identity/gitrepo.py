"""Minimal git access for the replay: history, per-commit changes, and blob contents."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import IO

_NULL_SHA = "0" * 40
_SKIP_MODES = {"160000", "120000"}  # submodules and symlinks


@dataclass(frozen=True)
class Change:
    """One file changed between two commits. A missing side is ``None``."""

    status: str  # A, D, M, R (rename), C (copy), T (type change)
    old_path: str | None
    new_path: str | None
    old_sha: str | None
    new_sha: str | None


class GitRepo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._batch: subprocess.Popen[bytes] | None = None

    # -- construction -------------------------------------------------------

    @classmethod
    def open_or_clone(cls, spec: str, workdir: Path, *, depth: int, ref: str | None) -> GitRepo:
        """Use *spec* as a local repository, or clone it (shallow) into *workdir*."""
        local = Path(spec)
        if local.is_dir() and (local / ".git").exists():
            return cls(local)
        name = spec.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
        target = workdir / name
        if not (target / ".git").exists():
            workdir.mkdir(parents=True, exist_ok=True)
            args = ["git", "clone", "--quiet", "--no-tags", "--single-branch", f"--depth={depth}"]
            if ref:
                args += ["--branch", ref]
            subprocess.run([*args, spec, str(target)], check=True)
        return cls(target)

    # -- queries ------------------------------------------------------------

    def _git(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(self.path), *args],
            check=True,
            capture_output=True,
        ).stdout

    def resolve(self, ref: str) -> str:
        return self._git("rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()

    def first_parent_history(self, ref: str, count: int) -> list[str]:
        """The last *count* commits on *ref*'s first-parent line, oldest first."""
        out = self._git("rev-list", "--first-parent", f"--max-count={count}", ref)
        return list(reversed(out.decode().split()))

    def changes(self, old: str, new: str) -> list[Change]:
        raw = self._git("diff", "--raw", "-z", "-M", "--no-abbrev", old, new)
        fields = raw.decode("utf-8", "surrogateescape").split("\0")
        out: list[Change] = []
        i = 0
        while i < len(fields) and fields[i]:
            meta = fields[i].lstrip(":").split()
            old_mode, new_mode, old_sha, new_sha, status = meta[:5]
            kind = status[0]
            if kind in ("R", "C"):
                old_path, new_path = fields[i + 1], fields[i + 2]
                i += 3
            else:
                old_path = new_path = fields[i + 1]
                i += 2
            if old_mode in _SKIP_MODES or new_mode in _SKIP_MODES:
                continue
            out.append(
                Change(
                    status=kind,
                    old_path=None if kind == "A" else old_path,
                    new_path=None if kind == "D" else new_path,
                    old_sha=None if old_sha == _NULL_SHA else old_sha,
                    new_sha=None if new_sha == _NULL_SHA else new_sha,
                )
            )
        return out

    def blob(self, sha: str) -> bytes:
        """Contents of blob *sha*, through one long-running ``git cat-file --batch``."""
        if self._batch is None:
            self._batch = subprocess.Popen(
                ["git", "-C", str(self.path), "cat-file", "--batch"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        stdin: IO[bytes] = self._batch.stdin  # type: ignore[assignment]
        stdout: IO[bytes] = self._batch.stdout  # type: ignore[assignment]
        stdin.write(sha.encode() + b"\n")
        stdin.flush()
        header = stdout.readline().decode().split()
        if len(header) < 3 or header[1] != "blob":
            raise KeyError(f"blob {sha} not found")
        data = stdout.read(int(header[2]))
        stdout.read(1)  # trailing newline
        return data

    def close(self) -> None:
        if self._batch is not None:
            if self._batch.stdin:
                self._batch.stdin.close()
            self._batch.wait()
            if self._batch.stdout:
                self._batch.stdout.close()
            self._batch = None
