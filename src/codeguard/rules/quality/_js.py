# SPDX-License-Identifier: Apache-2.0
"""JavaScript / TypeScript code-quality rules (CG-QUAL-1xx)."""

from __future__ import annotations

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Fix, Location, Severity
from codeguard.engine.fixes import edit_for_source_node
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules import _jscomplexity
from codeguard.rules._jsnodes import callee_text, member_property

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_NULLISH = frozenset({"null", "undefined"})
_LITERAL_KINDS = {
    "string": "string",
    "template_string": "string",
    "number": "number",
    "true": "boolean",
    "false": "boolean",
}
_NUMBER_MEMBERS = frozenset({"length", "size"})
_NUMBER_METHODS = frozenset({"indexOf", "lastIndexOf", "findIndex", "findLastIndex", "charCodeAt"})
_STRING_METHODS = frozenset({"toString", "toLowerCase", "toUpperCase", "trim", "charAt", "join"})
_CONVERTERS = {
    "String": "string",
    "Number": "number",
    "Boolean": "boolean",
    "parseInt": "number",
    "parseFloat": "number",
}


class _JsQualRule(TreeSitterRule):
    category = Category.QUALITY
    languages = _JS_TS


class LooseEqualityRule(_JsQualRule):
    id = "CG-QUAL-101"
    title = "Loose equality (== / !=)"
    description = (
        "== and != convert types before comparing ('' == 0 and '0' == false are both "
        "true). Strict === and !== compare without conversion."
    )
    severity = Severity.LOW
    autofix = True

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in root.walk():
            if node.kind != "binary_expression":
                continue
            op = node.child_by_field("operator")
            if op is None or op.text() not in ("==", "!="):
                continue
            left, right = node.child_by_field("left"), node.child_by_field("right")
            if left is None or right is None:
                continue
            if left.text() in _NULLISH or right.text() in _NULLISH:
                continue  # `x == null` is the idiomatic null-or-undefined check
            strict = op.text() + "="
            fix = None
            if _type_stable(left, right):
                fix = Fix(f"Use {strict}", (edit_for_source_node(op, strict),))
            findings.append(
                self._make_finding(
                    node=node,
                    ctx=ctx,
                    fix_suggestion=f"Use {strict} (convert explicitly first if needed).",
                    fix=fix,
                )
            )
        return findings


def _static_type(node: SourceNode) -> str | None:
    """The type a node always has, when that is evident from syntax alone."""
    kind = node.kind
    if kind == "parenthesized_expression":
        inner = [c for c in node.children() if c.kind not in ("(", ")")]
        return _static_type(inner[0]) if len(inner) == 1 else None
    if kind in _LITERAL_KINDS:
        if kind == "template_string" and any(
            d.kind == "template_substitution" for d in node.walk()
        ):
            return "string"
        return _LITERAL_KINDS[kind]
    if kind == "unary_expression" and node.text().startswith("typeof"):
        return "string"
    if kind == "member_expression" and member_property(node) in _NUMBER_MEMBERS:
        return "number"
    if kind == "call_expression":
        callee = callee_text(node)
        method = callee.rsplit(".", 1)[-1]
        if callee in _CONVERTERS:
            return _CONVERTERS[callee]
        if "." in callee and method in _NUMBER_METHODS:
            return "number"
        if "." in callee and method in _STRING_METHODS:
            return "string"
    return None


def _type_stable(left: SourceNode, right: SourceNode) -> bool:
    """Both sides have the same evident type, so == and === give the same result.

    One side must be a literal; `.length == 0` qualifies, `x == 0` does not.
    """
    if left.kind not in _LITERAL_KINDS and right.kind not in _LITERAL_KINDS:
        return False
    lt, rt = _static_type(left), _static_type(right)
    return lt is not None and lt == rt


class EmptyCatchRule(_JsQualRule):
    id = "CG-QUAL-102"
    title = "Empty catch block"
    description = (
        "An empty catch block discards the error. Failures become silent and very hard to diagnose."
    )
    severity = Severity.LOW

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for node in root.walk():
            if node.kind != "catch_clause":
                continue
            body = node.child_by_field("body")
            if body is None:
                continue
            inner = [c for c in body.children() if c.kind not in ("{", "}")]
            if not inner:  # a comment counts as an explanation
                findings.append(
                    self._make_finding(
                        node=node,
                        ctx=ctx,
                        fix_suggestion=(
                            "Handle the error, log it, or leave a comment explaining why "
                            "it is safe to ignore."
                        ),
                    )
                )
        return findings


class JsComplexityRule(_JsQualRule):
    id = "CG-QUAL-103"
    title = "Function is too complex"
    description = (
        "High cyclomatic complexity means many paths through the code: harder to test, "
        "review, and change safely."
    )
    severity = Severity.LOW
    default_options = {"max_complexity": 15}  # noqa: RUF012

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        limit = int(ctx.option("max_complexity", 15))
        findings: list[Finding] = []
        for fn in _jscomplexity.functions(root):
            score = _jscomplexity.cyclomatic(fn)
            if score <= limit:
                continue
            name = _jscomplexity.function_name(fn)
            start = fn.start
            name_node = fn.child_by_field("name")
            end = name_node.end if name_node is not None and name_node.end else None
            findings.append(
                Finding(
                    rule_id=self.id,
                    title=self.title,
                    description=(
                        f"{name}() has cyclomatic complexity {score} (limit {limit}). "
                        f"{self.description}"
                    ),
                    severity=self.severity,
                    category=self.category,
                    location=Location(
                        ctx.filename,
                        start.line,
                        start.col,
                        end.line if end else start.line,
                        end.col if end else start.col + 1,
                    ),
                    fix_suggestion=(
                        "Extract branches into well-named helper functions, or use a lookup "
                        "object instead of long if/else chains."
                    ),
                )
            )
        return findings


class VarDeclarationRule(_JsQualRule):
    id = "CG-QUAL-104"
    title = "var declaration"
    description = (
        "var is function-scoped and hoisted, so a variable is visible (as undefined) "
        "before its declaration and leaks out of blocks and loops."
    )
    severity = Severity.INFO

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        return [
            self._make_finding(
                node=node,
                ctx=ctx,
                fix_suggestion="Use const, or let if the variable is reassigned.",
            )
            for node in root.walk()
            if node.kind == "variable_declaration"
        ]


for _rule in (LooseEqualityRule(), EmptyCatchRule(), JsComplexityRule(), VarDeclarationRule()):
    REGISTRY.register(_rule)
