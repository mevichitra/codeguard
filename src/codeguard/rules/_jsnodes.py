# SPDX-License-Identifier: Apache-2.0
"""Small helpers for JavaScript / TypeScript rules over a tree-sitter tree.

These operate on :class:`~codeguard.lang.node.SourceNode`, so a rule stays a few
lines: walk the calls, read the callee text, check whether an argument is a
literal.
"""

from __future__ import annotations

from collections.abc import Iterator

from codeguard.lang.node import SourceNode

_PUNCT = {"(", ")", ",", "[", "]", "{", "}", ";"}
_SECRET_NAME = (
    "password",
    "passwd",
    "pwd",
    "passphrase",
    "secret",
    "apikey",
    "api_key",
    "accesskey",
    "access_key",
    "secretkey",
    "secret_key",
    "privatekey",
    "private_key",
    "token",
    "auth_token",
    "authtoken",
    "client_secret",
    "clientsecret",
    "aws_secret",
)


def calls(root: SourceNode) -> Iterator[SourceNode]:
    """Yield every ``call_expression`` node."""
    for node in root.walk():
        if node.kind == "call_expression":
            yield node


def new_expressions(root: SourceNode) -> Iterator[SourceNode]:
    for node in root.walk():
        if node.kind == "new_expression":
            yield node


def callee_text(call: SourceNode) -> str:
    """The called expression as source text (``"eval"``, ``"cp.execSync"``)."""
    fn = call.child_by_field("function") or call.child_by_field("constructor")
    return fn.text() if fn else ""


def arguments(call: SourceNode) -> list[SourceNode]:
    """The argument nodes of a call, punctuation stripped."""
    args_node = call.child_by_field("arguments")
    if args_node is None:
        return []
    return [c for c in args_node.children() if c.kind not in _PUNCT]


def is_literal(node: SourceNode) -> bool:
    """True if *node* is a constant: a string / number / boolean literal, a
    template string with no ``${}`` substitutions, or a ``+`` tree of those."""
    kind = node.kind
    if kind in ("string", "number", "true", "false", "regex"):
        return True
    if kind == "template_string":
        return not any(d.kind == "template_substitution" for d in node.walk())
    if kind in ("binary_expression", "parenthesized_expression"):
        children = [c for c in node.children() if c.kind not in ("+", "(", ")")]
        return bool(children) and all(is_literal(c) for c in children)
    return False


def looks_like_secret(name: str) -> bool:
    low = name.lower()
    return any(marker in low for marker in _SECRET_NAME)
