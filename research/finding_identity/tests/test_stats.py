"""Statistics checked against hand-computed values."""

import csv
import json
import math
from pathlib import Path
from typing import Any

import pytest

from research.finding_identity.stats import (
    ALL,
    bootstrap_draws,
    build_tables,
    cluster_bootstrap,
    counts,
    load_summaries,
    macro_rate,
    pooled_rate,
    quantile,
    run_stats,
    scope_block,
    wilson,
)


def test_wilson_half() -> None:
    # p = 0.5, n = 10: centre 0.5, half-width z*sqrt(0.025 + z^2/400)/(1 + z^2/10).
    lo, hi = wilson(5, 10) or (0.0, 0.0)
    assert lo == pytest.approx(0.236593, abs=1e-6)
    assert hi == pytest.approx(0.763407, abs=1e-6)


def test_wilson_zero_successes() -> None:
    # k = 0: the interval is [0, z^2 / (n + z^2)].
    lo, hi = wilson(0, 10) or (1.0, 1.0)
    z2 = 1.959963984540054**2
    assert lo == 0.0
    assert hi == pytest.approx(z2 / (10 + z2))


def test_wilson_all_successes_and_empty() -> None:
    # k = n: the interval is [n / (n + z^2), 1].
    lo, hi = wilson(20, 20) or (0.0, 0.0)
    assert hi == 1.0 and lo == pytest.approx(20 / (20 + 1.959963984540054**2))
    assert wilson(0, 0) is None


def test_quantile_type7() -> None:
    xs = [4.0, 1.0, 3.0, 2.0]
    assert quantile(xs, 0.5) == 2.5
    assert quantile(xs, 0.25) == 1.75
    assert quantile(xs, 0.75) == 3.25
    assert quantile([7.0], 0.9) == 7.0
    with pytest.raises(ValueError):
        quantile([], 0.5)


def test_pooled_versus_macro() -> None:
    # Repository A: 1 of 4 (25%); B: 3 of 6 (50%); C has no denominator.
    pairs = [(1, 4), (3, 6), (0, 0)]
    assert pooled_rate(pairs) == pytest.approx(0.4)  # 4 / 10
    assert macro_rate(pairs) == pytest.approx(0.375)  # (0.25 + 0.5) / 2
    assert pooled_rate([(0, 0)]) is None
    assert macro_rate([(0, 0)]) is None


def test_cluster_bootstrap_with_fixed_draws() -> None:
    pairs = [(1, 4), (3, 6)]
    # Resamples: {A, A} -> 0.25; {B, B} -> 0.5; {A, B} -> pooled 0.4, macro 0.375.
    draws = [[0, 0], [1, 1], [0, 1]]
    result = cluster_bootstrap(pairs, draws)
    # Sorted pooled values [0.25, 0.4, 0.5]; type-7 positions 0.05 and 1.95.
    pooled = result["pooled"]
    assert pooled is not None
    assert pooled[0] == pytest.approx(0.25 + 0.05 * 0.15)
    assert pooled[1] == pytest.approx(0.4 + 0.95 * 0.1)
    macro = result["macro"]
    assert macro is not None
    assert macro[0] == pytest.approx(0.25 + 0.05 * 0.125)
    assert macro[1] == pytest.approx(0.375 + 0.95 * 0.125)


def test_cluster_bootstrap_identical_repos_collapses() -> None:
    pairs = [(2, 8)] * 5
    result = cluster_bootstrap(pairs, bootstrap_draws(5, 200, seed=1))
    assert result["pooled"] == pytest.approx((0.25, 0.25))
    assert result["macro"] == pytest.approx((0.25, 0.25))


def test_cluster_bootstrap_drops_undefined_resamples() -> None:
    pairs = [(0, 0), (1, 2)]
    result = cluster_bootstrap(pairs, [[0, 0], [1, 1]])
    assert result["pooled"] == pytest.approx((0.5, 0.5))


def test_bootstrap_draws_are_reproducible() -> None:
    assert bootstrap_draws(6, 3, seed=7) == bootstrap_draws(6, 3, seed=7)
    assert all(len(d) == 6 and all(0 <= i < 6 for i in d) for d in bootstrap_draws(6, 3, 7))


# ---------------------------------------------------------------------------
# Summaries and tables
# ---------------------------------------------------------------------------

SCHEMES = ("line", "codeguard")


def _block(known: int, introduced: int, false_new: dict[str, int], obs: int) -> dict[str, Any]:
    schemes = {}
    for s in SCHEMES:
        schemes[s] = {
            "known_ok": known - false_new[s],
            "mispaired": 0,
            "false_new": false_new[s],
            "false_known": 1 if s == "line" and introduced else 0,
            "new_ok": introduced - (1 if s == "line" and introduced else 0),
            "false_new_equal": false_new[s],
            "false_new_edited": 0,
        }
    return {
        "totals": {
            "gt": {
                "old": known,
                "new": known + introduced,
                "known": known,
                "known_equal": known,
                "known_edited": 0,
                "introduced": introduced,
                "removed": 0,
            },
            "schemes": schemes,
            "files": 1,
            "renamed_files": 0,
            "skipped_files": 0,
        },
        "collisions": {"observations": obs, "by_scheme": {"line": 0, "codeguard": 2}},
    }


