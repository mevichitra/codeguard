"""Turn one or more ``summary.json`` files into the rate table the paper reports.

Rates, per scheme:

- false-new rate    false_new / known        persisting findings reported as new
- hidden rate       false_known / introduced genuinely new findings the scheme would hide
- mispair rate      mispaired / known        persisting findings tied to the wrong predecessor
- collision rate    colliding / observations findings sharing a key within one file version
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def rates(summary: dict[str, Any]) -> list[dict[str, Any]]:
    gt = summary["totals"]["gt"]
    obs = summary["collisions"]["observations"]
    rows = []
    for scheme, c in summary["totals"]["schemes"].items():
        rows.append(
            {
                "label": summary.get("label", ""),
                "scheme": scheme,
                "known": gt["known"],
                "introduced": gt["introduced"],
                "false_new": c["false_new"],
                "false_new_rate": _rate(c["false_new"], gt["known"]),
                "false_new_equal_rate": _rate(c["false_new_equal"], gt["known_equal"]),
                "false_new_edited_rate": _rate(c["false_new_edited"], gt["known_edited"]),
                "false_known": c["false_known"],
                "hidden_rate": _rate(c["false_known"], gt["introduced"]),
                "mispair_rate": _rate(c["mispaired"], gt["known"]),
                "collision_rate": _rate(summary["collisions"]["by_scheme"][scheme], obs),
            }
        )
    return rows


def merge(summaries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Pool several repositories into one summary (sums of counts, not averages of rates)."""
    first = summaries[0]
    merged: dict[str, Any] = {
        "label": "ALL",
        "totals": json.loads(json.dumps(first["totals"])),
        "collisions": json.loads(json.dumps(first["collisions"])),
    }
    for s in summaries[1:]:
        for k, v in s["totals"]["gt"].items():
            merged["totals"]["gt"][k] += v
        for scheme, counts in s["totals"]["schemes"].items():
            for k, v in counts.items():
                merged["totals"]["schemes"][scheme][k] += v
        merged["collisions"]["observations"] += s["collisions"]["observations"]
        for scheme, v in s["collisions"]["by_scheme"].items():
            merged["collisions"]["by_scheme"][scheme] += v
    return merged


def _pct(x: float | None) -> str:
    return "   n/a" if x is None else f"{100 * x:6.2f}"


def print_table(rows: Sequence[dict[str, Any]]) -> None:
    head = (
        f"{'scheme':<12} {'false-new %':>11} {'(moved)':>8} {'(edited)':>9} "
        f"{'hidden %':>9} {'mispair %':>10} {'collide %':>10}"
    )
    print(head)
    print("-" * len(head))
    for r in rows:
        print(
            f"{r['scheme']:<12} {_pct(r['false_new_rate']):>11} "
            f"{_pct(r['false_new_equal_rate']):>8} {_pct(r['false_new_edited_rate']):>9} "
            f"{_pct(r['hidden_rate']):>9} {_pct(r['mispair_rate']):>10} "
            f"{_pct(r['collision_rate']):>10}"
        )


def summarize(paths: Sequence[Path], csv_out: Path | None = None) -> None:
    summaries = [json.loads((p / "summary.json").read_text(encoding="utf-8")) for p in paths]
    all_rows: list[dict[str, Any]] = []
    for s in summaries:
        gt = s["totals"]["gt"]
        print(
            f"\n{s['label']}: {s['commit_pairs']} commit pairs, {s['totals']['files']} file "
            f"changes with findings, {gt['known']} persisting findings "
            f"({gt['known_equal']} moved, {gt['known_edited']} edited), "
            f"{gt['introduced']} introduced"
        )
        rows = rates(s)
        print_table(rows)
        all_rows += rows
    if len(summaries) > 1:
        merged = merge(summaries)
        gt = merged["totals"]["gt"]
        print(f"\nALL: {gt['known']} persisting findings, {gt['introduced']} introduced")
        rows = rates(merged)
        print_table(rows)
        all_rows += rows
    if csv_out is not None:
        with csv_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
