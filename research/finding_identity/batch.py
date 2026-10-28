"""Replay every repository of the corpus at its pinned commit, several at a time.

Each repository is fetched shallowly at its pinned SHA (no checkout) and replayed in its
own ``python -m research.finding_identity replay`` process, so one crash or timeout
affects only that repository. The batch is resumable: a repository whose
``summary.json`` already covers the pinned SHA and the requested number of commit pairs
is skipped. Every attempt is appended to ``<out>/batch.jsonl`` and each replay's output
goes to ``<out>/_logs/<label>.log``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .corpus import CorpusEntry, fetch_pinned, first_parent_count, has_commit

#: The directory ``python -m research.finding_identity`` must run from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class BatchOptions:
    commits: int
    out: Path
    workdir: Path
    categories: str = "security,performance,quality"
    details: bool = False
    timeout: float | None = None
    delete_clones: bool = False
    #: What produces the findings: ``codeguard``, ``bandit`` or ``semgrep``.
    analyzer: str = "codeguard"
    #: Semgrep's rules: a file or a rules repository (default: ``semgrep_rules.yml``).
    semgrep_rules: Path | None = None
    #: Record each repository's scanned versions under ``<observations>/<label>``.
    observations: Path | None = None


def summary_path(opts: BatchOptions, label: str) -> Path:
    return opts.out / label / "summary.json"


def recorded_analyzer(result_dir: Path) -> str | None:
    """The analyzer named in *result_dir*'s ``analyzer.json``; ``codeguard`` if it has none.

    Replays from before ``analyzer.json`` existed all used CodeGuard. ``None`` if the file
    cannot be read.
    """
    path = result_dir / "analyzer.json"
    if not path.exists():
        return "codeguard"
    try:
        name = json.loads(path.read_text(encoding="utf-8")).get("analyzer")
    except (OSError, ValueError, AttributeError):
        return None
    return name if isinstance(name, str) else None


def is_done(entry: CorpusEntry, opts: BatchOptions) -> bool:
    """True if a finished replay of *entry* at its pinned SHA, by ``opts.analyzer``,
    covers ``opts.commits``."""
    path = summary_path(opts, entry.label)
    if not path.exists():
        return False
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool(
        summary.get("head") == entry.sha
        and summary.get("commit_pairs", 0) >= opts.commits
        and recorded_analyzer(path.parent) == opts.analyzer
    )


def prepare(entry: CorpusEntry, opts: BatchOptions) -> Path:
    """A local repository holding the pinned commit and enough first-parent history."""
    target = opts.workdir / entry.label
    if not has_commit(target, entry.sha) or first_parent_count(target, entry.sha) <= opts.commits:
        fetch_pinned(entry.url, entry.sha, target, depth=opts.commits + 2)
    return target


def run_one(entry: CorpusEntry, opts: BatchOptions) -> None:
    """Fetch and replay one repository; raise if the replay does not finish."""
    log_path = opts.out / "_logs" / f"{entry.label}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    target = prepare(entry, opts)
    cmd = [
        sys.executable,
        "-m",
        "research.finding_identity",
        "replay",
        str(target.resolve()),
        "--ref",
        entry.sha,
        "--commits",
        str(opts.commits),
        "--label",
        entry.label,
        "--out",
        str((opts.out / entry.label).resolve()),
        "--categories",
        opts.categories,
    ]
    if opts.details:
        cmd.append("--details")
    if opts.analyzer != "codeguard":
        cmd += ["--analyzer", opts.analyzer]
    if opts.semgrep_rules is not None:
        cmd += ["--semgrep-rules", str(opts.semgrep_rules.resolve())]
    if opts.observations is not None:
        cmd += ["--observations", str((opts.observations / entry.label).resolve())]
    with log_path.open("w", encoding="utf-8") as log:
        log.write(" ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=opts.timeout,
            check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"replay exited with status {proc.returncode}, see {log_path}")
    if not is_done(entry, opts):
        raise RuntimeError(f"replay finished without a complete summary.json, see {log_path}")
    if opts.delete_clones:
        shutil.rmtree(target, ignore_errors=True)


Runner = Callable[[CorpusEntry, BatchOptions], None]


def _attempt(entry: CorpusEntry, opts: BatchOptions, runner: Runner) -> dict[str, Any]:
    started = time.monotonic()
    status: dict[str, Any] = {"label": entry.label, "sha": entry.sha, "status": "ok"}
    try:
        runner(entry, opts)
    except subprocess.TimeoutExpired:
        status.update(status="failed", error=f"timed out after {opts.timeout}s")
    except Exception as exc:  # one repository must not stop the batch
        status.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        log_path = opts.out / "_logs" / f"{entry.label}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(traceback.format_exc())
    status["seconds"] = round(time.monotonic() - started, 1)
    status["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return status


def run_batch(
    entries: Sequence[CorpusEntry],
    opts: BatchOptions,
    *,
    jobs: int = 1,
    force: bool = False,
    runner: Runner = run_one,
) -> list[dict[str, Any]]:
    """Replay every entry not already done; return one status record per entry."""
    opts.out.mkdir(parents=True, exist_ok=True)
    statuses: list[dict[str, Any]] = []
    pending: list[CorpusEntry] = []
    for entry in entries:
        if not force and is_done(entry, opts):
            statuses.append({"label": entry.label, "sha": entry.sha, "status": "skipped"})
        else:
            pending.append(entry)
    print(
        f"{len(entries)} repositories: {len(statuses)} already done, {len(pending)} to run "
        f"with {jobs} job(s)",
        file=sys.stderr,
    )
    started = time.monotonic()
    with (
        ThreadPoolExecutor(max_workers=max(jobs, 1)) as pool,
        (opts.out / "batch.jsonl").open("a", encoding="utf-8") as journal,
    ):
        futures = {pool.submit(_attempt, e, opts, runner): e for e in pending}
        for done, future in enumerate(as_completed(futures), start=1):
            status = future.result()
            statuses.append(status)
            journal.write(json.dumps(status) + "\n")
            journal.flush()
            note = f" ({status['error']})" if status["status"] == "failed" else ""
            print(
                f"[{done}/{len(pending)}] {status['label']}: {status['status']} "
                f"in {status['seconds']:.0f}s{note}",
                file=sys.stderr,
            )
    failed = [s["label"] for s in statuses if s["status"] == "failed"]
    print(
        f"batch finished in {time.monotonic() - started:.0f}s; "
        f"{len(failed)} failed{': ' + ', '.join(failed) if failed else ''}",
        file=sys.stderr,
    )
    order = {e.label: i for i, e in enumerate(entries)}
    return sorted(statuses, key=lambda s: order[s["label"]])
