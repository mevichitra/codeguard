# SPDX-License-Identifier: Apache-2.0

"""A stratified sample of ground-truth decisions, for a manual check.

``python -m research.finding_identity.gt_sample <results> --corpus corpus.csv --out <dir>``
draws findings from the replays' ``findings.jsonl`` (``--details``) in five strata, where
the ground truth is most and least likely to be wrong:

- ``edited``: persisting findings whose line was edited (every scheme struggles here);
- ``known_but_new``: persisting findings on an unchanged line, in a file that kept its
  path, that SonarQube or CodeGuard report as new (is the truth's pairing right?);
- ``new_but_matched``: introduced findings that a content scheme matched to an old one
  (is the finding really new?);
- ``agree_known`` and ``agree_new``: every content scheme agrees with the truth (control).

It writes ``sample.md``, one entry per finding with the code before and after the commit
and a link to the commit, and ``sample.csv`` with an empty ``verdict`` column to fill in:
``same`` (the old and new finding are the same issue), ``different``, or ``unclear``.

For independent raters it also writes ``items.json``: the same findings, shuffled under
neutral ids (``sample.csv``'s ``item`` column is the key), without the harness's answer,
the stratum or the schemes' outcomes. A persisting finding becomes a ``pair`` item ("is
the code flagged at the old line the same issue as at the new line?"), an introduced one
an ``introduced`` item ("did this issue already exist before the commit?").
The sample is seeded, so rerunning it gives the same findings and the same order.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import codeguard.rules  # noqa: F401  (registers the built-in rules)
from codeguard.engine.registry import REGISTRY

from .corpus import load_corpus
from .linemap import map_lines
from .schemes import split_lines

HERE = Path(__file__).parent

#: Schemes whose agreement defines the strata.
CONTENT_SCHEMES = ("line_text", "github", "codeguard", "sonar")

Record = dict[str, Any]


def _known(r: Record) -> bool:
    return bool(r["truth"] == "known")


STRATA: dict[str, Callable[[Record], bool]] = {
    "edited": lambda r: _known(r) and r.get("truth_kind") == "edited",
    "known_but_new": lambda r: (
        _known(r)
        and r.get("truth_kind") == "equal"
        and not str(r.get("status", "")).startswith("R")
        and any(r["outcomes"][s] == "false_new" for s in ("sonar", "codeguard"))
    ),
    "new_but_matched": lambda r: (
        not _known(r) and any(r["outcomes"][s] == "false_known" for s in CONTENT_SCHEMES)
    ),
    "agree_known": lambda r: (
        _known(r) and all(r["outcomes"][s] == "known_ok" for s in CONTENT_SCHEMES)
    ),
    "agree_new": lambda r: (
        not _known(r) and all(r["outcomes"][s] == "new_ok" for s in CONTENT_SCHEMES)
    ),
}


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    return done.stdout.decode("utf-8", "replace") if done.returncode == 0 else ""


def snippet_lines(
    repo: Path, commit: str, path: str, line: int, context: int = 4
) -> list[tuple[int, str]]:
    """``(line number, text)`` for the lines around *line* of *path* at *commit*."""
    lines = _git(repo, "show", f"{commit}:{path}").split("\n")
    lo, hi = max(1, line - context), min(len(lines), line + context)
    return [(n, lines[n - 1].rstrip()) for n in range(lo, hi + 1)]


def snippet(repo: Path, commit: str, path: str, line: int, context: int = 4) -> str:
    """Lines around *line* of *path* at *commit*, numbered, the line itself marked."""
    return "\n".join(
        f"{'>' if n == line else ' '}{n:5d}  {text}"
        for n, text in snippet_lines(repo, commit, path, line, context)
    )


def corresponding_old_line(
    old_lines: list[str], new_lines: list[str], line: int
) -> tuple[int, bool]:
    """The old line at the place of new line *line*, and whether *line* itself maps to it.

    Uses the ground truth's line map: if *line* maps back to an old line (unchanged or
    edited), that line; otherwise the line after the nearest old line that maps to a new
    line above *line* (the point where the new code was inserted).
    """
    back = {new: old for old, (new, _) in map_lines(old_lines, new_lines).items()}
    if line in back:
        return back[line], True
    above = [n for n in back if n < line]
    if not above:
        return 1, False
    anchor = max(above)
    return min(back[anchor] + 1, max(len(old_lines), 1)), False


def diff_hunks(repo: Path, old: str, new: str, path: str, old_path: str, line: int) -> str:
    """The hunks of the commit's diff of this file that come within 6 lines of *line*."""
    paths = [path] if path == old_path else [old_path, path]
    text = _git(repo, "diff", "-M", "--unified=3", old, new, "--", *paths)
    hunks: list[list[str]] = []
    current: list[str] = []
    for row in text.split("\n"):
        if row.startswith("@@"):
            if current:
                hunks.append(current)
            current = [row]
        elif current:
            current.append(row)
    if current:
        hunks.append(current)
    near = []
    for hunk in hunks:
        # @@ -a,b +c,d @@: the new side starts at c and spans d lines.
        new_side = hunk[0].split("+")[1].split(" ")[0].split(",")
        start = int(new_side[0])
        length = int(new_side[1]) if len(new_side) > 1 else 1
        if start - 6 <= line <= start + length + 6:
            near.append(_clip(hunk))
    return "\n".join(near[:MAX_HUNKS]) or "(no diff hunk near this line)"


