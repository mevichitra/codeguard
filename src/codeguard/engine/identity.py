# SPDX-License-Identifier: Apache-2.0
"""Finding identity, scheme ``codeguard/v2``.

A finding's identity is a small record of keys, each built from the *statement* the
parser says contains the flagged line, never from the line text alone, the file path
or the message:

``stmt``
    rule + enclosing scope + the statement with literals masked and comments and
    whitespace removed.  The ``codeguard/v1`` payload without the path, taken from
    the whole statement span so re-wrapping a call does not change it.
``nscope``
    rule + the same statement, without the scope: survives a renamed or extracted
    enclosing function.
``ident``
    rule + scope + the statement with identifiers masked (``ID``), keeping keywords,
    attribute names and call names: survives a renamed local.
``body``
    for a finding on a function or class header only: rule + parent scope + the
    normalized body with the function's own name removed.  Survives a renamed
    function or a changed signature.
``lh``
    rule + the raw line without whitespace (SonarQube's line hash): the loosest key,
    used to pair renamed files by content.
``ctx_prev`` / ``ctx_next``
    the normalized non-blank lines before and after the statement.  Never a key:
    they break ties between candidates with equal keys (a pasted copy keeps one
    neighbour, the original keeps the other).
``v1``
    the ``codeguard/v1`` fingerprint, for baselines written before v2.

The keys are compared by :mod:`codeguard.engine.matcher`, strictest first, one to one.
"""

from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from codeguard.lang.base import Language

from .text import split_lines

SCHEME = "codeguard/v2"

#: Keys that identify a finding, strictest first.  ``ctx_*`` and ``v1`` are not here:
#: the former only break ties, the latter is the previous scheme.
KEY_NAMES = ("stmt", "nscope", "ident", "body", "lh")

_STRING_RE = re.compile(r"""(['"`]).*?(?<!\\)\1""")
_PY_COMMENT_RE = re.compile(r"#.*$")
_JS_COMMENT_RE = re.compile(r"//.*$")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_NUMBER_RE = re.compile(r"(?<![A-Za-z_$])\d[\d_]*(?:\.\d[\d_]*)?")
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[A-Za-z_$][\w$]*|[^\w\s$]")
_WORD_RE = re.compile(r"[A-Za-z_$][\w$]*")

_PY_KEYWORDS = frozenset(
    "False None True and as assert async await break class continue def del elif else "
    "except finally for from global if import in is lambda nonlocal not or pass raise "
    "return try while with yield match case self cls STR NUM".split()
)
_JS_KEYWORDS = frozenset(
    "await break case catch class const continue debugger default delete do else enum "
    "export extends false finally for function if import in instanceof let new null "
    "return super switch this throw true try typeof var void while with yield async of "
    "static get set undefined STR NUM".split()
)

_PY_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
_PY_COMPOUND = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
)
_JS_FUNCTION_NODES = frozenset(
    {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "function_expression",
        "generator_function",
        "arrow_function",
        "function",
    }
)
_JS_CLASS_NODES = frozenset({"class_declaration", "class", "abstract_class_declaration"})
_JS_STATEMENT_NODES = frozenset(
    {
        "method_definition",
        "field_definition",
        "public_field_definition",
        "abstract_method_signature",
        "method_signature",
        "property_signature",
    }
)


