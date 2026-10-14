# SPDX-License-Identifier: Apache-2.0
"""Intraprocedural taint analysis for Python.

The analysis walks each scope (module, function, method) once, statement by
statement, keeping an *environment* that maps variable names to the
:class:`~codeguard.engine.dataflow.model.TaintInfo` they currently carry.

- An assignment from a tainted expression taints its target; an assignment from
  a clean expression clears it.
- ``if`` / ``try`` / ``match`` branches are analysed on copies of the
  environment and merged afterwards (a name tainted on any path stays tainted).
- Loop bodies are analysed twice so taint assigned late in one iteration
  reaches uses early in the next.
- Calls are followed only through the catalog (:mod:`.catalog`): sources
  create taint, sanitizers remove it, propagators and methods on tainted values
  pass it on.  Calls to user-defined functions return clean values -- the
  analysis does not cross function boundaries.

Every expression's taint is recorded (keyed by node identity) so rules can ask
:meth:`PythonDataflow.taint_of` about any sink argument.  An expression
evaluated several times (loops) keeps the first tainted result.
"""

from __future__ import annotations

import ast

from codeguard.rules._pyimports import ImportMap

from ..text import split_lines
from . import catalog
from .model import TaintHop, TaintInfo, TaintSource

Env = dict[str, TaintInfo]


class PythonDataflow:
    """The result of :func:`analyze_python` for one module."""

    def __init__(self, tree: ast.Module, memo: dict[int, TaintInfo]) -> None:
        self._tree = tree  # keeps node ids stable for the lifetime of the result
        self._memo = memo

    def taint_of(self, node: ast.AST) -> TaintInfo | None:
        return self._memo.get(id(node))

    def is_tainted(self, node: ast.AST) -> bool:
        return id(node) in self._memo


def analyze_python(tree: ast.Module, source: str) -> PythonDataflow:
    """Run the taint analysis over *tree* (parsed from *source*)."""
    analyzer = _Analyzer(source, ImportMap.from_tree(tree))
    analyzer.block(tree.body, {})
    return PythonDataflow(tree, analyzer.memo)


def _union_into(target: Env, other: Env) -> None:
    for name, info in other.items():
        target.setdefault(name, info)


