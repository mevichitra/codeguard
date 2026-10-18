# SPDX-License-Identifier: Apache-2.0

"""Gate-level metrics: what a CI gate that fails on new findings does with each scheme.

The per-finding rates of :mod:`matching` count a hidden finding as one error whatever
else the commit holds. A gate sees the commit as a whole: it fails when the scheme
reports at least one finding as new, so a hidden finding still trips the gate when
another finding in the same commit pair is reported new, and slips through only when
nothing is. This module scores each commit pair of a replay as a gate would:

- the ground truth says the gate should fail when the pair has an introduced finding;
- the scheme makes it fail when it reports any finding as new (``new_ok`` or
  ``false_new``).

Per scheme and repository it returns ``(numerator, denominator)`` for:

- ``gate_miss``: pairs with an introduced finding where the gate stays silent, over
  pairs with an introduced finding;
- ``gate_false_alarm``: pairs without introduced findings where the gate fails, over
  pairs without introduced findings;
- ``gate_wrong_reason``: pairs with an introduced finding where the gate fails only on
  persisting findings (every introduced finding hidden), over pairs with an introduced
  finding;
- ``hidden_masked`` and ``hidden_silent``: introduced findings that the scheme hides in a
  pair whose gate fails anyway, and in one whose gate stays silent, over introduced
  findings. The two add up to the hidden rate.

Pairs come from ``pairs.jsonl``, so pairs whose changed files hold no findings count
(the gate is silent there, and should be). Findings in files a commit does not change
are the same in both versions under every scheme, so they never make a gate fail.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

#: (name, description) of each gate metric.
GATE_METRICS = (
    ("gate_miss", "commit pairs with an introduced finding where the gate reports nothing new"),
    (
        "gate_false_alarm",
        "commit pairs without introduced findings where the gate reports something new",
    ),
    (
        "gate_wrong_reason",
        "commit pairs with an introduced finding where the gate fails only on persisting ones",
    ),
    ("hidden_masked", "introduced findings hidden in a commit pair whose gate fails anyway"),
    ("hidden_silent", "introduced findings hidden in a commit pair whose gate stays silent"),
)

#: Outcomes under which a scheme reports the finding as new.
REPORTS_NEW = frozenset({"new_ok", "false_new"})


def _records_by_commit(
    findings: Path, keep: Callable[[str], bool]
) -> dict[str, list[dict[str, Any]]]:
    by_commit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with findings.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if keep(rec["rule"]):
                by_commit[rec["commit"]].append(rec)
    return by_commit


def _pair_commits(pairs: Path) -> Iterator[str]:
    with pairs.open(encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)["new"]


def gate_counts(
    pairs: Path,
    findings: Path,
    schemes: Sequence[str],
    keep: Callable[[str], bool] = lambda rule: True,
) -> dict[str, dict[str, tuple[int, int]]]:
    """``{scheme: {metric: (numerator, denominator)}}`` for one replay.

    *pairs* and *findings* are the replay's ``pairs.jsonl`` and ``findings.jsonl``;
    *keep* says which rules the gate checks.
    """
    by_commit = _records_by_commit(findings, keep)
    c: dict[str, dict[str, list[int]]] = {
        s: {name: [0, 0] for name, _ in GATE_METRICS} for s in schemes
    }
    for commit in _pair_commits(pairs):
        recs = by_commit.get(commit, [])
        introduced = [r for r in recs if r["truth"] == "new"]
        for s in schemes:
            m = c[s]
            fails = any(r["outcomes"][s] in REPORTS_NEW for r in recs)
            hidden = sum(r["outcomes"][s] == "false_known" for r in introduced)
            if introduced:
                m["gate_miss"][0] += not fails
                m["gate_miss"][1] += 1
                caught = any(r["outcomes"][s] == "new_ok" for r in introduced)
                m["gate_wrong_reason"][0] += fails and not caught
                m["gate_wrong_reason"][1] += 1
            else:
                m["gate_false_alarm"][0] += fails
                m["gate_false_alarm"][1] += 1
            m["hidden_masked" if fails else "hidden_silent"][0] += hidden
            m["hidden_masked"][1] += len(introduced)
            m["hidden_silent"][1] += len(introduced)
    return {s: {k: (v[0], v[1]) for k, v in m.items()} for s, m in c.items()}