#: A diff shows at most this many hunks, each clipped to this many lines.
MAX_HUNKS = 2
MAX_HUNK_LINES = 40


def _clip(hunk: list[str]) -> str:
    if len(hunk) <= MAX_HUNK_LINES:
        return "\n".join(hunk)
    return "\n".join([*hunk[:MAX_HUNK_LINES], f"... ({len(hunk) - MAX_HUNK_LINES} more lines)"])


def load_records(results: Path, labels: list[str]) -> list[tuple[str, Record, str]]:
    """``(label, record, old commit)`` for every finding of every replay."""
    out = []
    for label in labels:
        d = results / label
        if not (d / "findings.jsonl").exists():
            continue
        parent = {}
        with (d / "pairs.jsonl").open(encoding="utf-8") as f:
            for line in f:
                pair = json.loads(line)
                parent[pair["new"]] = pair["old"]
        with (d / "findings.jsonl").open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                out.append((label, rec, parent[rec["commit"]]))
    return out


def draw(
    records: list[tuple[str, Record, str]], per_stratum: int, seed: int
) -> list[tuple[str, str, Record, str]]:
    """``(stratum, label, record, old commit)``, *per_stratum* from each stratum."""
    rng = random.Random(seed)  # noqa: S311  (reproducible sampling, not security)
    chosen = []
    for name, test in STRATA.items():
        pool = [(label, rec, old) for label, rec, old in records if test(rec)]
        for label, rec, old in rng.sample(pool, min(per_stratum, len(pool))):
            chosen.append((name, label, rec, old))
    return chosen