class _Analyzer:
    def __init__(self, source: str, imports: ImportMap) -> None:
        self.lines = split_lines(source)
        self.imports = imports
        self.memo: dict[int, TaintInfo] = {}

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def block(self, stmts: list[ast.stmt], env: Env) -> None:
        for stmt in stmts:
            self.stmt(stmt, env)

    def stmt(self, node: ast.stmt, env: Env) -> None:
        if isinstance(node, ast.Assign):
            info = self.expr(node.value, env)
            for target in node.targets:
                self.assign(target, node.value, info, env, node)
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:
                info = self.expr(node.value, env)
                self.assign(node.target, node.value, info, env, node)
        elif isinstance(node, ast.AugAssign):
            info = self.expr(node.value, env) or self.expr(node.target, env)
            self.assign(node.target, None, info, env, node)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            iter_info = self.expr(node.iter, env)
            before = dict(env)
            for _ in range(2):
                self.assign(node.target, None, iter_info, env, node)
                self.block(node.body, env)
                _union_into(env, before)
            self.block(node.orelse, env)
        elif isinstance(node, ast.While):
            before = dict(env)
            for _ in range(2):
                self.expr(node.test, env)
                self.block(node.body, env)
                _union_into(env, before)
            self.block(node.orelse, env)
        elif isinstance(node, ast.If):
            self.expr(node.test, env)
            then_env, else_env = dict(env), dict(env)
            self.block(node.body, then_env)
            self.block(node.orelse, else_env)
            env.clear()
            env.update(then_env)
            _union_into(env, else_env)
        elif isinstance(node, ast.Try) or type(node).__name__ == "TryStar":
            self.try_stmt(node, env)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                info = self.expr(item.context_expr, env)
                if item.optional_vars is not None:
                    self.assign(item.optional_vars, None, info, env, node)
            self.block(node.body, env)
        elif isinstance(node, ast.Match):
            subject = self.expr(node.subject, env)
            merged: Env = {}
            for case in node.cases:
                case_env = dict(env)
                for sub in ast.walk(case.pattern):
                    name = getattr(sub, "name", None)
                    if isinstance(name, str):
                        self.bind(name, subject, case_env, node)
                if case.guard is not None:
                    self.expr(case.guard, case_env)
                self.block(case.body, case_env)
                _union_into(merged, case_env)
            _union_into(merged, env)
            env.clear()
            env.update(merged)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.function(node, env)
        elif isinstance(node, ast.ClassDef):
            for deco in node.decorator_list:
                self.expr(deco, env)
            self.block(node.body, dict(env))
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    env.pop(target.id, None)
        else:
            # Return, Expr, Raise, Assert, ... -- evaluate every expression child.
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self.expr(child, env)

    def try_stmt(self, node: ast.stmt, env: Env) -> None:
        before = dict(env)
        self.block(getattr(node, "body", []), env)
        after_body = dict(env)
        _union_into(after_body, before)
        merged = dict(env)
        for handler in getattr(node, "handlers", []):
            handler_env = dict(after_body)
            if handler.type is not None:
                self.expr(handler.type, handler_env)
            if handler.name:
                handler_env.pop(handler.name, None)
            self.block(handler.body, handler_env)
            _union_into(merged, handler_env)
        self.block(getattr(node, "orelse", []), env)
        _union_into(merged, env)
        env.clear()
        env.update(merged)
        self.block(getattr(node, "finalbody", []), env)

    def function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, env: Env) -> None:
        for deco in node.decorator_list:
            self.expr(deco, env)
        for default in [*node.args.defaults, *node.args.kw_defaults]:
            if default is not None:
                self.expr(default, env)
        fn_env = dict(env)  # closures see the enclosing scope
        handler = _is_handler(node)
        args = node.args
        params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        params += [a for a in (args.vararg, args.kwarg) if a is not None]
        for arg in params:
            fn_env.pop(arg.arg, None)
            if handler and arg.arg not in catalog.HANDLER_NON_DATA_PARAMS:
                fn_env[arg.arg] = TaintInfo(
                    TaintSource(
                        f"route parameter '{arg.arg}'",
                        arg.lineno,
                        arg.col_offset + 1,
                        arg.end_lineno,
                        None if arg.end_col_offset is None else arg.end_col_offset + 1,
                    )
                )
        self.block(node.body, fn_env)

    # ------------------------------------------------------------------
    # Binding
    # ------------------------------------------------------------------

    def hop(self, stmt: ast.AST) -> TaintHop:
        line = getattr(stmt, "lineno", 1)
        text = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        if len(text) > 80:
            text = text[:77] + "..."
        return TaintHop(line, getattr(stmt, "col_offset", 0) + 1, text)

    def bind(self, name: str, info: TaintInfo | None, env: Env, stmt: ast.AST) -> None:
        if info is None:
            env.pop(name, None)
        else:
            env[name] = info.extended(self.hop(stmt))

    def assign(
        self,
        target: ast.expr,
        value: ast.expr | None,
        info: TaintInfo | None,
        env: Env,
        stmt: ast.AST,
    ) -> None:
        if isinstance(target, ast.Name):
            self.bind(target.id, info, env, stmt)
        elif isinstance(target, (ast.Tuple, ast.List)):
            values = (
                value.elts
                if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts)
                else None
            )
            for i, elt in enumerate(target.elts):
                if values is not None:
                    self.assign(elt, values[i], self.expr(values[i], env), env, stmt)
                else:
                    self.assign(elt, None, info, env, stmt)
        elif isinstance(target, ast.Starred):
            self.assign(target.value, None, info, env, stmt)
        elif isinstance(target, (ast.Attribute, ast.Subscript)):
            dotted = _dotted(target)
            if dotted is not None and isinstance(target, ast.Attribute):
                self.bind(dotted, info, env, stmt)
            # Writing tainted data into a container (`d[k] = x`) taints the container.
            root = _root_name(target) if isinstance(target, ast.Subscript) else None
            if root is not None and info is not None:
                self.bind(root, info, env, stmt)
            self.expr(target, env)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def expr(self, node: ast.expr, env: Env) -> TaintInfo | None:
        info = self._eval(node, env)
        if info is not None:
            self.memo.setdefault(id(node), info)
        return info

    def _any(self, nodes: list[ast.expr], env: Env) -> TaintInfo | None:
        found: TaintInfo | None = None
        for n in nodes:
            info = self.expr(n, env)
            if found is None:
                found = info
        return found

    def _eval(self, node: ast.expr, env: Env) -> TaintInfo | None:
        if isinstance(node, ast.Name):
            return env.get(node.id)
        if isinstance(node, ast.Constant):
            return None
        if isinstance(node, ast.Attribute):
            source = self._attribute_source(node)
            if source is not None:
                return source
            dotted = _dotted(node)
            if dotted is not None and dotted in env:
                return env[dotted]
            return self.expr(node.value, env)
        if isinstance(node, ast.Subscript):
            self.expr(node.slice, env)
            return self.expr(node.value, env)
        if isinstance(node, (ast.Starred, ast.Await, ast.FormattedValue)):
            if isinstance(node, ast.FormattedValue) and node.format_spec is not None:
                self.expr(node.format_spec, env)
            return self.expr(node.value, env)
        if isinstance(node, ast.Call):
            return self._call(node, env)
        if isinstance(node, ast.BinOp):
            return self._any([node.left, node.right], env)
        if isinstance(node, ast.JoinedStr):
            return self._any(list(node.values), env)
        if isinstance(node, ast.BoolOp):
            return self._any(list(node.values), env)
        if isinstance(node, ast.IfExp):
            self.expr(node.test, env)
            return self._any([node.body, node.orelse], env)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return self._any(list(node.elts), env)
        if isinstance(node, ast.Dict):
            return self._any([k for k in node.keys if k is not None] + list(node.values), env)
        if isinstance(node, ast.NamedExpr):
            info = self.expr(node.value, env)
            self.bind(node.target.id, info, env, node)
            return info
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            return self._comprehension(node, env)
        if isinstance(node, ast.Lambda):
            lambda_env = dict(env)
            for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                lambda_env.pop(arg.arg, None)
            self.expr(node.body, lambda_env)
            return None
        if isinstance(node, (ast.Compare, ast.UnaryOp)):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self.expr(child, env)
            if isinstance(node, ast.UnaryOp) and not isinstance(node.op, ast.Not):
                return self.expr(node.operand, env)
            return None  # comparisons and `not` yield booleans
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self.expr(child, env)
        return None

    def _comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp, env: Env
    ) -> TaintInfo | None:
        scratch = dict(env)
        for gen in node.generators:
            info = self.expr(gen.iter, scratch)
            self.assign(gen.target, None, info, scratch, node)
            for cond in gen.ifs:
                self.expr(cond, scratch)
        if isinstance(node, ast.DictComp):
            return self._any([node.key, node.value], scratch)
        return self.expr(node.elt, scratch)

    def _call(self, node: ast.Call, env: Env) -> TaintInfo | None:
        arg_nodes: list[ast.expr] = [*node.args, *(kw.value for kw in node.keywords)]
        args_info = self._any(arg_nodes, env)
        name = self._call_name(node.func)

        if name is not None:
            local = catalog.LOCAL_SOURCE_CALLS.get(name)
            if local is not None:
                return self._source(node, local, "local")
            if name.startswith("flask.request.") and (
                name.rsplit(".", 1)[1] in catalog.FLASK_REQUEST_METHODS
            ):
                return self._source(node, f"flask request.{name.rsplit('.', 1)[1]}()", "web")
            if name in catalog.SANITIZERS:
                return None
            if name in catalog.PROPAGATORS:
                return args_info

        func = node.func
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Constant) and isinstance(func.value.value, str):
                return args_info  # "...".format(x), " ".join(xs)
            receiver = self.expr(func.value, env)
            if receiver is not None:
                if func.attr in catalog.NON_PROPAGATING_METHODS:
                    return None
                return receiver
        else:
            self.expr(func, env)
        return None  # unknown callee: the analysis does not follow user functions

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def _source(self, node: ast.AST, label: str, kind: str) -> TaintInfo:
        line = getattr(node, "lineno", 1)
        col = getattr(node, "col_offset", 0) + 1
        end_line = getattr(node, "end_lineno", None)
        end_col = getattr(node, "end_col_offset", None)
        return TaintInfo(
            TaintSource(
                label, line, col, end_line, None if end_col is None else end_col + 1, kind=kind
            )
        )

    def _canonical(self, dotted: str) -> str:
        head, _, rest = dotted.partition(".")
        if head in self.imports.symbol_imports:
            module, attr = self.imports.symbol_imports[head]
            head = f"{module}.{attr}"
        elif head in self.imports.module_aliases:
            head = self.imports.module_aliases[head]
        return f"{head}.{rest}" if rest else head

    def _call_name(self, func: ast.expr) -> str | None:
        dotted = _dotted(func)
        if dotted is None:
            return None
        return self._canonical(dotted)

    def _attribute_source(self, node: ast.Attribute) -> TaintInfo | None:
        dotted = _dotted(node)
        if dotted is None:
            return None
        canonical = self._canonical(dotted)
        local = catalog.LOCAL_SOURCE_CHAINS.get(canonical)
        if local is not None:
            return self._source(node, local, "local")
        parts = canonical.split(".")
        if (
            parts[:2] == ["flask", "request"]
            and len(parts) == 3
            and parts[2] in catalog.FLASK_REQUEST_ATTRS
        ):
            return self._source(node, f"flask request.{parts[2]}", "web")
        # Django / DRF / Starlette: `request.GET`, `self.request.data`, ...  Checked on
        # the written name, because a `request` parameter shadows any import.
        head = dotted.split(".")
        if head[0] == "self":
            head = head[1:]
        if (
            len(head) == 2
            and head[0] in catalog.REQUEST_NAMES
            and head[1] in catalog.REQUEST_OBJECT_ATTRS
        ):
            return self._source(node, f"request.{head[1]}", "web")
        return None


def _dotted(node: ast.expr) -> str | None:
    """``"a.b.c"`` for a pure Name/Attribute chain, else ``None``."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Subscript, ast.Starred)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _is_handler(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for deco in node.decorator_list:
        target = deco.func if isinstance(deco, ast.Call) else deco
        name = (
            target.attr
            if isinstance(target, ast.Attribute)
            else target.id
            if isinstance(target, ast.Name)
            else None
        )
        if name is None:
            continue
        if name in catalog.HANDLER_DECORATORS or name.endswith("_route"):
            # `@property`-style bare names other than api_view are not handlers.
            if isinstance(target, ast.Name) and name != "api_view" and not name.endswith("_route"):
                continue
            return True
    return False
