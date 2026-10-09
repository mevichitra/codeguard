# SPDX-License-Identifier: Apache-2.0
"""Python code-quality rules (CG-QUAL-0xx)."""

from __future__ import annotations

import ast

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Location, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.rules import _pycomplexity

_MUTABLE_CALLS = frozenset({"list", "dict", "set", "bytearray", "defaultdict", "OrderedDict"})


class MutableDefaultRule(AstRule):
    id = "CG-QUAL-001"
    title = "Mutable default argument"
    description = (
        "A default value is created once, when the function is defined, and shared by "
        "every call. Mutating it in one call leaks state into the next."
    )
    severity = Severity.MEDIUM
    category = Category.QUALITY

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        findings: list[Finding] = []
        for fn in _pycomplexity.functions(tree):
            defaults = [*fn.args.defaults, *(d for d in fn.args.kw_defaults if d is not None)]
            for default in defaults:
                if _is_mutable(default):
                    findings.append(
                        self._make_finding(
                            node=default,
                            filename=filename,
                            fix_suggestion=(
                                "Default to None and create the value inside: "
                                "def f(items=None): items = [] if items is None else items"
                            ),
                        )
                    )
        return findings


def _is_mutable(node: ast.expr) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    if isinstance(node, ast.Call) and not node.args and not node.keywords:
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        return name in _MUTABLE_CALLS
    return False


class SwallowedExceptionRule(AstRule):
    id = "CG-QUAL-002"
    title = "Exception silently swallowed"
    description = (
        "A bare `except:` or `except Exception:` whose body is only `pass` hides every "
        "error, including bugs, and makes failures impossible to diagnose. A bare "
        "`except:` also catches KeyboardInterrupt and SystemExit."
    )
    severity = Severity.LOW
    category = Category.QUALITY

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            broad = node.type is None or (
                isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException")
            )
            if broad and all(_is_noop(stmt) for stmt in node.body):
                findings.append(
                    self._make_finding(
                        node=node,
                        filename=filename,
                        fix_suggestion=(
                            "Catch the specific exception you expect, and log or re-raise "
                            "anything else: except ValueError: logger.warning(...)."
                        ),
                    )
                )
        return findings


def _is_noop(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Pass) or (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is Ellipsis
    )


def _def_location(fn: _pycomplexity.FunctionNode, filename: str) -> Location:
    """Highlight just ``def name`` rather than the whole function body."""
    keyword = "async def " if isinstance(fn, ast.AsyncFunctionDef) else "def "
    col = fn.col_offset + 1
    return Location(filename, fn.lineno, col, fn.lineno, col + len(keyword) + len(fn.name))


class _MetricRule(AstRule):
    category = Category.QUALITY
    option_name: str
    metric_label: str

    def measure(self, fn: _pycomplexity.FunctionNode) -> int:
        raise NotImplementedError

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        limit = int(ctx.option(self.option_name, self.default_options[self.option_name]))
        return self._check(ctx.python_ast, ctx.filename, limit)

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        return self._check(tree, filename, int(self.default_options[self.option_name]))  # type: ignore[call-overload]

    def _check(self, tree: ast.AST, filename: str, limit: int) -> list[Finding]:
        findings: list[Finding] = []
        for fn in _pycomplexity.functions(tree):
            value = self.measure(fn)
            if value <= limit:
                continue
            findings.append(
                Finding(
                    rule_id=self.id,
                    title=self.title,
                    description=(
                        f"{fn.name}() has {self.metric_label} {value} (limit {limit}). "
                        f"{self.description}"
                    ),
                    severity=self.severity,
                    category=self.category,
                    location=_def_location(fn, filename),
                    fix_suggestion=self.fix_text,
                )
            )
        return findings

    fix_text = ""


class ComplexityRule(_MetricRule):
    id = "CG-QUAL-003"
    title = "Function is too complex"
    description = (
        "High cyclomatic complexity means many paths through the code: harder to test, "
        "review, and change safely."
    )
    severity = Severity.LOW
    default_options = {"max_complexity": 15}  # noqa: RUF012
    option_name = "max_complexity"
    metric_label = "cyclomatic complexity"
    fix_text = "Extract branches into well-named helper functions, or use a dispatch table."

    def measure(self, fn: _pycomplexity.FunctionNode) -> int:
        return _pycomplexity.cyclomatic(fn)


class NestingRule(_MetricRule):
    id = "CG-QUAL-004"
    title = "Code is nested too deeply"
    description = "Deeply nested blocks are hard to follow and usually hide a missing abstraction."
    severity = Severity.LOW
    default_options = {"max_depth": 5}  # noqa: RUF012
    option_name = "max_depth"
    metric_label = "nesting depth"
    fix_text = "Return early (guard clauses) and extract inner blocks into helper functions."

    def measure(self, fn: _pycomplexity.FunctionNode) -> int:
        return _pycomplexity.max_nesting(fn)


class TooManyParamsRule(_MetricRule):
    id = "CG-QUAL-005"
    title = "Function takes too many parameters"
    description = (
        "Long parameter lists are easy to call wrongly and suggest the function does too much."
    )
    severity = Severity.INFO
    default_options = {"max_params": 8}  # noqa: RUF012
    option_name = "max_params"
    metric_label = "parameter count"
    fix_text = "Group related parameters into a dataclass, or split the function."

    def measure(self, fn: _pycomplexity.FunctionNode) -> int:
        return _pycomplexity.param_count(fn)


for _rule in (
    MutableDefaultRule(),
    SwallowedExceptionRule(),
    ComplexityRule(),
    NestingRule(),
    TooManyParamsRule(),
):
    REGISTRY.register(_rule)
