# SPDX-License-Identifier: Apache-2.0
"""Shared predicates for Python security sinks.

Pattern rules (CG-SEC-001/003/005) and taint rules (CG-SEC-010..014) agree on
what a SQL call, a shell call, or an eval call looks like by using these
functions.
"""

from __future__ import annotations

import ast

from codeguard.rules._pyimports import ImportMap

SQL_METHODS = frozenset({"execute", "executemany", "executescript"})
EVAL_BUILTINS = frozenset({"eval", "exec", "compile"})

#: subprocess entry points that use a shell only when ``shell=True`` is passed.
SHELL_OPTIONAL: frozenset[tuple[str, str]] = frozenset(
    {
        ("subprocess", "run"),
        ("subprocess", "call"),
        ("subprocess", "Popen"),
        ("subprocess", "check_output"),
        ("subprocess", "check_call"),
    }
)

#: Calls that always run their argument through a shell.
ALWAYS_SHELL: frozenset[tuple[str, str]] = frozenset(
    {
        ("os", "system"),
        ("os", "popen"),
        ("subprocess", "getoutput"),
        ("subprocess", "getstatusoutput"),
    }
)

#: File-system calls whose first positional argument is a path.
PATH_CALLS: frozenset[tuple[str | None, str]] = frozenset(
    {
        (None, "open"),
        ("builtins", "open"),
        ("io", "open"),
        ("os", "open"),
        ("os", "remove"),
        ("os", "unlink"),
        ("os", "rmdir"),
        ("os", "listdir"),
        ("os", "rename"),
        ("shutil", "rmtree"),
        ("shutil", "copy"),
        ("shutil", "copyfile"),
        ("shutil", "move"),
        ("flask", "send_file"),
        ("pathlib", "Path"),
    }
)

#: Calls whose first positional argument is a redirect target.
REDIRECT_CALLS: frozenset[tuple[str | None, str]] = frozenset(
    {
        ("flask", "redirect"),
        ("django.shortcuts", "redirect"),
        ("django.http", "HttpResponseRedirect"),
        ("django.http", "HttpResponsePermanentRedirect"),
        ("fastapi.responses", "RedirectResponse"),
        ("starlette.responses", "RedirectResponse"),
        (None, "redirect"),
        (None, "HttpResponseRedirect"),
        (None, "RedirectResponse"),
    }
)


def is_sql_execute(call: ast.Call) -> bool:
    """``<anything>.execute(...)`` / ``executemany`` / ``executescript``."""
    return isinstance(call.func, ast.Attribute) and call.func.attr in SQL_METHODS


def is_constant_concat(node: ast.AST) -> bool:
    """True if *node* is a string literal or a ``+`` tree of string literals."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return is_constant_concat(node.left) and is_constant_concat(node.right)
    return False


def is_dynamic_string(node: ast.AST) -> bool:
    """True if *node* builds a string by formatting or concatenation inline."""
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return not is_constant_concat(node)
    return False


def eval_like_name(call: ast.Call) -> str | None:
    """``"eval"`` / ``"exec"`` / ``"compile"`` for a bare call to one of them, else ``None``."""
    if isinstance(call.func, ast.Name) and call.func.id in EVAL_BUILTINS:
        return call.func.id
    return None


def has_shell_true(call: ast.Call) -> bool:
    """True if ``shell=True`` (or another truthy constant) is passed."""
    for kw in call.keywords:
        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value:
            return True
    return False


def command_arg(call: ast.Call) -> ast.expr | None:
    """The command argument of a subprocess / os call (first positional or ``args=``)."""
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "args":
            return kw.value
    return None


def command_is_literal(call: ast.Call) -> bool:
    """True if the command is a string literal or a list of literals (or absent)."""
    arg = command_arg(call)
    if arg is None:
        return True
    if isinstance(arg, ast.List):
        return all(isinstance(elt, ast.Constant) for elt in arg.elts)
    return isinstance(arg, ast.Constant)


def shell_target(call: ast.Call, imports: ImportMap) -> tuple[str, str] | None:
    """The canonical ``(module, name)`` if *call* runs its command through a shell."""
    target = imports.resolve_call(call.func)
    if target in ALWAYS_SHELL:
        return target
    if target in SHELL_OPTIONAL and has_shell_true(call):
        return target
    return None


def path_call_arg(call: ast.Call, imports: ImportMap) -> ast.expr | None:
    """The path argument of a file-system call, or ``None`` if *call* is not one."""
    module, name = imports.resolve_call(call.func)
    if name is None:
        return None
    if (module, name) in PATH_CALLS or (module is None and (None, name) in PATH_CALLS):
        return call.args[0] if call.args else None
    if (module, name) == ("flask", "send_from_directory") and len(call.args) >= 2:
        return call.args[1]
    return None


def redirect_call_arg(call: ast.Call, imports: ImportMap) -> ast.expr | None:
    """The target argument of a redirect call, or ``None`` if *call* is not one."""
    module, name = imports.resolve_call(call.func)
    if name is None:
        return None
    if (module, name) not in REDIRECT_CALLS and (None, name) not in REDIRECT_CALLS:
        return None
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg in ("location", "url", "redirect_to"):
            return kw.value
    return None
