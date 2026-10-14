"""The study corpus: load ``corpus.csv``, pin commits, and check the selection criteria.

Every criterion that git can answer is measured at the pinned commit, so a check gives
the same answer whenever it is run:

- at least ``MIN_COMMITS`` first-parent commits in the ``WINDOW_DAYS`` before the pinned
  commit (enough history for the replay, and evidence of sustained activity);
- the pinned commit is at most ``MAX_AGE_DAYS`` older than the pinning date (the
  project is alive);
- the root licence file is an OSI-approved licence;
- the root licence file is not split into separately licensed parts;
- the declared backend language (Python, or JavaScript/TypeScript) has at least
  ``MIN_SOURCE_FILES`` analysable files and more than the other language.

"Application, not a library", "not a fork" and "not a tutorial" are judged by hand and
recorded in the ``rationale`` column.
"""

from __future__ import annotations

import csv
import re
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .scan import is_candidate

MIN_COMMITS = 200
WINDOW_DAYS = 730
MAX_AGE_DAYS = 90
MIN_SOURCE_FILES = 100

#: SPDX identifiers of the OSI-approved licences the corpus uses.
OSI_LICENSES = frozenset(
    {
        "AGPL-3.0",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "GPL-2.0",
        "GPL-3.0",
        "LGPL-3.0",
        "MIT",
        "MPL-2.0",
        "PostgreSQL",
    }
)

PY_SUFFIXES = (".py",)
JS_SUFFIXES = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")


@dataclass
class CorpusEntry:
    """One row of ``corpus.csv``. The last four columns are measured by ``check``."""

    label: str
    url: str
    branch: str
    sha: str
    pinned: str  # date the SHA was pinned, YYYY-MM-DD
    language: str  # "python" or "javascript" (JavaScript or TypeScript)
    framework: str
    license: str  # SPDX identifier
    rationale: str
    commit_date: str = ""
    commits_2y: str = ""
    py_files: str = ""
    js_files: str = ""


COLUMNS = [f.name for f in fields(CorpusEntry)]


def load_corpus(path: Path) -> list[CorpusEntry]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    entries = [CorpusEntry(**{k: (row.get(k) or "").strip() for k in COLUMNS}) for row in rows]
    labels = [e.label for e in entries]
    dupes = sorted({x for x in labels if labels.count(x) > 1})
    if dupes:
        raise ValueError(f"duplicate labels in {path}: {', '.join(dupes)}")
    return entries


def save_corpus(path: Path, entries: Iterable[CorpusEntry]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(e) for e in entries)


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path | None = None) -> str:
    cmd = ["git", *args] if cwd is None else ["git", "-C", str(cwd), *args]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def default_branch_head(url: str) -> tuple[str, str]:
    """``(branch, sha)`` of the remote's default branch."""
    out = _git("ls-remote", "--symref", url, "HEAD")
    branch = sha = ""
    for line in out.splitlines():
        if line.startswith("ref: "):
            branch = line.split()[1].removeprefix("refs/heads/")
        elif line.endswith("\tHEAD"):
            sha = line.split()[0]
    if not branch or not sha:
        raise RuntimeError(f"cannot resolve the default branch of {url}")
    return branch, sha


def has_commit(target: Path, sha: str) -> bool:
    if not (target / ".git").exists():
        return False
    try:
        _git("cat-file", "-e", f"{sha}^{{commit}}", cwd=target)
    except subprocess.CalledProcessError:
        return False
    return True


def first_parent_count(target: Path, sha: str, since: str | None = None) -> int:
    args = ["rev-list", "--first-parent", "--count", sha]
    if since:
        args.insert(3, f"--since={since}")
    return int(_git(*args, cwd=target).strip())


def fetch_pinned(url: str, sha: str, target: Path, *, depth: int) -> None:
    """Fetch *sha* and *depth* commits of its history into *target*, without a checkout."""
    if not (target / ".git").exists():
        target.mkdir(parents=True, exist_ok=True)
        _git("init", "--quiet", cwd=target)
        _git("remote", "add", "origin", url, cwd=target)
    _git("fetch", "--quiet", "--no-tags", f"--depth={depth}", "origin", sha, cwd=target)


def commit_datetime(target: Path, sha: str) -> datetime:
    stamp = _git("show", "-s", "--format=%cI", sha, cwd=target).strip()
    return datetime.fromisoformat(stamp)


# ---------------------------------------------------------------------------
# licence and language
# ---------------------------------------------------------------------------

_LICENSE_FILE = re.compile(r"^(licen[cs]e|copying)(\.(md|txt|rst))?$", re.IGNORECASE)
_NON_OSI_MARKERS = (
    "business source license",
    "sustainable use license",
    "functional source license",
    "elastic license",
    "commons clause",
)


_GNU = {
    "gnu affero general public license": "AGPL",
    "gnu lesser general public license": "LGPL",
    "gnu library general public license": "LGPL",
    "gnu general public license": "GPL",
}
_GNU_VERSION = re.compile(r"(?:version|v\.?)\s*(\d)")
#: Root licences that put some directories under other (usually source-available) terms.
_CARVE_OUT = re.compile(
    r"portions of (?:this|the \w+) software|enterprise edition|certain files are licen"
)


