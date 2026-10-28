# SPDX-License-Identifier: Apache-2.0
"""Classify a sample of the ``codeguard`` scheme's false-new findings at a long span.

``python -m research.finding_identity.analysis.drift_failures RESULTS --repos .repos/deep
--span 200 --sample 40`` reads the drift replays (``<label>/a<anchor>/findings.jsonl``),
takes the persisting findings on edited lines of files that kept their path which the
scheme reported as new, samples some, and classifies them with
:func:`cg_failures.classify_false_new` after fetching the anchor's and the compared
commit's file versions.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from .cg_failures import Repo, classify_false_new


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--repos", type=Path, required=True)
    ap.add_argument("--span", type=int, default=200)
    ap.add_argument("--sample", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--scheme", default="codeguard")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    candidates: list[tuple[str, str, dict[str, Any]]] = []
    for summary_path in sorted(args.results.glob("*/a*/summary.json")):
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        with (summary_path.parent / "findings.jsonl").open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec["span"] != args.span:
                    continue
                if rec["truth"] == "new":
                    continue
                if (
                    rec["outcomes"].get(args.scheme) == "false_new"
                    and rec.get("truth_kind") == "edited"
                    and rec.get("old_path") == rec["path"]
                ):
                    candidates.append((summary["label"], summary["anchor"], rec))
    rng = random.Random(args.seed)  # noqa: S311
    sample = rng.sample(candidates, min(args.sample, len(candidates)))
    cases = []
    repos: dict[str, Repo] = {}
    heads: dict[tuple[str, str], str] = {}
    for label, anchor, rec in sample:
        repo = repos.setdefault(label, Repo(args.repos / label))
        key = (label, anchor)
        if key not in heads:
            # The compared commit is `span` first-parent steps after the anchor.
            back = _back(args, label, anchor)
            summary = json.loads(
                (args.results / label / f"a{back}" / "summary.json").read_text(encoding="utf-8")
            )
            heads[key] = next(s["commit"] for s in summary["spans"] if s["span"] == args.span)
        new_commit = heads[key]
        old = repo.context(anchor, rec["old_path"])
        new = repo.context(new_commit, rec["path"])
        base = {"repo": label, "rule": rec["rule"], "path": rec["path"], "line": rec["line"]}
        if old is None or new is None:
            base["cause"] = "no_version"
        else:
            base.update(classify_false_new({**rec, "status": "M"}, old, new, args.scheme))
        cases.append(base)
    for repo in repos.values():
        repo.git.close()
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "drift_cases.jsonl").open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    lines = [
        f"# `{args.scheme}` false-new on edited lines at span {args.span}",
        "",
        f"{len(candidates)} candidates, {len(cases)} sampled (seed {args.seed}).",
        "",
        "| cause | n |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in Counter(c.get("cause") for c in cases).most_common()],
        "",
        "| def line | n |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in Counter(c.get("def_line") for c in cases).most_common()],
        "",
    ]
    (args.out / "drift_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _back(args: argparse.Namespace, label: str, anchor: str) -> int:
    for p in (args.results / label).glob("a*/summary.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        if s["anchor"] == anchor:
            return int(s["anchor_back"])
    raise KeyError(anchor)


if __name__ == "__main__":
    main()
