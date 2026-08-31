# SPDX-License-Identifier: Apache-2.0
"""Tests for the tree-sitter JavaScript / TypeScript backends."""

from __future__ import annotations

from codeguard.lang import Language, language_for_path, support_for
from codeguard.lang.node import SourceNode

JS = support_for(Language.JAVASCRIPT)
TS = support_for(Language.TYPESCRIPT)


class TestExtensions:
    def test_javascript(self) -> None:
        for ext in (".js", ".jsx", ".mjs", ".cjs"):
            assert language_for_path(f"m{ext}") is Language.JAVASCRIPT

    def test_typescript(self) -> None:
        for ext in (".ts", ".tsx", ".mts", ".cts"):
            assert language_for_path(f"m{ext}") is Language.TYPESCRIPT


class TestParse:
    def test_javascript_ok(self) -> None:
        r = JS.parse("const x = f(y);\n", "m.js")
        assert r.ok and isinstance(r.root, SourceNode)
        assert r.root.kind == "program"

    def test_typescript_types_parse(self) -> None:
        r = TS.parse("function f(x: string): number { return 1; }\n", "m.ts")
        assert r.ok
        kinds = {n.kind for n in r.root.walk()}
        assert "function_declaration" in kinds

    def test_tsx_parses(self) -> None:
        r = TS.parse("const el = <div className={c}>{x}</div>;\n", "m.tsx")
        assert r.ok

    def test_error_recovery_keeps_tree(self) -> None:
        # a stray token should not throw away the rest of the file
        r = JS.parse("const a = 1;\n@@@\nconst b = eval(z);\n", "m.js")
        assert r.ok
        calls = [n for n in r.root.walk() if n.kind == "call_expression"]
        assert calls and calls[0].child_by_field("function").text() == "eval"

    def test_total_garbage_fails(self) -> None:
        r = JS.parse("!@#$%^&*(", "m.js")
        assert not r.ok
        assert r.error is not None


class TestSourceNode:
    def test_positions_are_one_indexed(self) -> None:
        r = JS.parse("\nconst x = danger();\n", "m.js")
        call = next(n for n in r.root.walk() if n.kind == "call_expression")
        assert call.start.line == 2
        assert call.start.col == 11  # 1-indexed

    def test_child_by_field(self) -> None:
        r = JS.parse("obj.method(arg);\n", "m.js")
        call = next(n for n in r.root.walk() if n.kind == "call_expression")
        assert call.child_by_field("function").text() == "obj.method"
        assert call.child_by_field("arguments").text() == "(arg)"

    def test_query_missing_returns_none(self) -> None:
        assert JS.query("no-such-query") is None
