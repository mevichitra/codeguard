# SPDX-License-Identifier: Apache-2.0
"""Stable finding fingerprints.

A fingerprint identifies "the same finding" across reformatting, whitespace
changes, and line moves, so a baseline entry or a suppression stays matched to
its finding.  It deliberately *does* change when the finding's own statement or
its enclosing scope changes -- that is what makes diff/baseline workflows
meaningful.

Scheme ``codeguard/v1``:

    sha256(rule_id \\0 relative_path \\0 scope \\0 normalized_statement)[:16]

where *scope* is the dotted name of the enclosing function/class (Python) and
*normalized_statement* is the finding's own source line with string and number
literals masked and comments / whitespace stripped.  Line numbers are
deliberately excluded so a finding survives being moved within its scope.
"""

from __future__ import annotations

import ast
import hashlib
import os
import re

SCHEME = "codeguard/v1"

_STRING_RE = re.compile(r"""(['"]).*?(?<!\\)\1""", re.DOTALL)
_NUMBER_RE = re.compile(r"(?<![A-Za-z_])\d[\d_]*(?:\.\d[\d_]*)?")
_COMMENT_RE = re.compile(r"(#|//).*$")
_WS_RE = re.compile(r"\s+")

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def relative_path(file: str, *, root: str | None = None) -> str:
    """Normalise *file* to a forward-slash path relative to *root* (cwd by default).

    Fingerprints assume runs happen from the project root (as pre-commit and CI
    do).  Paths that cannot be made relative are returned unchanged.
    """
    if file in ("<stdin>", "<string>"):
        return file
    base = root or os.getcwd()
    try:
        rel = os.path.relpath(file, base)
    except ValueError:
        rel = file
    return rel.replace(os.sep, "/")


def _normalize(text: str) -> str:
    text = _STRING_RE.sub("STR", text)
    text = _COMMENT_RE.sub("", text)
    text = _NUMBER_RE.sub("NUM", text)
    return _WS_RE.sub("", text)


def _normalized_statement(source: str, line: int) -> str:
    lines = source.splitlines()
    if 1 <= line <= len(lines):
        return _normalize(lines[line - 1])
    return ""


def python_scope(tree: ast.AST, line: int) -> str:
    """Return the dotted name of the innermost function/class enclosing *line*.

    ``""`` for module level.  E.g. ``"MyClass.method"`` or ``"handler"``.
    """
    path: list[str] = []

    def visit(node: ast.AST, prefix: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPE_NODES):
                start = child.lineno
                end = getattr(child, "end_lineno", start)
                if start <= line <= end:
                    prefix.append(child.name)
                    path[:] = list(prefix)
                    visit(child, prefix)
                    prefix.pop()
            else:
                visit(child, prefix)

    visit(tree, [])
    return ".".join(path)


def compute(rule_id: str, rel_path: str, source: str, line: int, *, scope: str = "") -> str:
    """Return the 16-hex-char fingerprint for a finding."""
    payload = f"{rule_id}\0{rel_path}\0{scope}\0{_normalized_statement(source, line)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
