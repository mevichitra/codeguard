"""Source transformations with exact line maps, for the controlled experiment (RQ2).

Each transformation rewrites one Python file around one finding (the *target*, given by
its line) and returns the new text plus a map from old lines to new lines. The map is
the ground truth by construction: a finding on old line ``l`` is the same finding as one
with the same rule on new line ``line_map[l]``. Lines that the transformation deletes or
rewrites beyond recognition are absent from the map.

| Transformation    | What it does                                                        |
|-------------------|---------------------------------------------------------------------|
| reformat          | runs ``black`` (or ``ruff format``) at a narrower line length       |
| insert_top        | inserts a comment and an import below the docstring and imports     |
| insert_below      | inserts a comment line right below the flagged statement            |
| rename_local      | renames a local variable used on the flagged line                   |
| rename_function   | renames the enclosing function or method and its call sites         |
| move_function     | swaps the enclosing function with an adjacent function              |
| change_literal    | changes a string or number literal on the flagged line              |
| extract_helper    | moves the flagged statement into a new module-level helper function |
| duplicate_above   | copies the flagged statement directly above itself (a new finding)  |
| duplicate_below   | copies the flagged statement directly below itself (a new finding)  |
| ai_refactor       | asks a language model to refactor the enclosing function (optional) |

All but ``change_literal``, the two ``duplicate`` transformations and ``ai_refactor``
preserve the behaviour of the file itself; renames do not update other modules. A
transformation raises :class:`NotApplicable` when the target does not fit it (for
example, a finding at module level has no enclosing function to rename).
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import io
import json
import re
import subprocess
import textwrap
import tokenize
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Protocol

import libcst as cst
from libcst.metadata import (
    Assignment,
    ClassScope,
    CodeRange,
    FunctionScope,
    MetadataWrapper,
    PositionProvider,
    Scope,
    ScopeProvider,
)

from .linemap import map_lines
from .schemes import split_lines

DETERMINISTIC = (
    "reformat",
    "insert_top",
    "insert_below",
    "rename_local",
    "rename_function",
    "move_function",
    "change_literal",
    "extract_helper",
    "duplicate_above",
    "duplicate_below",
)
ALL_TRANSFORMS = (*DETERMINISTIC, "ai_refactor")

#: Text the insertions add. Comments and an unused import keep the file's behaviour.
TOP_LINES = (
    "# Added by the finding-identity experiment.",
    "import collections as _fi_collections  # noqa: F401",
)
BELOW_LINE = "# Reviewed: no behaviour change."


class NotApplicable(Exception):  # noqa: N818  (not an error: a skipped case)
    """The transformation does not fit this target (the reason is the message)."""


@dataclass
class Edit:
    """The result of one transformation."""

    text: str
    #: ``{old line: new line}`` for every line the transformation keeps (1-based).
    line_map: dict[int, int]
    #: Reformatting can split one old line over several new lines; the syntax nodes that
    #: started on the old line start on these new lines (first entry = ``line_map``).
    alternatives: dict[int, tuple[int, ...]] = field(default_factory=dict)
    #: The ground truth is a line diff, not a construction: check these by hand.
    needs_review: bool = False
    #: Material for the manual check (old and new code).
    review: dict[str, str] = field(default_factory=dict)


class Transform(Protocol):
    def __call__(self, src: Source, line: int) -> Edit: ...


# ---------------------------------------------------------------------------
# Source file with lazily computed views
# ---------------------------------------------------------------------------

_LINE_RE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")
_FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def split_keepends(text: str) -> list[str]:
    """Lines with their endings, split on LF, CRLF and CR only (as the parser counts)."""
    return _LINE_RE.findall(text)


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


class Source:
    """One version of one Python file. Raises ``SyntaxError`` if it does not parse."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.lines = split_keepends(text)
        self.tree = ast.parse(text)
        self.newline = "\r\n" if "\r\n" in text else "\n"
        #: Results that do not depend on the target, keyed by transformation.
        self.memo: dict[str, Edit | NotApplicable] = {}

    def line(self, n: int) -> str:
        """Line *n* (1-based) without its ending."""
        return self.lines[n - 1].rstrip("\r\n") if 1 <= n <= len(self.lines) else ""

    @cached_property
    def parents(self) -> dict[ast.AST, ast.AST]:
        return {c: p for p in ast.walk(self.tree) for c in ast.iter_child_nodes(p)}

    @cached_property
    def statements(self) -> list[ast.stmt]:
        return [n for n in ast.walk(self.tree) if isinstance(n, ast.stmt)]

    @cached_property
    def _cst(self) -> tuple[MetadataWrapper, Mapping[cst.CSTNode, Scope | None]] | None:
        try:
            wrapper = MetadataWrapper(cst.parse_module(self.text))
            return wrapper, wrapper.resolve(ScopeProvider)
        except Exception:  # libcst raises parser errors and recursion errors
            return None

    @property
    def wrapper(self) -> MetadataWrapper:
        if self._cst is None:
            raise NotApplicable("libcst cannot parse the file")
        return self._cst[0]

    @property
    def scopes(self) -> Mapping[cst.CSTNode, Scope | None]:
        if self._cst is None:
            raise NotApplicable("libcst cannot parse the file")
        return self._cst[1]

    @cached_property
    def positions(self) -> Mapping[cst.CSTNode, CodeRange]:
        return self.wrapper.resolve(PositionProvider)

    @cached_property
    def cst_by_line(self) -> dict[int, list[cst.CSTNode]]:
        """CST names, literals and function definitions by start line, in column order."""
        out: dict[int, list[tuple[int, cst.CSTNode]]] = {}
        kinds = (cst.Name, cst.SimpleString, cst.Integer, cst.Float, cst.FunctionDef)
        for node, pos in self.positions.items():
            if isinstance(node, cst.FunctionDef):
                pos = self.positions[node.name]
            if isinstance(node, kinds):
                out.setdefault(pos.start.line, []).append((pos.start.column, node))
        return {k: [n for _, n in sorted(v, key=lambda t: t[0])] for k, v in out.items()}

    # -- syntax helpers ------------------------------------------------------

    def enclosing_function(self, line: int) -> ast.FunctionDef | ast.AsyncFunctionDef:
        """Innermost function whose ``def`` line to last line contains *line*."""
        best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        for node in ast.walk(self.tree):
            if isinstance(node, _FUNC_NODES) and node.lineno <= line <= _end(node):
                if best is None or node.lineno >= best.lineno:
                    best = node
        if best is None:
            raise NotApplicable("finding is not inside a function")
        return best

    def ancestors(self, node: ast.AST) -> list[ast.AST]:
        out = []
        while node in self.parents:
            node = self.parents[node]
            out.append(node)
        return out

    def simple_statement(self, line: int) -> ast.stmt:
        """The innermost statement containing *line*; it must be a simple statement that
        occupies whole lines on its own (no ``;`` neighbours, no ``if x: stmt``)."""
        containing = [s for s in self.statements if s.lineno <= line <= _end(s)]
        if not containing:
            raise NotApplicable("no statement on the flagged line")
        stmt = max(containing, key=lambda s: (s.lineno, -_end(s)))
        if hasattr(stmt, "body"):
            raise NotApplicable("flagged line is a compound statement header")
        if self._prefix(stmt.lineno, stmt.col_offset).strip():
            raise NotApplicable("statement shares its first line")
        family = set(self.ancestors(stmt)) | {stmt}
        for other in self.statements:
            if other not in family and other.lineno <= _end(stmt) and _end(other) >= stmt.lineno:
                raise NotApplicable("statement shares a line with another statement")
        return stmt

    def _prefix(self, line: int, col: int) -> str:
        """Text of *line* before byte column *col* (ast columns are UTF-8 offsets)."""
        return self.line(line).encode("utf-8")[:col].decode("utf-8", "replace")


