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


# ---------------------------------------------------------------------------
# Drift (long-span) results: one table per span
# ---------------------------------------------------------------------------


def drift_rates(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """One row per span and scheme, for plotting rates against span length."""
    rows = []
    for entry in summary["spans"]:
        for r in rates({"label": summary.get("label", ""), **entry}):
            rows.append(
                {
                    "label": r["label"],
                    "span": entry["span"],
                    **{k: v for k, v in r.items() if k != "label"},
                }
            )
    return rows


def merge_drift(summaries: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Pool several drift runs span by span, over the spans every run has."""
    common = set.intersection(*({e["span"] for e in s["spans"]} for s in summaries))
    spans = []
    for k in sorted(common):
        entries = [e for s in summaries for e in s["spans"] if e["span"] == k]
        pooled = merge(entries)
        for key in ("files", "renamed_files", "skipped_files"):
            pooled["totals"][key] = sum(e["totals"][key] for e in entries)
        spans.append({"span": k, **pooled})
    return {"label": "ALL", "spans": spans}


def print_span_pivot(rows: Sequence[dict[str, Any]], field: str, title: str) -> None:
    """Schemes down, spans across: one rate per cell."""
    spans = sorted({r["span"] for r in rows})
    cells = {(r["scheme"], r["span"]): r[field] for r in rows}
    head = f"{title:<12} " + " ".join(f"{'k=' + str(k):>8}" for k in spans)
    print(head)
    print("-" * len(head))
    for scheme in dict.fromkeys(r["scheme"] for r in rows):
        print(f"{scheme:<12} " + " ".join(f"{_pct(cells[(scheme, k)]):>8}" for k in spans))


def print_drift(summary: dict[str, Any]) -> list[dict[str, Any]]:
    if "anchor" in summary:
        print(
            f"\n{summary['label']}: anchor {summary['anchor'][:12]}, "
            f"{summary['anchor_back']} first-parent commits behind {summary['ref']}"
        )
    else:
        print(f"\n{summary['label']}: pooled")
    for entry in summary["spans"]:
        gt = entry["totals"]["gt"]
        commit = f" (c_{entry['span']} = {entry['commit'][:12]})" if "commit" in entry else ""
        print(
            f"\nspan {entry['span']}{commit}: {entry['totals']['files']} files with findings, "
            f"{gt['old']} anchor findings, {gt['known']} persisting "
            f"({gt['known_equal']} moved, {gt['known_edited']} edited), "
            f"{gt['introduced']} introduced"
        )
        print_table(rates({"label": summary["label"], **entry}))
    rows = drift_rates(summary)
    print()
    print_span_pivot(rows, "false_new_rate", "false-new %")
    print()
    print_span_pivot(rows, "hidden_rate", "hidden %")
    return rows


def summarize_drift(paths: Sequence[Path], csv_out: Path | None = None) -> None:
    """Per-span rate tables for drift runs; pools them into "ALL" when there are several."""
    summaries = [json.loads((p / "summary.json").read_text(encoding="utf-8")) for p in paths]
    all_rows: list[dict[str, Any]] = []
    for s in summaries:
        all_rows += print_drift(s)
    if len(summaries) > 1:
        all_rows += print_drift(merge_drift(summaries))
    if csv_out is not None:
        with csv_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(all_rows[0]))
            writer.writeheader()
            writer.writerows(all_rows)
