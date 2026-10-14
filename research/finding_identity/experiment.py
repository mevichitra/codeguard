"""Controlled transformation experiment (RQ2): which kinds of change break which schemes?

Python files with findings are sampled from a repository. For each file and each
transformation (see :mod:`transforms`), a target finding is picked, the file is
rewritten around it, both versions are scanned, and every scheme is scored against the
line map the transformation returns. The result is an *invariance matrix*:
transformation x scheme, with false-new and hidden rates.

Two scopes are reported:

- ``target``: the finding the transformation was aimed at (did it keep its identity?)
  plus any finding the transformation introduced (was it hidden?);
- ``file``: every finding in the transformed file, as a CI baseline would see it.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import codeguard

from .matching import OUTCOMES, Observation, collisions, evaluate
from .scan import Scanner, is_candidate
from .schemes import split_lines
from .transforms import Edit, NotApplicable, Source, Transform

GT_KEYS = ("old", "new", "known", "known_equal", "known_edited", "introduced", "removed")
#: Target findings tried per file and transformation before giving up ("n/a").
MAX_TRIES = 50
_SKIP_DIRS = {".git", ".hg", ".tox", ".venv", "venv", "node_modules", "__pycache__"}


@dataclass
class Target:
    rule: str
    line: int


def _empty(schemes: Sequence[str]) -> dict[str, Any]:
    return {
        "cases": 0,
        "not_applicable": Counter(),
        "broken": 0,
        "target_lost": 0,
        "target_lost_rules": Counter(),
        "target_known": 0,
        "needs_review": 0,
        "gt": dict.fromkeys(GT_KEYS, 0),
        "file": {s: dict.fromkeys(OUTCOMES, 0) for s in schemes},
        "target": {s: dict.fromkeys(OUTCOMES, 0) for s in schemes},
        "colliding": dict.fromkeys(schemes, 0),
        "observations": 0,
    }


def python_files(root: Path) -> list[str]:
    """Repository-relative paths of the Python files worth scanning, sorted."""
    out = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root)
        if _SKIP_DIRS.intersection(rel.parts[:-1]) or not path.is_file():
            continue
        if is_candidate(rel.as_posix()):
            out.append(rel.as_posix())
    return sorted(out)


def ground_truth_map(
    edit: Edit, old_text: str, new_text: str, old: Sequence[Observation], new: Sequence[Observation]
) -> dict[int, tuple[int, str]]:
    """The edit's line map in the form :func:`matching.evaluate` takes.

    Where reformatting split an old line, the old line maps to the candidate new line
    that carries a finding of the same rule. A line is "equal" when its text is
    unchanged, else "edited".
    """
    old_lines, new_lines = split_lines(old_text), split_lines(new_text)
    new_rules: dict[int, set[str]] = defaultdict(set)
    for n in new:
        new_rules[n.line].add(n.rule)
    old_rules: dict[int, set[str]] = defaultdict(set)
    for o in old:
        old_rules[o.line].add(o.rule)
    out: dict[int, tuple[int, str]] = {}
    for old_line, new_line in edit.line_map.items():
        for candidate in edit.alternatives.get(old_line, ()):
            if old_rules[old_line] & new_rules[candidate]:
                new_line = candidate
                break
        same = old_lines[old_line - 1] == new_lines[new_line - 1]
        out[old_line] = (new_line, "equal" if same else "edited")
    return out


class Experiment:
    def __init__(
        self,
        root: Path,
        transforms: dict[str, Transform],
        scanner: Scanner,
        schemes: Sequence[str],
        *,
        seed: int = 0,
    ) -> None:
        self.root = root
        self.transforms = transforms
        self.scanner = scanner
        self.schemes = tuple(schemes)
        self.seed = seed
        self.totals = {name: _empty(schemes) for name in transforms}
        self.cases: list[dict[str, Any]] = []
        self.reviews: list[dict[str, Any]] = []
        self.files_with_findings = 0

    def _scan(self, path: str, text: str) -> list[Observation] | None:
        data = text.encode("utf-8")
        result = self.scanner.scan(hashlib.sha256(data).hexdigest(), path, data)
        return None if result is None else result.observations

    def run(self, samples: int, *, progress: bool = True) -> None:
        files = python_files(self.root)
        random.Random(self.seed).shuffle(files)  # noqa: S311  (reproducible sampling)
        started = time.monotonic()
        for path in files:
            if self.files_with_findings >= samples:
                break
            try:
                text = (self.root / path).read_bytes().decode("utf-8")
                src = Source(text)
            except (UnicodeDecodeError, SyntaxError, ValueError, RecursionError):
                continue
            old = self._scan(path, text)
            if not old:
                continue
            self.files_with_findings += 1
            self.run_file(path, src, old)
            if progress and self.files_with_findings % 10 == 0:
                print(
                    f"  {self.files_with_findings}/{samples} files, "
                    f"{time.monotonic() - started:.0f}s",
                    file=sys.stderr,
                )

    def run_file(self, path: str, src: Source, old: list[Observation]) -> None:
        rng = random.Random(f"{self.seed}:{path}")  # noqa: S311
        order = sorted({(o.rule, o.line) for o in old})
        rng.shuffle(order)
        for name, transform in self.transforms.items():
            totals = self.totals[name]
            reasons: Counter[str] = Counter()
            for rule, line in order[:MAX_TRIES]:
                try:
                    edit = transform(src, line)
                except NotApplicable as exc:
                    reasons[str(exc)] += 1
                    continue
                status = self._score(name, path, src, old, Target(rule, line), edit)
                if status == "scored":
                    break
                reasons[status] += 1  # target lost or output broken: try the next finding
            else:
                # Record why the transformation fit no finding in this file (one reason).
                totals["not_applicable"][reasons.most_common(1)[0][0] if reasons else "?"] += 1

    def _score(
        self,
        name: str,
        path: str,
        src: Source,
        old: list[Observation],
        target: Target,
        edit: Edit,
    ) -> str:
        """Score one applied transformation; returns the case status.

        Only a case whose target finding is still detected afterwards ("scored") enters
        the matrix. A target the change makes undetectable ("target_lost", e.g. a loop
        rule after the statement leaves the loop) is counted and logged, not scored.
        """
        totals = self.totals[name]
        case: dict[str, Any] = {"path": path, "transform": name, "rule": target.rule}
        case["line"] = target.line
        try:
            Source(edit.text)
        except (SyntaxError, ValueError):
            totals["broken"] += 1
            self.cases.append({**case, "status": "broken"})
            return "broken"
        new = self._scan(path, edit.text)
        if new is None:
            totals["broken"] += 1
            self.cases.append({**case, "status": "unscannable"})
            return "broken"
        line_map = ground_truth_map(edit, src.text, edit.text, old, new)
        result = evaluate(old, new, line_map, self.schemes, keep_records=True)
        key = ("known", target.rule, target.line)
        tracked = next(
            (r for r in result.records if (r["truth"], r["rule"], r["old_line"]) == key), None
        )
        case["new_line"] = line_map.get(target.line, (None,))[0]
        if tracked is None:
            totals["target_lost"] += 1
            totals["target_lost_rules"][target.rule] += 1
            self.cases.append({**case, "status": "target_lost"})
            return "target lost"
        totals["cases"] += 1
        totals["needs_review"] += int(edit.needs_review)
        for k, v in result.gt.items():
            totals["gt"][k] += v
        for scheme, counts in result.by_scheme.items():
            for k in OUTCOMES:
                totals["file"][scheme][k] += counts[k]
        for scheme, n in collisions(new, self.schemes).items():
            totals["colliding"][scheme] += n
        totals["observations"] += len(new)

        for rec in result.records:
            if rec["truth"] == "new":
                for scheme, outcome in rec["outcomes"].items():  # type: ignore[attr-defined]
                    totals["target"][scheme][outcome] += 1
        totals["target_known"] += 1
        for scheme, outcome in tracked["outcomes"].items():  # type: ignore[attr-defined]
            totals["target"][scheme][outcome] += 1
        case.update(
            status="scored",
            gt=result.gt,
            target_outcomes=tracked["outcomes"],
            introduced=[r for r in result.records if r["truth"] == "new"],
            needs_review=edit.needs_review,
        )
        self.cases.append(case)
        if edit.review:
            self.reviews.append({**case, **edit.review})
        return "scored"


# ---------------------------------------------------------------------------
# Rates and output
# ---------------------------------------------------------------------------


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def matrix_rows(totals: dict[str, dict[str, Any]], schemes: Sequence[str]) -> list[dict[str, Any]]:
    """One row per transformation x scheme."""
    rows = []
    for name, t in totals.items():
        gt = t["gt"]
        for scheme in schemes:
            tc, fc = t["target"][scheme], t["file"][scheme]
            introduced = tc["false_known"] + tc["new_ok"]
            rows.append(
                {
                    "transform": name,
                    "scheme": scheme,
                    "cases": t["cases"],
                    "target_known": t["target_known"],
                    "target_lost": t["target_lost"],
                    "false_new": tc["false_new"],
                    "false_new_rate": _rate(tc["false_new"], t["target_known"]),
                    "mispaired": tc["mispaired"],
                    "mispair_rate": _rate(tc["mispaired"], t["target_known"]),
                    "introduced": introduced,
                    "hidden": tc["false_known"],
                    "hidden_rate": _rate(tc["false_known"], introduced),
                    "file_known": gt["known"],
                    "file_false_new_rate": _rate(fc["false_new"], gt["known"]),
                    "file_mispair_rate": _rate(fc["mispaired"], gt["known"]),
                    "collision_rate": _rate(t["colliding"][scheme], t["observations"]),
                }
            )
    return rows


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{100 * x:5.1f}"


def print_matrix(rows: Sequence[dict[str, Any]], schemes: Sequence[str]) -> None:
    by = {(r["transform"], r["scheme"]): r for r in rows}
    names = list(dict.fromkeys(r["transform"] for r in rows))
    for title, key in (
        ("false-new % (target finding reported as new)", "false_new_rate"),
        ("hidden % (introduced finding matched to an old one)", "hidden_rate"),
    ):
        print(f"\n{title}")
        head = f"{'transform':<16} {'n':>4} " + " ".join(f"{s:>11}" for s in schemes)
        print(head)
        print("-" * len(head))
        for name in names:
            n = by[(name, schemes[0])]["target_known" if key == "false_new_rate" else "introduced"]
            cells = " ".join(f"{_pct(by[(name, s)][key]):>11}" for s in schemes)
            print(f"{name:<16} {n:>4} {cells}")


def write_csv(rows: Sequence[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def markdown_matrix(rows: Sequence[dict[str, Any]], schemes: Sequence[str]) -> str:
    """The matrix as a Markdown table: false-new % / hidden % per cell."""
    by = {(r["transform"], r["scheme"]): r for r in rows}
    names = list(dict.fromkeys(r["transform"] for r in rows))
    out = ["| transform | n | " + " | ".join(schemes) + " |"]
    out.append("|---|---:|" + "---:|" * len(schemes))
    for name in names:
        first = by[(name, schemes[0])]
        cells = []
        for s in schemes:
            r = by[(name, s)]
            cell = _pct(r["false_new_rate"]).strip()
            if r["introduced"]:
                cell += f" / {_pct(r['hidden_rate']).strip()}"
            cells.append(cell)
        out.append(f"| {name} | {first['target_known']} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


#: One-hue light-to-dark ramp for rates (0 = lightest), plus text and n/a colours.
SEQUENTIAL_BLUE = ("#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b")
NA_FILL, INK, INK_MUTED = "#f0efec", "#1f2328", "#6e7781"


def heatmap(rows: Sequence[dict[str, Any]], schemes: Sequence[str], path: Path) -> bool:
    """Draw the matrix as two heatmaps (false-new and hidden). False without matplotlib."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        return False
    cmap = LinearSegmentedColormap.from_list("rate", SEQUENTIAL_BLUE)
    cmap.set_bad(NA_FILL)
    by = {(r["transform"], r["scheme"]): r for r in rows}
    names = list(dict.fromkeys(r["transform"] for r in rows))
    hidden_names = [n for n in names if by[(n, schemes[0])]["introduced"]]
    panels = [("False-new rate (target finding)", "false_new_rate", "target_known", names)]
    if hidden_names:
        panels.append(
            ("Hidden rate (introduced finding)", "hidden_rate", "introduced", hidden_names)
        )
    heights = [len(p[3]) for p in panels]
    fig, axes = plt.subplots(
        len(panels),
        1,
        figsize=(1.1 * len(schemes) + 2.6, 0.42 * sum(heights) + 1.6 * len(panels)),
        gridspec_kw={"height_ratios": heights},
        squeeze=False,
    )
    for ax, (title, key, count, ylabels) in zip(axes[:, 0], panels, strict=True):
        values = np.array(
            [
                [np.nan if by[(n, s)][key] is None else by[(n, s)][key] for s in schemes]
                for n in ylabels
            ],
            dtype=float,
        )
        image = ax.imshow(np.ma.masked_invalid(values), cmap=cmap, vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(schemes)), schemes, rotation=30, ha="right")
        ax.set_yticks(
            range(len(ylabels)), [f"{n} (n={by[(n, schemes[0])][count]})" for n in ylabels]
        )
        ax.set_title(title, loc="left", fontsize=11)
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i in range(len(ylabels)):
            for j in range(len(schemes)):
                v = values[i, j]
                label = "n/a" if np.isnan(v) else f"{100 * v:.0f}"
                dark = not np.isnan(v) and v > 0.5
                ink = "white" if dark else (INK_MUTED if np.isnan(v) else INK)
                ax.text(j, i, label, ha="center", va="center", fontsize=8, color=ink)
        fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02, format=lambda x, _: f"{x:.0%}")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return True


