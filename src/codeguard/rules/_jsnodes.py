# SPDX-License-Identifier: Apache-2.0
"""Small helpers for JavaScript / TypeScript rules over a tree-sitter tree.

These operate on :class:`~codeguard.lang.node.SourceNode`, so a rule stays a few
lines: walk the calls, read the callee text, check whether an argument is a
literal.
"""

from __future__ import annotations

import re
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


#: Names that mark a value as security-sensitive (tokens, secrets, ids, ...).
SECURITY_WORD = re.compile(
    r"(?i)(token|secret|password|passwd|nonce|salt|otp|apikey|api_key|"
    r"session|session_id|sessionid|csrf|uuid|guid|random_?id|verification|"
    r"reset_?code|auth)"
)

_NAME_BEARING = {
    "variable_declarator": "name",
    "assignment_expression": "left",
    "pair": "key",
    "public_field_definition": "name",
}

FUNCTION_KINDS = frozenset(
    {
        "function_declaration",
        "function_expression",
        "function",
        "arrow_function",
        "method_definition",
        "generator_function",
        "generator_function_declaration",
    }
)

LOOP_KINDS = frozenset({"for_statement", "for_in_statement", "while_statement", "do_statement"})

#: The field holding each loop's body (the part that runs repeatedly).
_LOOP_BODY = {
    "for_statement": "body",
    "for_in_statement": "body",
    "while_statement": "body",
    "do_statement": "body",
}


def enclosing_binding_name(node: SourceNode, *, depth: int = 6) -> str | None:
    """Walk up to *depth* ancestors looking for a binding; return its name text."""
    for i, parent in enumerate(node.ancestors()):
        if i >= depth:
            return None
        field = _NAME_BEARING.get(parent.kind)
        if field is not None:
            target = parent.child_by_field(field)
            if target is not None:
                return target.text()
    return None


def _same(a: SourceNode, b: SourceNode) -> bool:
    return a.native == b.native


def enclosing_loop(node: SourceNode) -> SourceNode | None:
    """The nearest loop whose body contains *node*, not crossing a function boundary."""
    child = node
    for anc in node.ancestors():
        if anc.kind in FUNCTION_KINDS:
            return None
        if anc.kind in LOOP_KINDS:
            body = anc.child_by_field(_LOOP_BODY[anc.kind])
            if body is not None and _same(body, child):
                return anc
        child = anc
    return None


def is_for_await(loop: SourceNode) -> bool:
    """True for ``for await (... of ...)``."""
    return loop.kind == "for_in_statement" and any(c.kind == "await" for c in loop.children())


def string_value(node: SourceNode) -> str | None:
    """The value of a plain string literal (quotes stripped), else ``None``."""
    if node.kind == "string":
        raw = node.text()
        return raw[1:-1] if len(raw) >= 2 else ""
    if node.kind == "template_string" and is_literal(node):
        raw = node.text()
        return raw[1:-1] if len(raw) >= 2 else ""
    return None


def member_property(node: SourceNode) -> str | None:
    """``"x"`` for ``obj.x``, else ``None``."""
    if node.kind != "member_expression":
        return None
    prop = node.child_by_field("property")
    return prop.text() if prop is not None else None
