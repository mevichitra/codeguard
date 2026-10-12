# SPDX-License-Identifier: Apache-2.0
"""Tests for the Python intraprocedural taint analysis."""

from __future__ import annotations

import ast
import textwrap

import pytest

from codeguard.engine.dataflow.python import analyze_python


def _sinks(src: str) -> dict[str, object]:
    """Taint of the first argument of every `sink(...)` call, keyed by `sink(<label>)`."""
    src = textwrap.dedent(src)
    tree = ast.parse(src)
    df = analyze_python(tree, src)
    out: dict[str, object] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sink"
        ):
            label = node.args[1].value if len(node.args) > 1 else str(node.lineno)  # type: ignore[attr-defined]
            out[str(label)] = df.taint_of(node.args[0])
    return out


def _tainted(src: str) -> set[str]:
    return {k for k, v in _sinks(src).items() if v is not None}


def test_flask_request_flows_through_assignments() -> None:
    src = """
        from flask import request
        def view():
            name = request.args.get("n")
            cmd = "ls " + name
            sink(cmd, "a")
            sink("ls", "b")
    """
    infos = _sinks(src)
    assert infos["b"] is None
    info = infos["a"]
    assert info is not None
    assert info.source.label == "flask request.args"  # type: ignore[attr-defined]
    assert [h.text for h in info.path] == [  # type: ignore[attr-defined]
        'name = request.args.get("n")',
        'cmd = "ls " + name',
    ]


def test_alias_import_resolved() -> None:
    assert _tainted("from flask import request as rq\nx = rq.form['a']\nsink(x, 'a')\n") == {"a"}


def test_sanitizer_removes_taint() -> None:
    src = """
        import shlex, sys
        a = sys.argv[1]
        sink(shlex.quote(a), "q")
        sink(int(a), "i")
        sink(a.strip(), "s")
        sink(a.isdigit(), "d")
    """
    assert _tainted(src) == {"s"}


def test_reassignment_clears_and_branches_merge() -> None:
    src = """
        x = input()
        x = "safe"
        sink(x, "cleared")
        y = "safe"
        if cond:
            y = input()
        sink(y, "merged")
    """
    assert _tainted(src) == {"merged"}


def test_loop_carries_taint_to_next_iteration() -> None:
    src = """
        prev = ""
        for line in data:
            sink(prev, "loop")
            prev = input()
    """
    assert _tainted(src) == {"loop"}


def test_handler_parameters_are_sources_and_others_are_not() -> None:
    src = """
        @app.route("/u/<name>")
        def show(name, request):
            sink(name, "route")
            sink(request, "req")

        def helper(name):
            sink(name, "plain")

        @property
        def prop(self, name):
            sink(name, "prop")
    """
    assert _tainted(src) == {"route"}


def test_django_request_attrs_and_self_request() -> None:
    src = """
        def view(request):
            sink(request.GET["q"], "get")
            sink(request.user, "user")
        class V:
            def get(self):
                sink(self.request.data, "drf")
    """
    assert _tainted(src) == {"get", "drf"}


def test_fstring_format_join_and_containers() -> None:
    src = """
        import os
        v = os.environ["HOME"]
        sink(f"x{v}", "f")
        sink("{}".format(v), "fmt")
        sink(" ".join([v]), "join")
        d = {}
        d["k"] = v
        sink(d, "dict")
        sink([c for c in v], "comp")
        sink(os.path.join("/tmp", v), "join_path")
        sink(len(v), "len")
    """
    assert _tainted(src) == {"f", "fmt", "join", "dict", "comp", "join_path"}


def test_attribute_target_does_not_taint_whole_object() -> None:
    src = """
        self.q = input()
        sink(self.q, "attr")
        sink(self.other, "other")
    """
    assert _tainted(src) == {"attr"}


def test_unknown_function_returns_clean() -> None:
    assert _tainted("x = helper(input())\nsink(x, 'a')\n") == set()


def test_closure_sees_enclosing_taint_and_params_shadow() -> None:
    src = """
        x = input()
        def inner():
            sink(x, "closure")
        def shadow(x):
            sink(x, "shadow")
    """
    assert _tainted(src) == {"closure"}


def test_try_with_match_walrus() -> None:
    src = """
        try:
            a = input()
        except ValueError as exc:
            a = "x"
        sink(a, "try")
        stream = input()
        with stream as fh:
            sink(fh.read(), "with")
        with open(input()) as cfg:
            sink(cfg.read(), "file")  # contents of a user-chosen file are not request data
        match input():
            case str() as m:
                sink(m, "match")
        if (n := input()):
            sink(n, "walrus")
    """
    assert _tainted(src) == {"try", "with", "match", "walrus"}


def test_local_vs_web_kind() -> None:
    infos = _sinks(
        "import sys\nfrom flask import request\nsink(sys.argv, 'l')\nsink(request.json, 'w')\n"
    )
    assert infos["l"].source.kind == "local"  # type: ignore[union-attr]
    assert infos["w"].source.kind == "web"  # type: ignore[union-attr]


@pytest.mark.parametrize("depth", [200])
def test_deep_expression_does_not_crash(depth: int) -> None:
    expr = " + ".join(["input()"] * depth)
    assert _tainted(f"x = {expr}\nsink(x, 'deep')\n") == {"deep"}