def _summary(label: str, sec: dict[str, Any], qual: dict[str, Any]) -> dict[str, Any]:
    total = json.loads(json.dumps(sec))
    for part in ("gt",):
        for k, v in qual["totals"][part].items():
            total["totals"][part][k] += v
    for s in SCHEMES:
        for k, v in qual["totals"]["schemes"][s].items():
            total["totals"]["schemes"][s][k] += v
    total["collisions"]["observations"] += qual["collisions"]["observations"]
    for s in SCHEMES:
        total["collisions"]["by_scheme"][s] += qual["collisions"]["by_scheme"][s]
    return {
        "label": label,
        "head": "0" * 40,
        "commit_pairs": 10,
        **total,
        "by_category": {"security": sec, "quality": qual},
    }


@pytest.fixture
def summaries() -> list[dict[str, Any]]:
    # Security: A has 1 of 4 line false-new, B 3 of 6.  Quality adds 10 known, none lost.
    a = _summary(
        "a",
        _block(4, 2, {"line": 1, "codeguard": 0}, 10),
        _block(10, 0, {"line": 0, "codeguard": 0}, 20),
    )
    b = _summary(
        "b",
        _block(6, 0, {"line": 3, "codeguard": 0}, 10),
        _block(10, 0, {"line": 0, "codeguard": 0}, 20),
    )
    return [a, b]


def test_scope_block_and_counts(summaries: list[dict[str, Any]]) -> None:
    a = summaries[0]
    assert counts(scope_block(a, ALL) or {}, "line", "false_new") == (1, 14)
    assert counts(scope_block(a, "security") or {}, "line", "false_new") == (1, 4)
    assert counts(scope_block(a, "security") or {}, "line", "hidden") == (1, 2)
    assert counts(scope_block(a, ALL) or {}, "codeguard", "collision") == (4, 30)
    assert scope_block({"label": "old"}, "security") is None


def test_build_tables_pooled_and_spread(summaries: list[dict[str, Any]]) -> None:
    tables = build_tables(summaries, scopes=(ALL, "security"), resamples=500, seed=3)
    by = {(r["scope"], r["scheme"], r["metric"]): r for r in tables.pooled}

    sec = by[("security", "line", "false_new")]
    assert (sec["num"], sec["den"]) == (4, 10)
    assert sec["pooled"] == pytest.approx(0.4)
    assert sec["macro"] == pytest.approx(0.375)
    assert sec["median"] == pytest.approx(0.375)
    assert sec["q1"] == pytest.approx(0.3125)
    assert sec["q3"] == pytest.approx(0.4375)
    lo, hi = wilson(4, 10) or (0.0, 0.0)
    assert (sec["wilson_lo"], sec["wilson_hi"]) == pytest.approx((lo, hi))
    # With two repositories every resample is AA, BB or AB: the interval stays in range.
    assert 0.25 <= sec["boot_lo"] <= sec["boot_hi"] <= 0.5

    everything = by[(ALL, "line", "false_new")]
    assert (everything["num"], everything["den"]) == (4, 30)
    assert everything["macro"] == pytest.approx((1 / 14 + 3 / 16) / 2)

    hidden = by[("security", "line", "hidden")]
    assert (hidden["num"], hidden["den"], hidden["repos_with_rate"]) == (1, 2, 1)
    edited = by[("security", "line", "false_new_edited")]
    assert edited["pooled"] is None and edited["median"] is None

    per_repo = [
        r
        for r in tables.per_repo
        if r["scope"] == "security" and r["scheme"] == "line" and r["metric"] == "false_new"
    ]
    assert [(r["label"], r["rate"]) for r in per_repo] == [("a", 0.25), ("b", 0.5)]
    assert tables.repos[0]["security_known"] == 4 and tables.repos[0]["all_known"] == 14


def test_missing_scope_is_skipped(summaries: list[dict[str, Any]]) -> None:
    del summaries[1]["by_category"]
    tables = build_tables(summaries, scopes=(ALL, "security"), resamples=10)
    assert {r["scope"] for r in tables.pooled} == {ALL}


def test_run_stats_writes_tables(tmp_path: Path, summaries: list[dict[str, Any]]) -> None:
    results = tmp_path / "results"
    for s in summaries:
        (results / s["label"]).mkdir(parents=True)
        (results / s["label"] / "summary.json").write_text(json.dumps(s))
    (results / "_logs").mkdir()  # batch logs are not results
    assert [s["label"] for s in load_summaries([results], ["b", "a", "z"])] == ["b", "a"]

    out = tmp_path / "tables"
    run_stats([results], out, resamples=50)
    with (out / "pooled.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    row = next(
        r
        for r in rows
        if (r["scope"], r["scheme"], r["metric"]) == ("security", "line", "false_new")
    )
    assert math.isclose(float(row["pooled"]), 0.4)
    assert (out / "per_repo.csv").exists() and (out / "repos.csv").exists()
    assert "Security findings" in (out / "tables.md").read_text()
    per_repo_md = (out / "per_repo.md").read_text()
    assert "| a | 4 | 25.00 | 0.00 |" in per_repo_md  # security: line 1/4, codeguard 0/4