def run_experiment(
    root: Path,
    *,
    label: str,
    transforms: dict[str, Transform],
    scanner: Scanner,
    schemes: Sequence[str],
    samples: int,
    seed: int,
    out_dir: Path,
    meta: dict[str, Any] | None = None,
    draw_heatmap: bool = False,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    exp = Experiment(root, transforms, scanner, schemes, seed=seed)
    exp.run(samples)
    rows = matrix_rows(exp.totals, schemes)
    summary = {
        "label": label,
        "root": str(root),
        "samples": samples,
        "seed": seed,
        "files_with_findings": exp.files_with_findings,
        "transforms": list(transforms),
        "schemes": list(schemes),
        "codeguard_version": codeguard.__version__,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 1),
        **(meta or {}),
        "totals": exp.totals,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (out_dir / "cases.jsonl").open("w", encoding="utf-8") as fh:
        for case in exp.cases:
            fh.write(json.dumps(case) + "\n")
    if exp.reviews:
        with (out_dir / "review.jsonl").open("w", encoding="utf-8") as fh:
            for case in exp.reviews:
                fh.write(json.dumps(case) + "\n")
    if rows:
        write_csv(rows, out_dir / "matrix.csv")
        (out_dir / "matrix.md").write_text(markdown_matrix(rows, schemes), encoding="utf-8")
    print(f"\n{label}: {exp.files_with_findings} files with findings")
    print(f"{'transform':<16} {'cases':>5} {'lost':>5} {'n/a':>5} {'broken':>6}  top n/a reason")
    for name, t in exp.totals.items():
        na = sum(t["not_applicable"].values())
        reason = t["not_applicable"].most_common(1)[0][0] if na else ""
        counts = f"{t['cases']:>5} {t['target_lost']:>5} {na:>5} {t['broken']:>6}"
        print(f"{name:<16} {counts}  {reason}")
    if rows:
        print_matrix(rows, schemes)
    if draw_heatmap and rows:
        if heatmap(rows, schemes, out_dir / "matrix.png"):
            print(f"\nheatmap: {out_dir / 'matrix.png'}")
        else:
            print("\nheatmap skipped: matplotlib is not installed", file=sys.stderr)
    return summary
