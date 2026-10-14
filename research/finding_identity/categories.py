"""Rule categories (security, performance, quality) for per-category totals.

Every scheme key includes the rule ID, and the ground truth pairs findings of the same
rule only, so a file's findings split exactly by category: scoring each category's
findings on their own gives counts that add up to the all-category counts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from functools import cache

import codeguard.rules  # noqa: F401  (registers the built-in rules)
from codeguard.engine.registry import REGISTRY

from .matching import Observation

UNKNOWN = "unknown"


@cache
def _categories() -> dict[str, str]:
    return {r.id: r.category.value for r in REGISTRY.all()}


def category_of(rule_id: str) -> str:
    """The category of *rule_id*, or ``"unknown"`` for a rule not in the registry."""
    return _categories().get(rule_id, UNKNOWN)


def split_by_category(observations: Sequence[Observation]) -> dict[str, list[Observation]]:
    out: dict[str, list[Observation]] = defaultdict(list)
    for o in observations:
        out[category_of(o.rule)].append(o)
    return dict(out)