def _end(node: ast.AST) -> int:
    end = getattr(node, "end_lineno", None)
    return int(end) if end is not None else int(getattr(node, "lineno", 0))


def _start(node: ast.stmt) -> int:
    """First line of a statement, including its decorators."""
    decorators: list[ast.expr] = getattr(node, "decorator_list", [])
    return min([node.lineno, *(d.lineno for d in decorators)])


# ---------------------------------------------------------------------------
# Line-splicing helpers
# ---------------------------------------------------------------------------


def _terminated(lines: list[str], newline: str) -> list[str]:
    out = list(lines)
    if out and not out[-1].endswith(("\n", "\r")):
        out[-1] += newline
    return out


def _insert(src: Source, before: int, block: list[str]) -> Edit:
    """Insert *block* (lines without endings) before old line *before* (1-based)."""
    lines = _terminated(src.lines, src.newline)
    new = lines[: before - 1] + [b + src.newline for b in block] + lines[before - 1 :]
    n = len(block)
    line_map = {k: k if k < before else k + n for k in range(1, len(lines) + 1)}
    return Edit("".join(new), line_map)


def _identity(src: Source, new_text: str) -> Edit:
    if len(split_keepends(new_text)) != len(src.lines):
        raise NotApplicable("rewrite changed the number of lines")
    return Edit(new_text, {k: k for k in range(1, len(src.lines) + 1)})