def _hash(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityRecord:
    """The identity of one finding: its keys, plus what the matcher needs to pair it.

    ``keys`` holds the hashes named in the module docstring that could be computed;
    a record built from a bare ``codeguard/v1`` fingerprint has only ``v1``.
    ``tokens`` is the token set of the normalized statement, for the similarity pass.
    ``idents`` and ``scope_words`` support the identifier check of the matcher.
    """

    rule: str
    file: str
    line: int
    scope: str = ""
    keys: Mapping[str, str] = field(default_factory=dict)
    tokens: frozenset[str] = frozenset()
    header: bool = False
    #: Identifiers the ``ident`` key masked: the matcher refuses to follow one that
    #: still exists in the other version's scope (a new variable, not a rename).
    idents: frozenset[str] = frozenset()
    #: Identifiers in the enclosing scope's text.  Not stored in baselines.
    scope_words: frozenset[str] = frozenset()

    def key(self, name: str) -> str:
        """The key *name*, or ``""`` when the record does not have it."""
        return self.keys.get(name, "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme": SCHEME,
            "scope": self.scope,
            "header": self.header,
            "keys": {k: self.keys[k] for k in sorted(self.keys)},
        }

    @classmethod
    def from_fingerprint(cls, rule: str, file: str, line: int, fingerprint: str) -> IdentityRecord:
        """A record that carries only a ``codeguard/v1`` fingerprint."""
        keys = {"v1": fingerprint} if fingerprint else {}
        return cls(rule=rule, file=file, line=line, keys=keys)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _strip_line(line: str, language: Language) -> str:
    """Mask literals and drop the comment of one line; whitespace is kept."""
    line = _STRING_RE.sub("STR", line)
    if language is Language.PYTHON:
        line = _PY_COMMENT_RE.sub("", line)
    else:
        line = _JS_COMMENT_RE.sub("", line)
    return _NUMBER_RE.sub("NUM", line)


def normalize(lines: list[str], language: Language) -> str:
    """The normalized form of a statement given as source lines.

    Literals are masked, comments dropped and whitespace collapsed to single spaces,
    so that :func:`tokens_of` still sees word boundaries; :func:`compact` removes the
    spaces for hashing.
    """
    text = "\n".join(_strip_line(ln, language) for ln in lines)
    if language is not Language.PYTHON:
        text = _BLOCK_COMMENT_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()


def compact(normalized: str) -> str:
    """A normalized statement without any whitespace, as the keys hash it."""
    return normalized.replace(" ", "")


def tokens_of(normalized: str) -> tuple[str, ...]:
    """The tokens of a normalized statement: words, ``STR``/``NUM`` and punctuation."""
    return tuple(_TOKEN_RE.findall(normalized))


def words_of(text: str) -> frozenset[str]:
    """The identifiers in *text* (literals masked first)."""
    return frozenset(_WORD_RE.findall(_STRING_RE.sub("STR", text)))


def mask_identifiers(normalized: str, language: Language) -> tuple[str, frozenset[str]]:
    """Replace identifiers by ``ID``, keeping keywords, attribute names and call names.

    Returns the masked statement (compact) and the identifiers that were masked.
    """
    keywords = _PY_KEYWORDS if language is Language.PYTHON else _JS_KEYWORDS
    toks = tokens_of(normalized)
    out: list[str] = []
    masked: set[str] = set()
    for i, tok in enumerate(toks):
        if _WORD_RE.fullmatch(tok) and tok not in keywords:
            after_dot = i > 0 and toks[i - 1] == "."
            call = i + 1 < len(toks) and toks[i + 1] == "("
            if not after_dot and not call:
                masked.add(tok)
                tok = "ID"
        out.append(tok)
    return "".join(out), frozenset(masked)


# ---------------------------------------------------------------------------
# Locating the statement
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Statement:
    """What a finding's line resolves to."""

    start: int  # first line of the text the keys are built from (1-based)
    end: int  # last line, inclusive
    scope: str  # enclosing scope; for a header, the parent's
    header: bool
    name: str = ""  # the function or class name, for headers
    body_start: int = 0
    body_end: int = 0
    scope_start: int = 0  # the lines of the scope named in ``scope`` (0: whole file)
    scope_end: int = 0


class _PythonIndex:
    def __init__(self, tree: ast.AST) -> None:
        self.stmts: list[tuple[int, int, ast.stmt]] = []
        self.scopes: list[tuple[int, int, str, list[str]]] = []  # start, end, name, chain
        self._walk(tree, [])

    def _walk(self, node: ast.AST, chain: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                end = getattr(child, "end_lineno", None) or child.lineno
                self.stmts.append((child.lineno, end, child))
            if isinstance(child, _PY_SCOPE_NODES):
                end = getattr(child, "end_lineno", None) or child.lineno
                self.scopes.append((child.lineno, end, child.name, list(chain)))
                chain.append(child.name)
                self._walk(child, chain)
                chain.pop()
            else:
                self._walk(child, chain)

    def scope_at(self, line: int, *, exclude_own: bool = False) -> tuple[str, int, int]:
        """The scope enclosing *line* and its line span (``0, 0`` for the module).

        With *exclude_own*, the innermost scope is left out (for a header finding)
        and the span is its parent's.
        """
        found = [(s, e, name, chain) for s, e, name, chain in self.scopes if s <= line <= e]
        found.sort(key=lambda x: x[1] - x[0])
        if exclude_own and found:
            found = found[1:]
        if not found:
            return "", 0, 0
        s, e, name, chain = found[0]
        return ".".join([*chain, name]), s, e

    def statement_at(self, line: int) -> _Statement:
        best: tuple[int, int, ast.stmt] | None = None
        for s, e, node in self.stmts:
            if s <= line <= e and (best is None or (e - s) <= (best[1] - best[0])):
                best = (s, e, node)
        scope, ss, se = self.scope_at(line)
        if best is None:
            return _Statement(line, line, scope, False, scope_start=ss, scope_end=se)
        s, e, node = best
        if isinstance(node, _PY_COMPOUND):
            body: list[ast.stmt] = getattr(node, "body", [])
            header_end = max(body[0].lineno - 1 if body else e, s)
            if line > header_end:
                # an ``else:``/``elif`` line or a comment between statements
                return _Statement(line, line, scope, False, scope_start=ss, scope_end=se)
            if isinstance(node, _PY_SCOPE_NODES):
                scope, ss, se = self.scope_at(line, exclude_own=True)
                return _Statement(
                    s,
                    header_end,
                    scope,
                    True,
                    node.name,
                    body[0].lineno if body else e,
                    e,
                    ss,
                    se,
                )
            return _Statement(s, header_end, scope, False, scope_start=ss, scope_end=se)
        return _Statement(s, e, scope, False, scope_start=ss, scope_end=se)


class _TreeSitterIndex:
    def __init__(self, root: Any) -> None:
        self.root = root

    @staticmethod
    def _lines(node: Any) -> tuple[int, int]:
        return node.start_point[0] + 1, node.end_point[0] + 1

    @staticmethod
    def _is_statement(node: Any) -> bool:
        t = str(node.type)
        return t.endswith("_statement") or t.endswith("_declaration") or t in _JS_STATEMENT_NODES

    def _smallest_statement(self, line: int) -> Any | None:
        best: Any | None = None
        stack = [self.root]
        while stack:
            node = stack.pop()
            s, e = self._lines(node)
            if line < s or line > e:
                continue
            if self._is_statement(node) and (best is None or (e - s) <= _span(best)):
                best = node
            stack.extend(node.children)
        return best

    @staticmethod
    def _name_of(node: Any) -> str:
        """The name a function-like or class node is known by, or ``""``."""
        name = node.child_by_field_name("name")
        if name is not None:
            return _text(name)
        parent = node.parent
        if parent is None:
            return ""
        if parent.type == "variable_declarator":
            return _text(parent.child_by_field_name("name"))
        if parent.type == "pair":
            return _text(parent.child_by_field_name("key"))
        if parent.type == "assignment_expression":
            return _text(parent.child_by_field_name("left"))
        if parent.type in ("field_definition", "public_field_definition"):
            return _text(parent.child_by_field_name("name"))
        return ""

    def _chain(self, node: Any) -> tuple[str, int, int]:
        """The scope enclosing *node* (dotted, outermost first) and its line span."""
        names: list[str] = []
        span = (0, 0)
        cur = node.parent
        while cur is not None:
            if cur.type in _JS_FUNCTION_NODES or cur.type in _JS_CLASS_NODES:
                name = self._name_of(cur)
                if name:
                    if not names:
                        span = self._lines(cur)
                    names.append(name)
            cur = cur.parent
        names.reverse()
        return ".".join(names), *span

    def statement_at(self, line: int) -> _Statement:
        node = self._smallest_statement(line)
        if node is None:
            return _Statement(line, line, "", False)
        s, e = self._lines(node)
        scope, ss, se = self._chain(node)
        func = _function_of(node)
        if func is not None:
            body = func.child_by_field_name("body")
            if body is not None:
                body_start, body_end = self._lines(body)
                header_end = max(s, body_start - 1)
                if line <= header_end:
                    scope, ss, se = self._chain(func)
                    return _Statement(
                        s,
                        header_end,
                        scope,
                        True,
                        self._name_of(func),
                        body_start,
                        body_end,
                        ss,
                        se,
                    )
                # a line of the body no inner statement covers: a closing brace
                return _Statement(line, line, scope, False, scope_start=ss, scope_end=se)
        return _Statement(s, e, scope, False, scope_start=ss, scope_end=se)


def _span(node: Any) -> int:
    return int(node.end_point[0] - node.start_point[0])


def _text(node: Any | None) -> str:
    if node is None:
        return ""
    raw = node.text
    return raw.decode("utf-8", "replace") if raw is not None else ""


def _function_of(stmt: Any) -> Any | None:
    """The function or class node whose header *stmt* is, if it is one."""
    if stmt.type in _JS_FUNCTION_NODES or stmt.type in _JS_CLASS_NODES:
        return stmt
    if stmt.type == "export_statement":
        for child in stmt.children:
            if child.type in _JS_FUNCTION_NODES or child.type in _JS_CLASS_NODES:
                return child
    if stmt.type in ("lexical_declaration", "variable_declaration"):
        for child in stmt.children:
            if child.type == "variable_declarator":
                value = child.child_by_field_name("value")
                if value is not None and value.type in _JS_FUNCTION_NODES:
                    return value
    if stmt.type == "expression_statement" and stmt.children:
        expr = stmt.children[0]
        if expr.type == "assignment_expression":
            value = expr.child_by_field_name("right")
            if value is not None and value.type in _JS_FUNCTION_NODES:
                return value
    return None


# ---------------------------------------------------------------------------
# Building records for one file
# ---------------------------------------------------------------------------


class IdentityBuilder:
    """Computes :class:`IdentityRecord` for the findings of one file version.

    Parameters
    ----------
    source:
        The file text.
    language:
        Its language.
    tree:
        The parsed tree: an :class:`ast.AST` for Python, a tree-sitter root node for
        JavaScript and TypeScript, or ``None`` when the file did not parse (keys are
        then built from the line alone).
    """

    def __init__(self, source: str, language: Language, tree: object | None) -> None:
        self.lines = split_lines(source)
        self.language = language
        self._py: _PythonIndex | None = None
        self._ts: _TreeSitterIndex | None = None
        if isinstance(tree, ast.AST):
            self._py = _PythonIndex(tree)
        elif tree is not None and hasattr(tree, "start_point"):
            self._ts = _TreeSitterIndex(tree)
        self._cache: dict[int, _Statement] = {}
        self._words: dict[tuple[int, int], frozenset[str]] = {}

    def _statement(self, line: int) -> _Statement:
        hit = self._cache.get(line)
        if hit is None:
            if self._py is not None:
                hit = self._py.statement_at(line)
            elif self._ts is not None:
                hit = self._ts.statement_at(line)
            else:
                hit = _Statement(line, line, "", False)
            self._cache[line] = hit
        return hit

    def _slice(self, start: int, end: int) -> list[str]:
        return self.lines[max(start, 1) - 1 : max(end, 0)]

    def _neighbour(self, at: int, step: int) -> str:
        """The nearest non-blank line from *at* (exclusive) in direction *step*."""
        i = at + step
        while 1 <= i <= len(self.lines):
            text = self.lines[i - 1].strip()
            if text:
                return compact(normalize([text], self.language))
            i += step
        return ""

    def _scope_words(self, start: int, end: int) -> frozenset[str]:
        span = (start, end) if start else (1, len(self.lines))
        hit = self._words.get(span)
        if hit is None:
            hit = words_of("\n".join(self._slice(*span)))
            self._words[span] = hit
        return hit

    def record(self, rule: str, file: str, line: int, *, v1: str = "") -> IdentityRecord:
        """The identity of the finding *rule* at *line*."""
        if not 1 <= line <= len(self.lines):
            return IdentityRecord.from_fingerprint(rule, file, line, v1)
        st = self._statement(line)
        spaced = normalize(self._slice(st.start, st.end), self.language)
        if not spaced:
            spaced = normalize([self.lines[line - 1]], self.language)
        stmt_norm = compact(spaced)
        ident_norm, idents = mask_identifiers(spaced, self.language)
        raw_line = _WS_RE.sub("", self.lines[line - 1])
        prev, nxt = self._neighbour(st.start, -1), self._neighbour(st.end, 1)
        keys: dict[str, str] = {
            "stmt": _hash(rule, st.scope, stmt_norm),
            "nscope": _hash(rule, stmt_norm),
            "ident": _hash(rule, st.scope, ident_norm),
            "lh": _hash(rule, raw_line),
            "ctx_prev": _hash(prev) if prev else "",
            "ctx_next": _hash(nxt) if nxt else "",
        }
        if st.header and st.body_start:
            body_norm = compact(normalize(self._slice(st.body_start, st.body_end), self.language))
            if st.name:
                body_norm = re.sub(rf"(?<![\w$]){re.escape(st.name)}(?![\w$])", "SELF", body_norm)
            keys["body"] = _hash(rule, st.scope, body_norm)
        if v1:
            keys["v1"] = v1
        return IdentityRecord(
            rule=rule,
            file=file,
            line=line,
            scope=st.scope,
            keys=keys,
            tokens=frozenset(tokens_of(spaced)),
            header=st.header,
            idents=idents,
            scope_words=self._scope_words(st.scope_start, st.scope_end),
        )


def scope_at(source: str, language: Language, tree: object | None, line: int) -> str:
    """The enclosing scope of *line* (the function or class chain, dotted)."""
    return IdentityBuilder(source, language, tree)._statement(line).scope


def iter_keys(record: IdentityRecord) -> Iterator[tuple[str, str]]:
    """``(name, hash)`` for every identifying key the record has, strictest first."""
    for name in KEY_NAMES:
        value = record.keys.get(name)
        if value:
            yield name, value
