# SPDX-License-Identifier: Apache-2.0
"""Python taint analysis (placeholder until the engine lands)."""

from __future__ import annotations

import ast

from .model import DataflowResult


def analyze_python(tree: ast.Module, source: str) -> DataflowResult | None:
    """Return the taint analysis for *tree*."""
    return None
