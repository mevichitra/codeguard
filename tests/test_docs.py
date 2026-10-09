# SPDX-License-Identifier: Apache-2.0
"""Every registered rule has a documentation page that is reachable from the site nav."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeguard.engine.registry import REGISTRY

ROOT = Path(__file__).resolve().parents[1]
RULE_IDS = [rule.id for rule in REGISTRY.all()]


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_rule_has_docs_page(rule_id: str) -> None:
    assert (ROOT / "docs" / "rules" / f"{rule_id}.md").is_file()


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_rule_page_is_in_nav(rule_id: str) -> None:
    nav = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert f"rules/{rule_id}.md" in nav


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_rule_listed_in_rules_index(rule_id: str) -> None:
    index = (ROOT / "docs" / "rules" / "index.md").read_text(encoding="utf-8")
    assert rule_id in index
