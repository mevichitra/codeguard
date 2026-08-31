# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures and helpers for CodeGuard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

# Load all built-in rules so REGISTRY is populated before any test runs
import codeguard.rules  # noqa: F401

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(language: str, category: str, rule_id: str, fixture_name: str) -> str:
    """Read a fixture file and return its source text.

    Layout: ``tests/fixtures/<language>/<category>/<rule_id>/<fixture_name>.<ext>``.
    The extension is discovered by glob, so ``.js`` / ``.jsx`` / ``.ts`` / ``.tsx``
    / ``.py`` all work.

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
    directory = FIXTURES_DIR / language / category / rule_id
    matches = sorted(directory.glob(f"{fixture_name}.*"))
    if not matches:
        pytest.fail(f"Fixture not found: {directory / fixture_name}.*")
    return matches[0].read_text(encoding="utf-8")


def fixture_path(language: str, category: str, rule_id: str, fixture_name: str) -> Path:
    """Like :func:`load_fixture` but returns the path (for the ``filename=`` arg)."""
    directory = FIXTURES_DIR / language / category / rule_id
    matches = sorted(directory.glob(f"{fixture_name}.*"))
    if not matches:
        pytest.fail(f"Fixture not found: {directory / fixture_name}.*")
    return matches[0]
