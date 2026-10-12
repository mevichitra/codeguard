# SPDX-License-Identifier: Apache-2.0
"""Tests for the shared rule helpers."""

from __future__ import annotations

import ast
import textwrap

from codeguard.lang.base import Language
from codeguard.lang.registry import support_for
from codeguard.rules import _jscomplexity, _jsnodes, _pycomplexity
from codeguard.rules._pyimports import ImportMap, insertion_line
from codeguard.rules._pyparents import PyParents


def _js(src: str):  # type: ignore[no-untyped-def]
    parsed = support_for(Language.JAVASCRIPT).parse(src, "x.js")
    assert parsed.root is not None
    return parsed.root


def _fn(src: str) -> ast.FunctionDef:
    node = ast.parse(textwrap.dedent(src)).body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def test_py_cyclomatic_and_nesting() -> None:
    fn = _fn(
        """
        def f(a, b):
            if a and b:
                for x in a:
                    while x:
                        x -= 1
            elif b:
                pass
            try:
                pass
            except ValueError:
                pass
            return [i for i in a if i]
            def inner():
                if a: pass
        """
    )
    # 1 + if + and + for + while + elif(if) + except + comprehension(1 + 1 if)
    assert _pycomplexity.cyclomatic(fn) == 9
    assert _pycomplexity.max_nesting(fn) == 3


def test_py_param_count() -> None:
    assert _pycomplexity.param_count(_fn("def m(self, a, *args, b, **kw): pass")) == 4
    assert _pycomplexity.param_count(_fn("def f(): pass")) == 0


def test_py_enclosing_loop_body_only() -> None:
    tree = ast.parse("for x in f():\n    g(x)\nelse:\n    h()\n")
    parents = PyParents.from_tree(tree)
    calls = {n.func.id: n for n in ast.walk(tree) if isinstance(n, ast.Call)}  # type: ignore[union-attr]
    assert parents.in_loop(calls["g"])
    assert not parents.in_loop(calls["f"])  # iter runs once
    assert not parents.in_loop(calls["h"])  # else block


def test_py_loop_does_not_cross_function() -> None:
    tree = ast.parse("for x in y:\n    def cb():\n        g()\n")
    parents = PyParents.from_tree(tree)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert not parents.in_loop(call)


def test_py_security_context() -> None:
    tree = ast.parse("reset_token = make()\ncolor = make()\n")
    parents = PyParents.from_tree(tree)
    a, b = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert parents.in_security_context(a)
    assert not parents.in_security_context(b)


def test_insertion_line() -> None:
    assert insertion_line(ast.parse('"""doc"""\nimport os\nimport sys\nx = 1\n')) == 4
    assert insertion_line(ast.parse('"""doc"""\nx = 1\n')) == 2
    assert insertion_line(ast.parse("x = 1\n")) == 1


def test_import_map_local_name() -> None:
    m = ImportMap.from_tree(ast.parse("import random as rnd\nimport os\n"))
    assert m.local_name_for("random") == "rnd"
    assert m.local_name_for("os") == "os"
    assert m.has_module("random") and not m.has_module("secrets")


def test_js_enclosing_loop_and_binding() -> None:
    root = _js("for (const x of xs) { const token = Math.random(); }\nfoo(() => { while (1) {} });")
    call = next(c for c in _jsnodes.calls(root) if _jsnodes.callee_text(c) == "Math.random")
    assert _jsnodes.enclosing_loop(call) is not None
    assert _jsnodes.enclosing_binding_name(call) == "token"
    outer = next(c for c in _jsnodes.calls(root) if _jsnodes.callee_text(c) == "foo")
    assert _jsnodes.enclosing_loop(outer) is None


def test_js_cyclomatic() -> None:
    root = _js(
        "function f(a){ if (a && b) { return a ? 1 : 2 } for(;;){} function g(){ if(x){} } }"
    )
    fn = next(_jscomplexity.functions(root))
    assert _jscomplexity.function_name(fn) == "f"
    assert _jscomplexity.cyclomatic(fn) == 5  # 1 + if + && + ?: + for
