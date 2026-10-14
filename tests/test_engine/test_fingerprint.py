# SPDX-License-Identifier: Apache-2.0
"""Tests for stable finding fingerprints."""

from __future__ import annotations

import ast
import textwrap

import pytest

import codeguard.rules  # noqa: F401  (registers rules)
from codeguard.engine import fingerprint as fp
from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language


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


class TestLineSeparators:
    """Only LF, CRLF and CR end a line -- the same lines ``ast`` numbers."""

    def test_finding_after_form_feed_uses_its_own_line(self) -> None:
        src = "x = 1\n\x0c\ndef f(s):\n    return eval(s)\n"
        plain = "x = 1\n\ndef f(s):\n    return eval(s)\n"
        runner = AnalysisRunner(rule_ids=["CG-SEC-003"])
        [with_ff] = runner.run(src, filename="m.py", language=Language.PYTHON)
        [without] = runner.run(plain, filename="m.py", language=Language.PYTHON)
        assert with_ff.location.line == without.location.line == 4
        assert with_ff.fingerprint == without.fingerprint

    @pytest.mark.parametrize(
        "sep", ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]
    )
    def test_unicode_line_breaks_do_not_shift_lines(self, sep: str) -> None:
        a = f"# page{sep}break\ndef f():\n    x = eval(data)\n"
        b = "# page break\ndef f():\n    x = eval(data)\n"
        assert _fp(a, 3) == _fp(b, 3)

    @pytest.mark.parametrize("eol", ["\r\n", "\r"])
    def test_crlf_and_cr_line_endings(self, eol: str) -> None:
        a = "def f():\n    x = eval(data)\n"
        assert _fp(a.replace("\n", eol), 2) == _fp(a, 2)


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
