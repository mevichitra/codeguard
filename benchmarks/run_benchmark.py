#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Benchmark harness — computes per-rule precision and recall against a labelled corpus.

Usage:
    python benchmarks/run_benchmark.py
    python benchmarks/run_benchmark.py --rule CG-SEC-001
    python benchmarks/run_benchmark.py --verbose

Output:
    A table of per-rule precision, recall, F1, and counts.
    Any claim about rule accuracy must reference this script's output.

Corpus format:
    benchmarks/corpus/
        <rule_id>/
            tp/   # True positives  — files that MUST trigger the rule
            tn/   # True negatives  — files that MUST NOT trigger the rule
            fp/   # Known false positives (optional, for documentation)

Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * (precision * recall) / (precision + recall)
"""

from __future__ import annotations

import argparse
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

# Repo-relative import
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

import codeguard.rules  # noqa: F401 — register all rules
from codeguard.engine.runner import AnalysisRunner

CORPUS_DIR = Path(__file__).parent / "corpus"


@dataclass
class RuleStats:
    rule_id: str
    tp: int = 0   # files in tp/ that produced >= 1 finding
    fn: int = 0   # files in tp/ that produced 0 findings (missed)
    tn: int = 0   # files in tn/ that produced 0 findings (correct)
    fp: int = 0   # files in tn/ that produced >= 1 finding (false alarm)

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else float("nan")

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else float("nan")

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if p != p or r != r:  # nan check
            return float("nan")
        denom = p + r
        return 2 * p * r / denom if denom else float("nan")


def run_benchmark(rule_id: str | None = None, verbose: bool = False) -> list[RuleStats]:
    """Run the benchmark over the corpus and return per-rule stats."""
    results: list[RuleStats] = []

    if not CORPUS_DIR.exists():
        print(f"Corpus directory not found: {CORPUS_DIR}", file=sys.stderr)
        print("Create benchmarks/corpus/<rule_id>/tp/ and tn/ directories.", file=sys.stderr)
        return []

    rule_dirs = sorted(CORPUS_DIR.iterdir())
    if rule_id:
        rule_dirs = [d for d in rule_dirs if d.name.upper() == rule_id.upper()]

    for rule_dir in rule_dirs:
        if not rule_dir.is_dir():
            continue

        rid = rule_dir.name.upper()
        runner = AnalysisRunner(rule_ids=[rid])
        stats = RuleStats(rule_id=rid)

        # True positive files — rule MUST fire
        tp_dir = rule_dir / "tp"
        if tp_dir.exists():
            for py_file in sorted(tp_dir.glob("*.py")):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    findings = [f for f in runner.run_file(py_file) if not f.suppressed]
                fired = len(findings) > 0
                if fired:
                    stats.tp += 1
                else:
                    stats.fn += 1
                    if verbose:
                        print(f"  MISS  {py_file.relative_to(REPO_ROOT)}")

        # True negative files — rule MUST NOT fire
        tn_dir = rule_dir / "tn"
        if tn_dir.exists():
            for py_file in sorted(tn_dir.glob("*.py")):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    findings = [f for f in runner.run_file(py_file) if not f.suppressed]
                fired = len(findings) > 0
                if not fired:
                    stats.tn += 1
                else:
                    stats.fp += 1
                    if verbose:
                        print(f"  FALSE POSITIVE  {py_file.relative_to(REPO_ROOT)}")
                        for f in findings:
                            print(f"    {f.rule_id} @ line {f.location.line}")

        results.append(stats)

    return results


def print_table(results: list[RuleStats]) -> None:
    """Print a results table to stdout."""
    if not results:
        print("No results. Check that benchmarks/corpus/ is populated.")
        return

    header = f"{'Rule':<14} {'Precision':>10} {'Recall':>8} {'F1':>8} {'TP':>4} {'FN':>4} {'TN':>4} {'FP':>4}"
    print(header)
    print("-" * len(header))

    for s in results:
        def fmt(v: float) -> str:
            return f"{v:.3f}" if v == v else "  N/A"

        print(
            f"{s.rule_id:<14} {fmt(s.precision):>10} {fmt(s.recall):>8} "
            f"{fmt(s.f1):>8} {s.tp:>4} {s.fn:>4} {s.tn:>4} {s.fp:>4}"
        )

    print()
    print("NOTE: These numbers are only meaningful when the corpus is large and representative.")
    print("      Small corpora produce unreliable estimates. Grow the corpus before citing numbers.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rule", help="Only benchmark this rule ID")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show individual misses and false positives")
    args = parser.parse_args()

    results = run_benchmark(rule_id=args.rule, verbose=args.verbose)
    print_table(results)

    # Non-zero exit if any rule has recall < 1.0 (misses are bugs)
    misses = sum(s.fn for s in results)
    sys.exit(1 if misses else 0)


if __name__ == "__main__":
    main()
