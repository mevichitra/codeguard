# SPDX-License-Identifier: Apache-2.0
"""Base class for Python taint rules (CG-SEC-010..014).

A taint rule names a sink (a call and which argument matters).  It reports a
finding when the taint analysis says that argument carries data from an
untrusted source, and attaches the source and every assignment on the way as
related locations.
"""

from __future__ import annotations

import ast
from abc import abstractmethod

from codeguard.engine.context import RuleContext
from codeguard.engine.dataflow.model import TaintInfo
from codeguard.engine.finding import Category, Finding, Location
from codeguard.engine.rule import Rule
from codeguard.lang.base import Language
from codeguard.rules._pyimports import ImportMap

#: Confidence when the source is request data / process input.
WEB_CONFIDENCE = 0.85
LOCAL_CONFIDENCE = 0.6


class TaintRule(Rule):
    """Report sinks whose argument is tainted."""

    category = Category.SECURITY
    languages = frozenset({Language.PYTHON})
    wants_dataflow = True
    #: Source kinds this rule reports (``"web"``, ``"local"``).
    source_kinds: frozenset[str] = frozenset({"web", "local"})
    fix_text: str = ""

    @abstractmethod
    def sink(self, call: ast.Call, imports: ImportMap) -> tuple[ast.expr, str] | None:
        """Return ``(argument, sink description)`` if *call* is a sink, else ``None``."""

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        df = ctx.dataflow
        if df is None:
            return []
        tree = ctx.python_ast
        imports = ImportMap.from_tree(tree)
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            hit = self.sink(node, imports)
            if hit is None:
                continue
            arg, sink_desc = hit
            taint = df.taint_of(arg)
            if taint is None or taint.source.kind not in self.source_kinds:
                continue
            findings.append(self._finding(node, ctx.filename, sink_desc, taint))
        return findings

    def _finding(self, node: ast.Call, filename: str, sink: str, taint: TaintInfo) -> Finding:
        src = taint.source
        hops = len(taint.path)
        via = f" via {hops} assignment{'s' if hops != 1 else ''}" if hops else ""
        description = (
            f"{sink} receives a value derived from {src.label} (line {src.line}){via}. "
            f"{self.description}"
        )
        end_col = node.end_col_offset
        return Finding(
            rule_id=self.id,
            title=self.title,
            description=description,
            severity=self.severity,
            category=self.category,
            location=Location(
                file=filename,
                line=node.lineno,
                col=node.col_offset + 1,
                end_line=node.end_lineno,
                end_col=None if end_col is None else end_col + 1,
            ),
            cwe=self.cwe,
            owasp=self.owasp,
            fix_suggestion=self.fix_text or None,
            confidence=WEB_CONFIDENCE if src.kind == "web" else LOCAL_CONFIDENCE,
            related=taint.related(filename),
        )


def call_label(call: ast.Call) -> str:
    """``"cursor.execute()"`` -- a short readable name for the call."""
    try:
        return f"{ast.unparse(call.func)}()"
    except Exception:  # pragma: no cover - unparse is total on parsed trees
        return "call"
