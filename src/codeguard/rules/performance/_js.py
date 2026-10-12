# SPDX-License-Identifier: Apache-2.0
"""JavaScript / TypeScript performance rules (CG-PERF-1xx)."""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import (
    FUNCTION_KINDS,
    arguments,
    callee_text,
    calls,
    enclosing_loop,
    is_for_await,
    is_literal,
    member_property,
    new_expressions,
)

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})


class _JsPerfRule(TreeSitterRule):
    category = Category.PERFORMANCE
    languages = _JS_TS


class AwaitInLoopRule(_JsPerfRule):
    id = "CG-PERF-101"
    title = "await inside a loop runs the iterations one after another"
    description = (
        "Each iteration waits for the previous await to finish. When the iterations are "
        "independent, starting them together with Promise.all is usually much faster."
    )
    severity = Severity.LOW

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in root.walk():
            if node.kind != "await_expression":
                continue
            loop = enclosing_loop(node)
            if loop is None or is_for_await(loop):
                continue
            findings.append(
                self._make_finding(
                    node=node,
                    ctx=ctx,
                    fix_suggestion=(
                        "If iterations are independent: await Promise.all(items.map(async "
                        "(item) => ...)). Keep the loop when order or rate limits matter."
                    ),
                    confidence=0.6,
                )
            )
        return findings


class JsonDeepCloneRule(_JsPerfRule):
    id = "CG-PERF-102"
    title = "Deep clone with JSON.parse(JSON.stringify(x))"
    description = (
        "Serialising to a JSON string and parsing it back is slow for large objects and "
        "silently drops undefined, functions, Dates (become strings), Maps, and Sets."
    )
    severity = Severity.INFO

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            if callee_text(call) != "JSON.parse":
                continue
            args = arguments(call)
            if (
                args
                and args[0].kind == "call_expression"
                and callee_text(args[0]) == "JSON.stringify"
            ):
                findings.append(
                    self._make_finding(
                        node=call,
                        ctx=ctx,
                        fix_suggestion=(
                            "Use structuredClone(x) (Node 17+, all modern browsers). It keeps "
                            "Dates, Maps, and Sets, but throws on functions."
                        ),
                    )
                )
        return findings


class SpreadInReduceRule(_JsPerfRule):
    id = "CG-PERF-103"
    title = "Accumulator copied with spread inside reduce"
    description = (
        "Returning [...acc, x] or {...acc, k: v} from a reduce callback copies the whole "
        "accumulator on every step, which is quadratic in the number of items."
    )
    severity = Severity.LOW

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            if not callee_text(call).endswith(".reduce"):
                continue
            args = arguments(call)
            if not args or args[0].kind not in FUNCTION_KINDS:
                continue
            acc = _first_param(args[0])
            if acc is None:
                continue
            spread = f"...{acc}"
            if any(
                n.kind == "spread_element" and n.text().replace(" ", "") == spread
                for n in args[0].walk()
            ):
                findings.append(
                    self._make_finding(
                        node=call,
                        ctx=ctx,
                        fix_suggestion=(
                            "Mutate the accumulator (acc.push(x); return acc) or use a plain "
                            "loop / Object.fromEntries."
                        ),
                    )
                )
        return findings


def _first_param(fn: SourceNode) -> str | None:
    params = fn.child_by_field("parameters") or fn.child_by_field("parameter")
    if params is None:
        return None
    if params.kind == "identifier":
        return params.text()
    for child in params.children():
        if child.kind == "identifier":
            return child.text()
        pattern = child.child_by_field("pattern")
        if pattern is not None and pattern.kind == "identifier":
            return pattern.text()
    return None


class RegExpInLoopRule(_JsPerfRule):
    id = "CG-PERF-104"
    title = "new RegExp() with a constant pattern inside a loop"
    description = (
        "A regular expression with a constant pattern is compiled on every iteration. "
        "Create it once outside the loop, or use a regex literal."
    )
    severity = Severity.LOW

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in new_expressions(root):
            if callee_text(node) != "RegExp":
                continue
            args = arguments(node)
            if not args or not all(is_literal(a) for a in args):
                continue
            if enclosing_loop(node) is not None:
                findings.append(
                    self._make_finding(
                        node=node,
                        ctx=ctx,
                        fix_suggestion="Hoist it: const PATTERN = /.../; before the loop.",
                    )
                )
        return findings


class ArrayLiteralLookupInLoopRule(_JsPerfRule):
    id = "CG-PERF-105"
    title = "includes() / indexOf() on an array literal inside a loop"
    description = (
        "Searching an array literal compares against every element on every iteration. "
        "A Set created once outside the loop answers with a single hash lookup."
    )
    severity = Severity.LOW
    default_options = {"min_elements": 3}  # noqa: RUF012

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        minimum = int(ctx.option("min_elements", 3))
        findings: list[Finding] = []
        for call in calls(root):
            fn = call.child_by_field("function")
            if fn is None or member_property(fn) not in ("includes", "indexOf"):
                continue
            obj = fn.child_by_field("object")
            if obj is None or obj.kind != "array":
                continue
            elements = [c for c in obj.children() if c.kind not in ("[", "]", ",")]
            if len(elements) < minimum or enclosing_loop(call) is None:
                continue
            findings.append(
                self._make_finding(
                    node=call,
                    ctx=ctx,
                    fix_suggestion=(
                        "const ALLOWED = new Set([...]); outside the loop, then ALLOWED.has(x)."
                    ),
                )
            )
        return findings


for _rule in (
    AwaitInLoopRule(),
    JsonDeepCloneRule(),
    SpreadInReduceRule(),
    RegExpInLoopRule(),
    ArrayLiteralLookupInLoopRule(),
):
    REGISTRY.register(_rule)
