# SPDX-License-Identifier: Apache-2.0
"""Intraprocedural taint (dataflow) analysis."""

from __future__ import annotations

from .model import DataflowResult, TaintHop, TaintInfo, TaintSource

__all__ = ["DataflowResult", "TaintHop", "TaintInfo", "TaintSource"]
