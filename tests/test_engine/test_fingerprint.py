# SPDX-License-Identifier: Apache-2.0
"""Tests for stable finding fingerprints."""

from __future__ import annotations

import ast
import textwrap

from codeguard.engine import fingerprint as fp


def _fp(source: str, line: int) -> str:
    tree = ast.parse(textwrap.dedent(source))
    scope = fp.python_scope(tree, line)
    return fp.compute("CG-SEC-001", "mod.py", textwrap.dedent(source), line, scope=scope)


class TestStability:
    def test_whitespace_and_operator_spacing(self) -> None:
        a = "def f():\n    x = eval(data)\n"
        b = "def f():\n    x=eval( data )\n"
        assert _fp(a, 2) == _fp(b, 2)

    def test_blank_lines_and_trailing_comment(self) -> None:
        a = "import os\n\n\ndef f():\n    x = eval(data)\n"
        b = "import os\ndef f():\n    x = eval(data)  # checked\n"
        assert _fp(a, 5) == _fp(b, 3)

    def test_string_and_number_literals_masked(self) -> None:
        a = 'def f():\n    q = run("SELECT 1", 42)\n'
        b = 'def f():\n    q = run("SELECT 2", 99)\n'
        assert _fp(a, 2) == _fp(b, 2)


class TestSensitivity:
    def test_statement_change_moves_fingerprint(self) -> None:
        a = "def f():\n    x = eval(data)\n"
        b = "def f():\n    x = eval(other)\n"
        assert _fp(a, 2) != _fp(b, 2)

    def test_enclosing_scope_change_moves_fingerprint(self) -> None:
        a = "def f():\n    x = eval(data)\n"
        b = "def g():\n    x = eval(data)\n"
        assert _fp(a, 2) != _fp(b, 2)

    def test_rule_id_is_part_of_identity(self) -> None:
        src = textwrap.dedent("def f():\n    x = eval(data)\n")
        tree = ast.parse(src)
        scope = fp.python_scope(tree, 2)
        one = fp.compute("CG-SEC-001", "mod.py", src, 2, scope=scope)
        two = fp.compute("CG-SEC-003", "mod.py", src, 2, scope=scope)
        assert one != two


class TestPythonScope:
    def test_module_level(self) -> None:
        assert fp.python_scope(ast.parse("x = 1\n"), 1) == ""

    def test_nested(self) -> None:
        src = "class A:\n    def m(self):\n        y = 1\n"
        assert fp.python_scope(ast.parse(src), 3) == "A.m"


class TestRelativePath:
    def test_stdin_passthrough(self) -> None:
        assert fp.relative_path("<stdin>") == "<stdin>"

    def test_forward_slashes(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        p = tmp_path / "pkg" / "mod.py"
        assert "/" in fp.relative_path(str(p), root=str(tmp_path))
        assert "\\" not in fp.relative_path(str(p), root=str(tmp_path))