def write_sample(
    chosen: list[tuple[str, str, Record, str]],
    repos: Path,
    urls: dict[str, str],
    out: Path,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    md = [
        "# Ground-truth check",
        "",
        "For each finding, decide whether the old and the new finding are the **same**",
        "issue (for an introduced finding: whether it is **new** in this commit), and write",
        "`same`, `different` or `unclear` in the `verdict` column of `sample.csv`.",
        "The harness's answer is given under *Truth*; judge the code, not the answer.",
        "",
    ]
    rows = []
    items = []
    titles = {r.id: r.title for r in REGISTRY.all()}
    # Neutral item ids in a seeded order unrelated to the strata.
    order = list(range(1, len(chosen) + 1))
    random.Random(len(chosen)).shuffle(order)  # noqa: S311  (blinding order, not security)
    item_of = {i: f"F{position:03d}" for position, i in enumerate(order, start=1)}
    for i, (stratum, label, rec, old) in enumerate(chosen, start=1):
        repo = repos / label
        new = rec["commit"]
        path, old_path = rec["path"], rec.get("old_path") or rec["path"]
        truth = rec["truth"] if rec["truth"] == "new" else f"known ({rec['truth_kind']})"
        disagree = sorted(
            s for s in CONTENT_SCHEMES if rec["outcomes"][s] not in ("known_ok", "new_ok")
        )
        url = f"{urls[label].removesuffix('.git')}/commit/{new}"
        md += [
            f"## {i}. {label}: `{rec['rule']}` ({stratum})",
            "",
            f"- Commit: [{new[:10]}]({url}), file `{path}`"
            + (f" (was `{old_path}`)" if old_path != path else ""),
            f"- Truth: **{truth}**"
            + (f", old line {rec['old_line']}" if rec.get("old_line") else "")
            + f", new line {rec['line']}",
            "- Schemes that disagree with the truth: "
            + (", ".join(f"`{s}` ({rec['outcomes'][s]})" for s in disagree) or "none"),
            "",
        ]
        if rec.get("old_line"):
            md += ["Before:", "", "```", snippet(repo, old, old_path, rec["old_line"]), "```"]
        md += ["After:", "", "```", snippet(repo, new, path, rec["line"]), "```", ""]
        if rec["truth"] == "new" or rec.get("truth_kind") == "edited":
            hunks = diff_hunks(repo, old, new, path, old_path, rec["line"])
            md += ["Diff near the line:", "", "```diff", hunks, "```", ""]
        old_line = rec.get("old_line")
        if old_line:
            before_line, before_mapped = old_line, True
        else:
            # An introduced finding: show the old code at the same place, so a rater can
            # see whether the issue was already there.
            old_text = split_lines(_git(repo, "show", f"{old}:{old_path}"))
            new_text = split_lines(_git(repo, "show", f"{new}:{path}"))
            before_line, before_mapped = corresponding_old_line(old_text, new_text, rec["line"])
        items.append(
            {
                "item": item_of[i],
                "kind": "pair" if rec["truth"] == "known" else "introduced",
                "repository": label,
                "commit_url": url,
                "rule": rec["rule"],
                "rule_title": titles.get(rec["rule"], ""),
                "path": path,
                "old_path": old_path,
                "old_line": old_line,
                "line": rec["line"],
                "before": snippet_lines(
                    repo, old, old_path, before_line, context=4 if old_line else 6
                ),
                "before_line": before_line,
                # True when the flagged line itself was already there before the commit.
                "before_mapped": before_mapped,
                "after": snippet_lines(repo, new, path, rec["line"]),
                "diff": "\n".join(
                    row.rstrip()
                    for row in diff_hunks(repo, old, new, path, old_path, rec["line"]).split("\n")
                ),
            }
        )
        rows.append(
            {
                "id": i,
                "item": item_of[i],
                "stratum": stratum,
                "repository": label,
                "commit": new,
                "path": path,
                "rule": rec["rule"],
                "truth": truth,
                "old_line": rec.get("old_line") or "",
                "line": rec["line"],
                "disagreeing_schemes": " ".join(disagree),
                "verdict": "",
                "note": "",
            }
        )
    # Quoted source can end lines in spaces; the repository's hooks strip them.
    text = "\n".join(row.rstrip() for row in "\n".join(md).split("\n"))
    (out / "sample.md").write_text(text.rstrip("\n") + "\n", encoding="utf-8")
    items.sort(key=lambda it: str(it["item"]))
    (out / "items.json").write_text(json.dumps(items, indent=1) + "\n", encoding="utf-8")
    with (out / "sample.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m research.finding_identity.gt_sample")
    ap.add_argument("results", type=Path, help="batch results with findings.jsonl")
    ap.add_argument("--corpus", type=Path, default=HERE / "corpus.csv")
    ap.add_argument("--repos", type=Path, default=HERE / ".repos", help="the batch's clones")
    ap.add_argument("--out", type=Path, default=HERE / "paper" / "ground_truth_check")
    ap.add_argument("--per-stratum", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261017)
    args = ap.parse_args(argv)
    corpus = load_corpus(args.corpus)
    records = load_records(args.results, [e.label for e in corpus])
    chosen = draw(records, args.per_stratum, args.seed)
    write_sample(chosen, args.repos, {e.label: e.url for e in corpus}, args.out)
    counts = {name: sum(1 for c in chosen if c[0] == name) for name in STRATA}
    print(f"wrote {len(chosen)} findings to {args.out}: {counts}")


if __name__ == "__main__":
    main()
