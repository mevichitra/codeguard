# SPDX-License-Identifier: Apache-2.0
"""How much a similarity fallback would recover, and what it would risk.

``python -m research.finding_identity.analysis.similarity_sweep RESULTS --repos .repos
--out DIR`` takes, from a replay, (a) every persisting finding on a file that kept its
path which the ``codeguard`` scheme reported as new, and (b) a seeded sample of
introduced findings. For each it computes the best similarity between the finding's
normalized statement and any old line in the same enclosing scope (any line, not only
flagged ones, so the risk side is an upper bound), under two measures that are not the
ground truth's: the Jaccard index of the token sets and difflib's ratio over token
sequences. The report lists, per threshold, the share of (a) a fallback at that threshold
would recover and the share of (b) it could wrongly match.
"""

from __future__ import annotations

import argparse
import difflib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from codeguard.engine import fingerprint as cg_fp

from ..schemes import FileContext
from .cg_failures import Repo, load_pairs, tokens

THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9)


def token_sets(line: str) -> tuple[set[str], list[str]]:
    toks = [t for k, t in tokens(cg_fp._STRING_RE.sub("STR", line)) if k != "comment"]
    toks = [cg_fp._NUMBER_RE.sub("NUM", t) for t in toks]
    return set(toks), toks


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def seq_ratio(a: list[str], b: list[str]) -> float:
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def best_match(new: FileContext, line: int, old: FileContext) -> dict[str, float]:
    """Best Jaccard and sequence ratio of the new line against old lines in its scope."""
    scope = new.scope(line)
    n_set, n_seq = token_sets(new.raw_line(line))
    best = {"jaccard": 0.0, "seq": 0.0}
    if len(n_seq) < 3:
        return best
    for i, raw in enumerate(old.lines, start=1):
        if not raw.strip() or old.scope(i) != scope:
            continue
        o_set, o_seq = token_sets(raw)
        if len(o_seq) < 3:
            continue
        j = jaccard(n_set, o_set)
        if j > best["jaccard"]:
            best["jaccard"] = j
        if j >= 0.3:  # the sequence ratio cannot be high when the sets barely overlap
            s = seq_ratio(n_seq, o_seq)
            if s > best["seq"]:
                best["seq"] = s
    return best


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--repos", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--scheme", default="codeguard")
    ap.add_argument("--sample", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    rng = random.Random(args.seed)  # noqa: S311

    recover: list[dict[str, Any]] = []
    risk: list[dict[str, Any]] = []
    for repo_dir in sorted(p for p in args.results.iterdir() if (p / "findings.jsonl").exists()):
        label = repo_dir.name
        if not (args.repos / label).is_dir():
            continue
        pairs = load_pairs(repo_dir)
        wanted: list[dict[str, Any]] = []
        introduced: list[dict[str, Any]] = []
        with (repo_dir / "findings.jsonl").open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec["status"] != "M":
                    continue
                if rec["truth"] == "known" and rec["outcomes"].get(args.scheme) == "false_new":
                    wanted.append(rec)
                elif rec["truth"] == "new":
                    introduced.append(rec)
        sample = rng.sample(introduced, min(len(introduced), max(1, args.sample // 35)))
        repo = Repo(args.repos / label)
        by_version: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = defaultdict(list)
        for r in wanted:
            by_version[(r["commit"], r["path"])].append(("recover", r))
        for r in sample:
            by_version[(r["commit"], r["path"])].append(("risk", r))
        for (commit, path), items in by_version.items():
            new = repo.context(commit, path)
            old = repo.context(pairs[commit], path) if commit in pairs else None
            if new is None or old is None:
                continue
            for kind, r in items:
                row = {"repo": label, "rule": r["rule"], **best_match(new, r["line"], old)}
                (recover if kind == "recover" else risk).append(row)
        repo.git.close()
        print(f"{label}: {len(wanted)} to recover, {len(sample)} at risk")

    args.out.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Similarity fallback: recovery against risk",
        "",
        f"Recover: {len(recover)} persisting findings `{args.scheme}` reported as new on files "
        "that kept their path. Risk: a seeded sample of "
        f"{len(risk)} introduced findings. Each is compared with every non-blank old line in "
        "the same scope; the table gives the share whose best match reaches the threshold.",
        "",
        "| measure | threshold | recovered | wrongly matchable (upper bound) |",
        "|---|---:|---:|---:|",
    ]
    for measure in ("jaccard", "seq"):
        for t in THRESHOLDS:
            rec = sum(1 for r in recover if r[measure] >= t)
            rsk = sum(1 for r in risk if r[measure] >= t)
            rec_pct = 100 * rec / max(1, len(recover))
            rsk_pct = 100 * rsk / max(1, len(risk))
            lines.append(
                f"| {measure} | {t} | {rec}/{len(recover)} ({rec_pct:.0f}%) "
                f"| {rsk}/{len(risk)} ({rsk_pct:.0f}%) |"
            )
    (args.out / "similarity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (args.out / "similarity.jsonl").open("w", encoding="utf-8") as f:
        for kind, rows in (("recover", recover), ("risk", risk)):
            for r in rows:
                f.write(json.dumps({"kind": kind, **r}) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
