# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures and helpers for CodeGuard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# Load all built-in rules so REGISTRY is populated before any test runs
import codeguard.rules  # noqa: F401

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_EXT = {"python": "py", "javascript": "js", "typescript": "ts"}


def load_fixture(language: str, category: str, rule_id: str, fixture_name: str) -> str:
    """Read a fixture file and return its source text.

    Layout: ``tests/fixtures/<language>/<category>/<rule_id>/<fixture_name>.<ext>``.

    Parameters
    ----------
    language:
        ``"python"``, ``"javascript"``, or ``"typescript"``.
    category:
        e.g. ``"security"``.
    rule_id:
        e.g. ``"cg_sec_001"``.
    fixture_name:
        ``"vulnerable"`` or ``"safe"`` (without extension).
    """
    ext = _EXT[language]
    path = FIXTURES_DIR / language / category / rule_id / f"{fixture_name}.{ext}"
    if not path.exists():
        pytest.fail(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8")
