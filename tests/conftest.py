# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures and helpers for CodeGuard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# Load all built-in rules so REGISTRY is populated before any test runs
import codeguard.rules  # noqa: F401

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(category: str, rule_id: str, fixture_name: str) -> str:
    """Read a fixture file and return its source text.

    Parameters
    ----------
    category:
        e.g. ``"security"``
    rule_id:
        e.g. ``"cg_sec_001"``
    fixture_name:
        ``"vulnerable"`` or ``"safe"`` (without ``.py``)
    """
    path = FIXTURES_DIR / category / rule_id / f"{fixture_name}.py"
    if not path.exists():
        pytest.fail(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8")
