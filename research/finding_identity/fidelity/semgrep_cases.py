"""Check the ``match_based_id`` port against the IDs Semgrep itself emits.

Scans whole directories with ``semgrep_rules.yml`` in one Semgrep run (offline, see
:func:`analyzers.semgrep_env`), recomputes every result's ID with
:func:`schemes.semgrep_match_based_ids`, and compares. ``--write`` records what the port
reads from each result (rule, path, metavariable bindings, order) and the emitted ID as
``tests/fixtures/semgrep_match_based_id.json``, so the test runs without Semgrep.

    python -m research.finding_identity.fidelity.semgrep_cases DIR [DIR ...] [--write]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from ..analyzers import (
    DEFAULT_SEMGREP_RULES,
    SEMGREP_SCAN_ARGS,
    semgrep_env,
    semgrep_formulas,
    semgrep_matches,
)
from ..schemes import semgrep_match_based_ids

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "semgrep_match_based_id.json"


def scan(directory: Path, rules_text: str) -> list[dict[str, Any]]:
    """Semgrep's JSON results for *directory*, with paths relative to it."""
    exe = shutil.which("semgrep")
    if exe is None:
        raise SystemExit("semgrep is not installed")
    with tempfile.TemporaryDirectory() as home:
        # Rule IDs carry no directory prefix when the rules file sits in the working dir.
        (directory / ".finding-identity-rules.yml").write_text(rules_text, encoding="utf-8")
        ignore = directory / ".semgrepignore"
        created_ignore = not ignore.exists()
        if created_ignore:
            ignore.write_text("", encoding="utf-8")
        try:
            proc = subprocess.run(
                [exe, *SEMGREP_SCAN_ARGS, "--config", ".finding-identity-rules.yml", "."],
                cwd=directory,
                env=semgrep_env(Path(home)),
                capture_output=True,
                text=True,
                check=True,
            )
        finally:
            (directory / ".finding-identity-rules.yml").unlink()
            if created_ignore:
                ignore.unlink()
    results: list[dict[str, Any]] = json.loads(proc.stdout)["results"]
    return results


def by_path(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        out.setdefault(r["path"], []).append(r)
    return out


def compare(results: list[dict[str, Any]], formulas: dict[str, str]) -> int:
    mismatches = 0
    for path, rs in by_path(results).items():
        ported = semgrep_match_based_ids(semgrep_matches(rs, formulas))
        for r, port_id in zip(rs, ported, strict=True):
            if port_id != r["extra"]["fingerprint"]:
                mismatches += 1
                print(f"mismatch {path}:{r['start']['line']} {r['check_id']}", file=sys.stderr)
    return mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dirs", nargs="+", type=Path)
    parser.add_argument("--rules", type=Path, default=DEFAULT_SEMGREP_RULES)
    parser.add_argument("--write", action="store_true", help=f"write {FIXTURE.name}")
    args = parser.parse_args(argv)

    rules_text = args.rules.read_text(encoding="utf-8")
    formulas = semgrep_formulas(rules_text)
    version = subprocess.run(
        ["semgrep", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    sources = []
    total = mismatches = 0
    for d in args.dirs:
        results = scan(d.resolve(), rules_text)
        bad = compare(results, formulas)
        reused = sum(1 for r in results if not r["extra"]["fingerprint"].endswith("_0"))
        print(f"{d}: {len(results)} results, {reused} with index > 0, {bad} mismatches")
        total += len(results)
        mismatches += bad
        commit = subprocess.run(
            ["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "-C", str(d), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        sources.append(
            {
                "source": remote or d.name,
                "commit": commit,
                "files": [
                    [
                        {
                            "rule": r["check_id"],
                            "path": r["path"],
                            "metavars": {
                                k: v["abstract_content"]
                                for k, v in r["extra"].get("metavars", {}).items()
                            },
                            "id": r["extra"]["fingerprint"],
                        }
                        for r in rs
                    ]
                    for rs in by_path(results).values()
                ],
            }
        )
    print(f"total: {total} results, {mismatches} mismatches")
    if args.write and not mismatches:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(
            json.dumps(
                {
                    "semgrep": version,
                    "rules": rules_text,
                    "rules_sha256": hashlib.sha256(rules_text.encode()).hexdigest(),
                    "sources": sources,
                },
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