def _unique_name(src: Source, base: str) -> str:
    name, k = base, 2
    while re.search(rf"\b{re.escape(name)}\b", src.text):
        name, k = f"{base}{k}", k + 1
    return name


# ---------------------------------------------------------------------------
# reformat
# ---------------------------------------------------------------------------


def _format(text: str, line_length: int) -> str:
    try:
        black: Any = importlib.import_module("black")
    except ImportError:
        proc = subprocess.run(
            ["ruff", "format", "--isolated", f"--line-length={line_length}", "-"],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if proc.returncode:
            raise NotApplicable("formatter failed") from None
        return proc.stdout.decode("utf-8")
    try:
        return str(black.format_str(text, mode=black.Mode(line_length=line_length)))
    except Exception as exc:  # black raises several unrelated exception types
        raise NotApplicable(f"formatter failed: {type(exc).__name__}") from exc


def node_line_map(old: ast.AST, new: ast.AST) -> dict[int, tuple[int, ...]]:
    """Pair the syntax nodes of two equivalent trees and map each old line on which
    nodes start to the new lines where the same nodes start (outermost first)."""
    old_nodes = [n for n in ast.walk(old) if hasattr(n, "lineno")]
    new_nodes = [n for n in ast.walk(new) if hasattr(n, "lineno")]
    if len(old_nodes) != len(new_nodes) or any(
        type(a) is not type(b) for a, b in zip(old_nodes, new_nodes, strict=True)
    ):
        raise NotApplicable("reformatting changed the syntax tree")
    out: dict[int, list[int]] = {}
    for a, b in zip(old_nodes, new_nodes, strict=True):
        targets = out.setdefault(a.lineno, [])
        if b.lineno not in targets:
            targets.append(b.lineno)
    return {k: tuple(v) for k, v in out.items()}


def _reformat(src: Source, line_length: int) -> Edit:
    new_text = _format(src.text, line_length)
    if new_text == src.text:
        raise NotApplicable("already formatted")
    alternatives = node_line_map(src.tree, ast.parse(new_text))
    return Edit(
        new_text,
        {k: v[0] for k, v in alternatives.items()},
        {k: v for k, v in alternatives.items() if len(v) > 1},
    )


def make_reformat(line_length: int = 79) -> Transform:
    """Reformat the whole file. Projects already formatted at 88 columns still change
    at the default of 79 (the PEP 8 limit)."""

    def reformat(src: Source, line: int) -> Edit:
        key = f"reformat:{line_length}"
        if key not in src.memo:
            try:
                src.memo[key] = _reformat(src, line_length)
            except NotApplicable as exc:
                src.memo[key] = exc
        result = src.memo[key]
        if isinstance(result, NotApplicable):
            raise result
        return result

    return reformat


# ---------------------------------------------------------------------------
# insert_top, insert_below
# ---------------------------------------------------------------------------

_MAGIC_COMMENT = re.compile(r"^#!|^#.*coding[:=]")


def insert_top(src: Source, line: int) -> Edit:
    """Insert a comment and an import at the top, after the module docstring and the
    ``from __future__`` imports (or after a shebang or encoding line)."""
    body, last, i = src.tree.body, 0, 0
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        last, i = _end(body[0]), 1
    while i < len(body):
        node = body[i]
        if not (isinstance(node, ast.ImportFrom) and node.module == "__future__"):
            break
        last, i = _end(node), i + 1
    if last == 0:
        while last < min(2, len(src.lines)) and _MAGIC_COMMENT.match(src.line(last + 1)):
            last += 1
    return _insert(src, last + 1, list(TOP_LINES))


def _logical_line_end(src: Source, line: int) -> int:
    """Last physical line of the logical line that contains *line*."""
    text = src.text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.NEWLINE and tok.start[0] >= line:
                return tok.start[0]
    except (tokenize.TokenError, SyntaxError) as exc:
        raise NotApplicable("tokenizer failed") from exc
    return len(src.lines)


def insert_below(src: Source, line: int) -> Edit:
    """Insert a comment line right below the flagged statement (its logical line). This
    changes the text GitHub's line hash reads (100 characters forward)."""
    end = _logical_line_end(src, line)
    containing = [s for s in src.statements if s.lineno <= line <= _end(s)]
    first = max((s.lineno for s in containing), default=line)
    indent = _indent(src.line(first))
    for k in range(end + 1, len(src.lines) + 1):
        if src.line(k).strip():
            if len(_indent(src.line(k))) > len(indent):
                indent = _indent(src.line(k))
            break
    return _insert(src, end + 1, [indent + BELOW_LINE])


# ---------------------------------------------------------------------------
# rename_local, rename_function, change_literal (libcst, source preserving)
# ---------------------------------------------------------------------------


class _Rewriter(cst.CSTTransformer):
    """Give new ``value`` text to names and literals, chosen by node identity."""

    def __init__(self, values: dict[int, str]) -> None:
        super().__init__()
        self._values = values

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:  # noqa: N802
        value = self._values.get(id(original_node))
        return updated_node if value is None else updated_node.with_changes(value=value)

    def leave_SimpleString(  # noqa: N802
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.BaseExpression:
        value = self._values.get(id(original_node))
        return updated_node if value is None else updated_node.with_changes(value=value)

    def leave_Integer(  # noqa: N802
        self, original_node: cst.Integer, updated_node: cst.Integer
    ) -> cst.BaseExpression:
        value = self._values.get(id(original_node))
        return updated_node if value is None else updated_node.with_changes(value=value)

    def leave_Float(  # noqa: N802
        self, original_node: cst.Float, updated_node: cst.Float
    ) -> cst.BaseExpression:
        value = self._values.get(id(original_node))
        return updated_node if value is None else updated_node.with_changes(value=value)


def _rewrite(src: Source, values: dict[int, str]) -> Edit:
    return _identity(src, src.wrapper.module.visit(_Rewriter(values)).code)


def _function_text(src: Source, func: ast.AST) -> str:
    return "".join(src.lines[getattr(func, "lineno", 1) - 1 : _end(func)])


def rename_local(src: Source, line: int) -> Edit:
    """Rename a local variable (not a parameter) used on the flagged line, everywhere in
    its function, including nested functions that read it."""
    func = src.enclosing_function(line)
    if re.search(r"\b(locals|vars)\(\)|\bnonlocal\b|\bglobal\b", _function_text(src, func)):
        raise NotApplicable("function inspects or rebinds its namespace")
    for node in src.cst_by_line.get(line, []):
        if not isinstance(node, cst.Name):
            continue
        scope = src.scopes.get(node)
        if not isinstance(scope, FunctionScope):
            continue
        assignments = list(scope.assignments[node.value])
        if not assignments or not all(
            isinstance(a, Assignment) and isinstance(a.node, cst.Name) for a in assignments
        ):
            continue  # not local, or bound by a parameter, import, def or class
        targets: list[cst.CSTNode] = []
        for a in assignments:
            assert isinstance(a, Assignment)
            targets.append(a.node)
            targets.extend(r.node for r in a.references if isinstance(r.node, cst.Name))
        new = _unique_name(src, f"{node.value}_v2")
        return _rewrite(src, {id(t): new for t in targets})
    raise NotApplicable("no local variable on the flagged line")


def _cst_function(src: Source, func: ast.FunctionDef | ast.AsyncFunctionDef) -> cst.FunctionDef:
    for node in src.cst_by_line.get(func.lineno, []):
        if isinstance(node, cst.FunctionDef) and node.name.value == func.name:
            return node
    raise NotApplicable("function not found in the CST")


def rename_function(src: Source, line: int) -> Edit:
    """Rename the enclosing function or method and its references in the file: names
    bound to a function, and ``self.m``, ``cls.m`` and ``Class.m`` for a method."""
    func = src.enclosing_function(line)
    name = func.name
    if name.startswith("__") and name.endswith("__"):
        raise NotApplicable("special method")
    fdef = _cst_function(src, func)
    scope = src.scopes.get(fdef)
    new = _unique_name(src, f"{name}_renamed")
    if isinstance(scope, ClassScope):
        same_name = [n for n in ast.walk(src.tree) if isinstance(n, _FUNC_NODES) and n.name == name]
        if len(same_name) > 1:
            raise NotApplicable("method name defined more than once (override or property)")
        cls = src.parents.get(func)
        assert isinstance(cls, ast.ClassDef)
        owners = {"self", "cls", cls.name}
        targets: list[cst.CSTNode] = [fdef.name]
        for node in src.positions:
            if (
                isinstance(node, cst.Attribute)
                and node.attr.value == name
                and isinstance(node.value, cst.Name)
                and node.value.value in owners
            ):
                targets.append(node.attr)
        return _rewrite(src, {id(t): new for t in targets})
    if scope is None:
        raise NotApplicable("no scope for the function")
    assignments = list(scope.assignments[name])
    only = assignments[0] if len(assignments) == 1 else None
    if not isinstance(only, Assignment) or only.node is not fdef:
        raise NotApplicable("function name is bound more than once")
    targets = [fdef.name, *(r.node for r in only.references if isinstance(r.node, cst.Name))]
    return _rewrite(src, {id(t): new for t in targets})


_FLOAT_RE = re.compile(r"\d+\.\d*|\.\d+")


def _changed_literal(node: cst.CSTNode) -> str | None:
    if isinstance(node, cst.SimpleString):
        prefix, quote = node.prefix, node.quote
        inner = node.value[len(prefix) + len(quote) : -len(quote)]
        return f"{prefix}{quote}{inner}_v2{quote}"
    if isinstance(node, cst.Integer) and node.value.isdigit():
        return str(int(node.value) + 1)
    if isinstance(node, cst.Float) and _FLOAT_RE.fullmatch(node.value):
        return repr(float(node.value) + 1)
    return None


def change_literal(src: Source, line: int) -> Edit:
    """Change the first string literal on the flagged line (append ``_v2``), or else the
    first number literal (add one). Literals spanning several lines are left alone."""
    nodes = src.cst_by_line.get(line, [])
    strings = [n for n in nodes if isinstance(n, cst.SimpleString)]
    numbers = [n for n in nodes if isinstance(n, cst.Integer | cst.Float)]
    for node in strings + numbers:
        if src.positions[node].end.line != line:
            continue
        changed = _changed_literal(node)
        if changed is not None:
            return _rewrite(src, {id(node): changed})
    raise NotApplicable("no literal on the flagged line")


# ---------------------------------------------------------------------------
# move_function
# ---------------------------------------------------------------------------


def _definition_deps(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Names a ``def`` evaluates when it runs: decorators, defaults and annotations."""
    parts: list[ast.AST] = [*node.decorator_list, *node.args.defaults]
    parts += [d for d in node.args.kw_defaults if d is not None]
    args = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
    args += [a for a in (node.args.vararg, node.args.kwarg) if a is not None]
    parts += [a.annotation for a in args if a.annotation is not None]
    if node.returns is not None:
        parts.append(node.returns)
    return {n.id for p in parts for n in ast.walk(p) if isinstance(n, ast.Name)}


def _block(src: Source, node: ast.stmt, floor: int) -> tuple[int, int]:
    """Lines of a definition with its decorators and the comments right above it."""
    start = _start(node)
    while start - 1 > floor and src.line(start - 1).lstrip().startswith("#"):
        start -= 1
    return start, _end(node)


def move_function(src: Source, line: int) -> Edit:
    """Swap the enclosing function with the function defined right before it (or, if
    that is not safe, right after it) in the same body. Comments directly above a
    definition move with it."""
    func = src.enclosing_function(line)
    parent = src.parents.get(func)
    body = next(
        (
            b
            for b in (getattr(parent, f, None) for f in ("body", "orelse", "finalbody"))
            if isinstance(b, list) and func in b
        ),
        None,
    )
    if body is None:
        raise NotApplicable("function body not found")
    # Comments right after a class or def header belong to the body, not to the header.
    floor = 0 if isinstance(parent, ast.Module) else getattr(parent, "lineno", 0)
    i = body.index(func)
    for j in (i - 1, i + 1):
        if not 0 <= j < len(body):
            continue
        a, b = (body[j], func) if j < i else (func, body[j])
        if not (isinstance(a, _FUNC_NODES) and isinstance(b, _FUNC_NODES)):
            continue
        if a.name == b.name or a.name in _definition_deps(b) or b.name in _definition_deps(a):
            continue
        k = body.index(a)
        a0, a1 = _block(src, a, _end(body[k - 1]) if k > 0 else floor)
        b0, b1 = _block(src, b, a1)
        return _swap(src, (a0, a1), (b0, b1))
    raise NotApplicable("no adjacent function to swap with")


def _swap(src: Source, a: tuple[int, int], b: tuple[int, int]) -> Edit:
    (a0, a1), (b0, b1) = a, b
    lines = _terminated(src.lines, src.newline)
    block_a, gap, block_b = lines[a0 - 1 : a1], lines[a1 : b0 - 1], lines[b0 - 1 : b1]
    new = lines[: a0 - 1] + block_b + gap + block_a + lines[b1:]
    nb, ng = len(block_b), len(gap)
    line_map: dict[int, int] = {}
    for k in range(1, len(lines) + 1):
        if a0 <= k <= a1:
            line_map[k] = a0 + nb + ng + (k - a0)
        elif a1 < k < b0:
            line_map[k] = a0 + nb + (k - a1 - 1)
        elif b0 <= k <= b1:
            line_map[k] = a0 + (k - b0)
        else:
            line_map[k] = k
    return Edit("".join(new), line_map)


# ---------------------------------------------------------------------------
# extract_helper, duplicate
# ---------------------------------------------------------------------------

_EXTRACTABLE = (
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.Expr,
    ast.Return,
    ast.Raise,
    ast.Assert,
)
_NESTED_SCOPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def _function_locals(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    a = func.args
    names = {x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs]}
    names |= {x.arg for x in (a.vararg, a.kwarg) if x is not None}
    todo: list[ast.AST] = list(func.body)
    while todo:
        node = todo.pop()
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
            names.add(node.id)
        elif isinstance(node, ast.alias):
            names.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        if not isinstance(node, _NESTED_SCOPES):
            todo.extend(ast.iter_child_nodes(node))
    return names


def _nested_bound(stmt: ast.stmt) -> set[str]:
    """Names bound by lambdas and comprehensions inside *stmt*."""
    out: set[str] = set()
    for node in ast.walk(stmt):
        if isinstance(node, ast.Lambda):
            a = node.args
            out |= {x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs]}
            out |= {x.arg for x in (a.vararg, a.kwarg) if x is not None}
        elif isinstance(node, ast.comprehension):
            out |= {n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)}
    return out


def _check_extractable(stmt: ast.stmt) -> None:
    if not isinstance(stmt, _EXTRACTABLE):
        raise NotApplicable(f"cannot extract a {type(stmt).__name__} statement")
    if isinstance(stmt, ast.AnnAssign) and stmt.value is None:
        raise NotApplicable("bare annotation")
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        raise NotApplicable("docstring")
    for node in ast.walk(stmt):
        if isinstance(node, ast.Yield | ast.YieldFrom | ast.Await | ast.NamedExpr):
            raise NotApplicable("statement yields, awaits or uses :=")
        if isinstance(node, ast.Name) and node.id in {"super", "locals", "vars", "__class__"}:
            raise NotApplicable("statement depends on its frame")
        name = node.id if isinstance(node, ast.Name) else getattr(node, "attr", "")
        if isinstance(name, str) and name.startswith("__") and not name.endswith("__"):
            raise NotApplicable("private name mangling")


def _reindented(src: Source, stmt: ast.stmt, indent: str) -> list[str]:
    """The statement's lines with *indent* in place of its own indentation, unless a
    string literal spans lines (re-indenting would change the string)."""
    lines = [src.line(k) for k in range(stmt.lineno, _end(stmt) + 1)]
    own = _indent(lines[0])
    multiline_string = any(
        isinstance(n, ast.Constant | ast.JoinedStr) and _end(n) > n.lineno for n in ast.walk(stmt)
    )
    if multiline_string or not all(ln.startswith(own) or not ln.strip() for ln in lines):
        return lines
    return [indent + ln[len(own) :] if ln.strip() else ln for ln in lines]


def extract_helper(src: Source, line: int) -> Edit:
    """Move the flagged statement into a new module-level function placed right before
    the top-level definition that contains it, and call it from the old place. Locals
    the statement reads become parameters; locals it assigns are returned."""
    stmt = src.simple_statement(line)
    _check_extractable(stmt)
    func = src.enclosing_function(stmt.lineno)
    if func not in src.ancestors(stmt):
        raise NotApplicable("statement is not in a function body")
    chain = src.ancestors(func)
    if not (
        isinstance(chain[0], ast.Module)
        or (isinstance(chain[0], ast.ClassDef) and isinstance(chain[1], ast.Module))
    ):
        raise NotApplicable("function is nested in another function")
    if any(isinstance(n, ast.Global | ast.Nonlocal) for n in ast.walk(func)):
        raise NotApplicable("function declares global or nonlocal names")
    top = chain[-2] if len(chain) >= 2 else func
    assert isinstance(top, ast.stmt)

    local = _function_locals(func)
    nested = _nested_bound(stmt)
    loads: list[str] = []
    stores: list[str] = []
    for node in ast.walk(stmt):
        if isinstance(node, ast.Name):
            bucket = loads if isinstance(node.ctx, ast.Load) else stores
            bucket.append(node.id)
    if isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
        loads.append(stmt.target.id)
    if set(loads) & nested & local:
        raise NotApplicable("a comprehension or lambda shadows a local")
    params = list(dict.fromkeys(n for n in loads if n in local and n not in nested))
    outputs = list(dict.fromkeys(n for n in stores if n not in nested))

    name = _unique_name(src, f"_{func.name}_extracted")
    unit = "\t" if _indent(src.line(stmt.lineno)).startswith("\t") else "    "
    helper = [f"def {name}({', '.join(params)}):"]
    helper += _reindented(src, stmt, unit)
    if outputs:
        helper.append(f"{unit}return {', '.join(outputs)}")
    helper += ["", ""]

    call = f"{name}({', '.join(params)})"
    if isinstance(stmt, ast.Return):
        call = f"return {call}"
    elif outputs:
        call = f"{', '.join(outputs)} = {call}"
    call = _indent(src.line(stmt.lineno)) + call

    insert_at, _ = _block(src, top, 0)
    s0, s1 = stmt.lineno, _end(stmt)
    lines = _terminated(src.lines, src.newline)
    nl = src.newline
    new = (
        lines[: insert_at - 1]
        + [h + nl for h in helper]
        + lines[insert_at - 1 : s0 - 1]
        + [call + nl]
        + lines[s1:]
    )
    k, n = len(helper), s1 - s0 + 1
    line_map: dict[int, int] = {}
    for old in range(1, len(lines) + 1):
        if old < insert_at:
            line_map[old] = old
        elif old < s0:
            line_map[old] = old + k
        elif old <= s1:
            line_map[old] = insert_at + 1 + (old - s0)
        else:
            line_map[old] = old + k - n + 1
    return Edit("".join(new), line_map)


def _duplicate(src: Source, line: int, *, above: bool) -> Edit:
    stmt = src.simple_statement(line)
    src.enclosing_function(stmt.lineno)
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        raise NotApplicable("docstring")
    s0, s1 = stmt.lineno, _end(stmt)
    copy = [src.line(k) for k in range(s0, s1 + 1)]
    return _insert(src, s0 if above else s1 + 1, copy)


def duplicate_above(src: Source, line: int) -> Edit:
    """Copy the flagged statement directly above itself: the copy is a new finding."""
    return _duplicate(src, line, above=True)


def duplicate_below(src: Source, line: int) -> Edit:
    """Copy the flagged statement directly below itself: the copy is a new finding."""
    return _duplicate(src, line, above=False)


# ---------------------------------------------------------------------------
# ai_refactor
# ---------------------------------------------------------------------------

AI_PROMPT_VERSION = 1
AI_PROMPT = """\
Refactor this Python function without changing its behaviour. Keep its name, its
signature and its decorators. Reply with only the complete refactored function in one
```python code block.

```python
{code}
```
"""
_CODE_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL)


class AIRefactor:
    """Ask a language model to refactor the enclosing function.

    Responses are cached on disk by (model, prompt), so a rerun with the same cache
    gives the same edits without network access. The ground truth for these edits is a
    line diff (:func:`linemap.map_lines`), so every case is flagged for manual review.
    """

    def __init__(
        self,
        model: str,
        cache_dir: Path,
        *,
        api_key: str | None = None,
        offline: bool = False,
        ask: Callable[[str], str] | None = None,
    ) -> None:
        self.model = model
        self.cache_dir = cache_dir
        self.api_key = api_key
        self.offline = offline
        self._ask = ask
        self._client: Any = None
        self.calls = 0
        self.cache_hits = 0

    def complete(self, prompt: str) -> str:
        key = hashlib.sha256(f"{self.model}\0{prompt}".encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            self.cache_hits += 1
            return str(json.loads(path.read_text(encoding="utf-8"))["response"])
        if self.offline:
            raise NotApplicable("no cached model response (offline)")
        response = self._ask(prompt) if self._ask else self._call_api(prompt)
        self.calls += 1
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        record = {"model": self.model, "prompt": prompt, "response": response}
        path.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
        return response

    def _call_api(self, prompt: str) -> str:
        if self._client is None:
            try:
                anthropic: Any = importlib.import_module("anthropic")
            except ImportError as exc:
                raise RuntimeError("ai_refactor needs `pip install anthropic`") from exc
            self._client = anthropic.Anthropic(api_key=self.api_key)
        message = self._client.messages.create(
            model=self.model,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
        )
        if message.stop_reason == "refusal":
            raise NotApplicable("model declined")
        return "".join(b.text for b in message.content if b.type == "text")

    def __call__(self, src: Source, line: int) -> Edit:
        func = src.enclosing_function(line)
        f0, f1 = _start(func), _end(func)
        old_code = "".join(src.lines[f0 - 1 : f1])
        base = _indent(src.line(f0))
        prompt = AI_PROMPT.format(code=textwrap.dedent(old_code).rstrip("\n"))
        reply = self.complete(prompt)
        match = _CODE_BLOCK.search(reply)
        code = textwrap.dedent(match.group(1) if match else reply).strip("\n")
        try:
            module = ast.parse(code)
        except SyntaxError as exc:
            raise NotApplicable("model reply does not parse") from exc
        if not (
            len(module.body) == 1
            and isinstance(module.body[0], _FUNC_NODES)
            and module.body[0].name == func.name
        ):
            raise NotApplicable("model reply is not one function with the same name")
        nl = src.newline
        new_lines = [(base + ln if ln.strip() else ln) + nl for ln in code.split("\n")]
        lines = _terminated(src.lines, nl)
        new_text = "".join(lines[: f0 - 1] + new_lines + lines[f1:])
        try:
            ast.parse(new_text)
        except SyntaxError as exc:
            raise NotApplicable("spliced file does not parse") from exc
        if new_text == src.text:
            raise NotApplicable("model returned the function unchanged")
        mapping = map_lines(split_lines(src.text), split_lines(new_text))
        return Edit(
            new_text,
            {k: v[0] for k, v in mapping.items()},
            needs_review=True,
            review={"old": old_code, "new": "".join(new_lines)},
        )


def deterministic_transforms(reformat_line_length: int = 79) -> dict[str, Transform]:
    return {
        "reformat": make_reformat(reformat_line_length),
        "insert_top": insert_top,
        "insert_below": insert_below,
        "rename_local": rename_local,
        "rename_function": rename_function,
        "move_function": move_function,
        "change_literal": change_literal,
        "extract_helper": extract_helper,
        "duplicate_above": duplicate_above,
        "duplicate_below": duplicate_below,
    }
