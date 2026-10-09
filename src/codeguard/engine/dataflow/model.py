# SPDX-License-Identifier: Apache-2.0
"""Data types shared by the taint (dataflow) analysis and the rules that read it."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Protocol

from codeguard.engine.finding import Location, RelatedLocation

#: Longest assignment path kept on a :class:`TaintInfo` (older hops are dropped).
MAX_HOPS = 6


@dataclass(frozen=True)
class TaintSource:
    """Where untrusted data entered the program."""

    label: str
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None


@dataclass(frozen=True)
class TaintHop:
    """One assignment that carried tainted data forward."""

    line: int
    col: int
    text: str


@dataclass(frozen=True)
class TaintInfo:
    """Why a value is considered tainted: its source and the assignments on the way."""

    source: TaintSource
    path: tuple[TaintHop, ...] = ()

    def extended(self, hop: TaintHop) -> TaintInfo:
        """Return a copy with *hop* appended (keeping at most :data:`MAX_HOPS`)."""
        if self.path and self.path[-1] == hop:
            return self
        return TaintInfo(self.source, (*self.path, hop)[-MAX_HOPS:])

    def related(self, file: str) -> tuple[RelatedLocation, ...]:
        """The source and each hop as :class:`RelatedLocation` entries."""
        src = self.source
        out = [
            RelatedLocation(
                Location(file, src.line, src.col, src.end_line, src.end_col),
                f"Untrusted input: {src.label}",
            )
        ]
        out.extend(
            RelatedLocation(Location(file, hop.line, hop.col), f"Flows through: {hop.text}")
            for hop in self.path
        )
        return tuple(out)


class DataflowResult(Protocol):
    """What a rule can ask the taint analysis about one file."""

    def taint_of(self, node: ast.AST) -> TaintInfo | None:
        """The taint carried by expression *node*, or ``None`` if it is clean."""

    def is_tainted(self, node: ast.AST) -> bool:
        """Shorthand for ``taint_of(node) is not None``."""
