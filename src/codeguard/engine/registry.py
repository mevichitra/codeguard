# SPDX-License-Identifier: Apache-2.0
"""Rule registry — the central catalogue of all registered CodeGuard rules."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .rule import Rule


class RuleRegistry:
    """Central registry that maps rule IDs to :class:`~codeguard.engine.rule.Rule` instances.

    Rules self-register at import time via :meth:`register`.  The module-level
    :data:`REGISTRY` singleton is what the runner uses; tests may construct
    isolated registries to avoid cross-rule interference.

    Example
    -------
    ::

        from codeguard.engine.registry import REGISTRY

        for rule in REGISTRY:
            print(rule.id, rule.title)
    """

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        """Register *rule*.

        Raises
        ------
        ValueError
            If another rule with the same ``id`` is already registered.
            Rule IDs are a public contract; duplicates are a hard error.
        TypeError
            If *rule* does not have a non-empty ``id`` attribute.
        """
        if not getattr(rule, "id", None):
            raise TypeError(f"{rule!r} does not have a non-empty 'id' attribute")
        if rule.id in self._rules:
            existing = self._rules[rule.id]
            raise ValueError(
                f"Rule ID conflict: {rule.id!r} is already registered by "
                f"{existing.__class__.__qualname__}. "
                f"Rule IDs are permanent — claim a new one."
            )
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule | None:
        """Return the rule for *rule_id*, or ``None`` if not registered."""
        return self._rules.get(rule_id)

    def all(self) -> list[Rule]:
        """Return all registered rules, sorted by ID."""
        return sorted(self._rules.values(), key=lambda r: r.id)

    def __iter__(self) -> Iterator[Rule]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self._rules)

    def __contains__(self, rule_id: object) -> bool:
        return rule_id in self._rules

    def __repr__(self) -> str:
        ids = sorted(self._rules)
        return f"RuleRegistry({ids})"


#: Module-level singleton used by the runner and all rules.
REGISTRY: RuleRegistry = RuleRegistry()