def _gnu_license(t: str) -> str | None:
    # The GNU licences mention each other (GPLv3 section 13 names the AGPL), so the one
    # named first is the licence, and the version is the one stated right after it.
    found = [(t.find(name), family) for name, family in _GNU.items() if name in t]
    if not found:
        return None
    pos, family = min(found)
    version = _GNU_VERSION.search(t, pos, pos + 250)
    number = version.group(1) if version else "2"
    if family == "LGPL":
        return "LGPL-3.0" if number == "3" else "LGPL-2.1"
    return f"{family}-{number}.0"


def classify_license(text: str) -> str:
    """A best-effort SPDX identifier for a licence text ("unknown" if unrecognised).

    A licence that carves out separately licensed parts reads as ``mixed (...)``.
    """
    t = " ".join(text.lower().split())
    for marker in _NON_OSI_MARKERS:
        if marker in t:
            return f"non-osi ({marker})"
    spdx = _gnu_license(t) or _permissive_license(t)
    return f"mixed ({spdx})" if _CARVE_OUT.search(t) else spdx


def _permissive_license(t: str) -> str:
    if "mozilla public license" in t and "2.0" in t:
        return "MPL-2.0"
    if "apache license" in t and "version 2.0" in t:
        return "Apache-2.0"
    if "postgresql" in t and "without a written agreement" in t:
        return "PostgreSQL"
    if "redistribution and use in source and binary forms" in t:
        return "BSD-3-Clause" if "neither the name" in t else "BSD-2-Clause"
    if "permission is hereby granted, free of charge" in t:
        return "MIT"
    return "unknown"


def detect_license(target: Path, sha: str) -> str:
    names = _git("ls-tree", "--name-only", sha, cwd=target).splitlines()
    found = sorted(n for n in names if _LICENSE_FILE.match(n))
    if not found:
        return "missing"
    return classify_license(_git("show", f"{sha}:{found[0]}", cwd=target))


def count_source_files(paths: Sequence[str]) -> tuple[int, int]:
    """``(python files, JavaScript/TypeScript files)`` the harness would analyse."""
    py = js = 0
    for p in paths:
        if not is_candidate(p):
            continue
        if p.endswith(PY_SUFFIXES):
            py += 1
        elif p.endswith(JS_SUFFIXES):
            js += 1
    return py, js


# ---------------------------------------------------------------------------
# pin and check
# ---------------------------------------------------------------------------


def branch_head(url: str, branch: str) -> str:
    out = _git("ls-remote", url, f"refs/heads/{branch}")
    if not out.strip():
        raise RuntimeError(f"{url} has no branch {branch!r}")
    return out.split()[0]


def pin(entry: CorpusEntry, today: date) -> None:
    """Pin *entry* to the current head of its branch (the default branch if unset)."""
    if entry.branch:
        entry.sha = branch_head(entry.url, entry.branch)
    else:
        entry.branch, entry.sha = default_branch_head(entry.url)
    entry.pinned = today.isoformat()


def count_history(entry: CorpusEntry, workdir: Path, since: datetime) -> int:
    """First-parent commits from *since* to the pinned commit, from a commits-only clone."""
    target = workdir / "_history" / entry.label
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        _git(
            "clone",
            "--quiet",
            "--bare",
            "--no-tags",
            "--filter=tree:0",
            "--single-branch",
            f"--branch={entry.branch}",
            f"--shallow-since={(since - timedelta(days=1)).date().isoformat()}",
            entry.url,
            str(target),
        )
    return first_parent_count(target, entry.sha, since=since.isoformat())


def measure(entry: CorpusEntry, workdir: Path) -> list[str]:
    """Fill the measured columns of *entry*; return the criteria it fails."""
    target = workdir / entry.label
    if not has_commit(target, entry.sha):
        fetch_pinned(entry.url, entry.sha, target, depth=1)
    committed = commit_datetime(target, entry.sha)
    commits = count_history(entry, workdir, committed - timedelta(days=WINDOW_DAYS))
    paths = _git("ls-tree", "-r", "--name-only", entry.sha, cwd=target).splitlines()
    py, js = count_source_files(paths)
    detected = detect_license(target, entry.sha)

    entry.commit_date = committed.astimezone(timezone.utc).date().isoformat()
    entry.commits_2y = str(commits)
    entry.py_files, entry.js_files = str(py), str(js)

    problems: list[str] = []
    if commits < MIN_COMMITS:
        problems.append(f"only {commits} first-parent commits in {WINDOW_DAYS} days")
    age = date.fromisoformat(entry.pinned) - committed.date()
    if age.days > MAX_AGE_DAYS:
        problems.append(f"pinned commit is {age.days} days old")
    if entry.license not in OSI_LICENSES:
        problems.append(f"declared licence {entry.license!r} is not in the OSI list")
    if detected != entry.license:
        problems.append(f"licence file reads as {detected}, declared {entry.license}")
    own, other = (py, js) if entry.language == "python" else (js, py)
    if own < MIN_SOURCE_FILES:
        problems.append(f"only {own} {entry.language} source files")
    if own <= other:
        problems.append(f"{entry.language} is not the majority language ({py} py, {js} js)")
    return problems
