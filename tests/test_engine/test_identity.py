# SPDX-License-Identifier: Apache-2.0
"""Tests for the ``codeguard/v2`` identity record, the matcher and file pairing."""

from __future__ import annotations

import ast
import random
import subprocess
import textwrap
import time
from pathlib import Path

from codeguard.engine import gitdiff
from codeguard.engine.filepairs import PairConfig, pair_files
from codeguard.engine.identity import (
    IdentityBuilder,
    IdentityRecord,
    compact,
    mask_identifiers,
    normalize,
    scope_at,
)
from codeguard.engine.matcher import MatchConfig, jaccard, match
from codeguard.lang.base import Language
from codeguard.lang.registry import support_for

EV = "ev" + "al"


def _records(
    source: str, *, rule: str = "CG-SEC-003", lines: list[int] | None = None, filename: str = "a.py"
) -> list[IdentityRecord]:
    source = textwrap.dedent(source)
    lang = Language.PYTHON if filename.endswith(".py") else Language.JAVASCRIPT
    if lang is Language.PYTHON:
        tree: object = ast.parse(source)
    else:
        tree = support_for(lang).parse(source, filename).root.native  # type: ignore[union-attr]
    builder = IdentityBuilder(source, lang, tree)
    if lines is None:
        lines = [i + 1 for i, ln in enumerate(source.splitlines()) if EV + "(" in ln]
    return [builder.record(rule, filename, ln) for ln in lines]


def _pairs(
    old: list[IdentityRecord], new: list[IdentityRecord], **kw: object
) -> list[tuple[int, int, str, bool]]:
    cfg = MatchConfig(**kw) if kw else None  # type: ignore[arg-type]
    return [(m.old, m.new, m.pass_name, m.ambiguous) for m in match(old, new, cfg)]


# ---------------------------------------------------------------------------
# Identity records
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_literals_comments_and_whitespace(self) -> None:
        a = normalize(['x = run("SELECT 1", 42)  # note'], Language.PYTHON)
        b = normalize(["x=run('SELECT 2',   99)"], Language.PYTHON)
        assert a == "x = run(STR, NUM)"
        assert compact(a) == compact(b) == "x=run(STR,NUM)"

    def test_javascript_template_literal_and_block_comment(self) -> None:
        a = normalize(["const q = `a${b}` /* c */ + 1;"], Language.JAVASCRIPT)
        assert a == "const q = STR + NUM;"

    def test_mask_identifiers_keeps_calls_attributes_and_keywords(self) -> None:
        masked, idents = mask_identifiers("return eval(data.strip())", Language.PYTHON)
        assert masked == "returneval(ID.strip())"
        assert idents == frozenset({"data"})


class TestStatementSpan:
    def test_multiline_call_is_one_statement(self) -> None:
        [a] = _records(f"def h(a):\n    return {EV}(a,\n        b)\n", lines=[2])
        [b] = _records(f"def h(a):\n    return {EV}(\n        a, b)\n", lines=[2])
        assert a.key("stmt") == b.key("stmt")

    def test_header_finding_has_parent_scope_and_body_key(self) -> None:
        [rec] = _records("class C:\n    def f(self, a):\n        return a\n", rule="Q", lines=[2])
        assert rec.header is True
        assert rec.scope == "C"
        assert rec.key("body")
        [other] = _records(
            "class C:\n    def g(self, a, b):\n        return a\n", rule="Q", lines=[2]
        )
        assert other.key("body") == rec.key("body")  # the body ignores the name and signature

    def test_body_key_absent_off_headers(self) -> None:
        [rec] = _records(f"def h(a):\n    return {EV}(a)\n")
        assert rec.header is False and not rec.key("body")

    def test_line_outside_any_statement(self) -> None:
        src = "x = 1\n\n# comment\n"
        rec = IdentityBuilder(src, Language.PYTHON, ast.parse(src)).record("R", "a.py", 3)
        assert rec.key("stmt") and rec.scope == ""

    def test_unparsed_file_falls_back_to_the_line(self) -> None:
        rec = IdentityBuilder("a = b(\n", Language.PYTHON, None).record("R", "a.py", 1)
        assert rec.key("stmt") and rec.key("lh")

    def test_line_out_of_range_keeps_only_v1(self) -> None:
        rec = IdentityBuilder("a = 1\n", Language.PYTHON, None).record("R", "a.py", 9, v1="ff")
        assert rec.keys == {"v1": "ff"}


class TestJavaScriptScope:
    JS = f"""
        class A {{
          get(x) {{
            const y = {EV}(x);
            return y;
          }}
        }}
        const g = (q) => {{ return {EV}(q); }};
        obj.k = function () {{ return {EV}(1); }};
        function f(a) {{
          return {EV}(a);
        }}
        {EV}(2);
        """

    def test_scopes(self) -> None:
        recs = _records(self.JS, rule="CG-SEC-101", filename="a.js")
        assert [r.scope for r in recs] == ["A.get", "g", "obj.k", "f", ""]

    def test_header_of_a_function_declaration(self) -> None:
        src = "function f(a,\n  b) {\n  return 1;\n}\n"
        tree = support_for(Language.JAVASCRIPT).parse(src, "a.js").root.native  # type: ignore[union-attr]
        rec = IdentityBuilder(src, Language.JAVASCRIPT, tree).record("Q", "a.js", 1)
        assert rec.header is True and rec.scope == "" and rec.key("body")
        assert scope_at(src, Language.JAVASCRIPT, tree, 3) == "f"


# ---------------------------------------------------------------------------
# The matcher
# ---------------------------------------------------------------------------


class TestPasses:
    def test_exact_key(self) -> None:
        old = _records(f"def h(a):\n    return {EV}(a)\n")
        new = _records(f"import os\n\ndef h(a):\n    return {EV}(a)\n")
        assert _pairs(old, new) == [(0, 0, "stmt", False)]

    def test_scope_free_fallback(self) -> None:
        old = _records(f"def h(a):\n    return {EV}(a)\n")
        new = _records(f"def k(a):\n    return {EV}(a)\n")
        assert _pairs(old, new) == [(0, 0, "nscope", False)]

    def test_identifier_fallback_follows_a_rename_only(self) -> None:
        old = _records(f"def h(r):\n    data = r.x\n    return {EV}(data)\n")
        renamed = _records(f"def h(r):\n    payload = r.x\n    return {EV}(payload)\n")
        assert _pairs(old, renamed) == [(0, 0, "ident", False)]
        # ``a`` still exists in the new function: ``eval(b)`` is a new statement.
        old2 = _records(f"def h(a):\n    return {EV}(a)\n")
        new2 = _records(f"def h(a, b):\n    return {EV}(b)\n")
        assert _pairs(old2, new2) == []

    def test_body_fallback_for_headers(self) -> None:
        old = _records(
            "def f(a):\n    if a:\n        return 1\n    return 2\n", rule="Q", lines=[1]
        )
        new = _records(
            "def g(a, b):\n    if a:\n        return 1\n    return 2\n", rule="Q", lines=[1]
        )
        assert _pairs(old, new) == [(0, 0, "body", False)]

    def test_similarity_fallback(self) -> None:
        old = _records(f"def h(d):\n    return {EV}(d)\n")
        new = _records(f"def h(d):\n    return {EV}(d.strip())\n")
        [(i, j, name, amb)] = _pairs(old, new)
        assert (i, j, name, amb) == (0, 0, "sim", False)
        assert _pairs(old, new, similarity_threshold=0.9) == []
        assert _pairs(old, new, passes=("stmt", "nscope")) == []

    def test_rules_never_pair(self) -> None:
        old = _records(f"def h(a):\n    return {EV}(a)\n", rule="A")
        new = _records(f"def h(a):\n    return {EV}(a)\n", rule="B")
        assert _pairs(old, new) == []

    def test_v1_pass_for_old_baselines(self) -> None:
        old = [IdentityRecord.from_fingerprint("A", "a.py", 0, "abc")]
        new = [IdentityRecord.from_fingerprint("A", "a.py", 3, "abc")]
        assert _pairs(old, new) == [(0, 0, "v1", False)]


class TestTieBreaking:
    TWIN = f"def handler(data):\n    out = {EV}(data)\n    out = {EV}(data)\n    return out\n"

    def test_copy_above_keeps_the_original(self) -> None:
        old = _records(f"def handler(data):\n    out = {EV}(data)\n    return out\n")
        new = _records(self.TWIN)
        [(i, j, _name, ambiguous)] = _pairs(old, new)
        assert (i, j) == (0, 1)  # the original, which kept its following line
        assert ambiguous is True  # the copy kept the preceding line: conflicting evidence

    def test_copy_removed_pairs_the_survivor(self) -> None:
        old = _records(self.TWIN)
        new = _records(f"def handler(data):\n    out = {EV}(data)\n    return out\n")
        pairs = _pairs(old, new)
        assert len(pairs) == 1 and pairs[0][1] == 0

    def test_equal_candidates_without_context_are_a_guess(self) -> None:
        src = f"a = {EV}(x)\nb = {EV}(x)\n"
        old = [
            IdentityRecord("R", "f", 1, keys={"stmt": "k"}),
            IdentityRecord("R", "f", 2, keys={"stmt": "k"}),
        ]
        new = [
            IdentityRecord("R", "f", 2, keys={"stmt": "k"}),
            IdentityRecord("R", "f", 4, keys={"stmt": "k"}),
        ]
        assert src  # the records above stand for two equal statements
        pairs = _pairs(old, new)
        assert sorted(i for i, _j, _n, _a in pairs) == [0, 1]
        assert sorted(j for _i, j, _n, _a in pairs) == [0, 1]
        assert all(a for _i, _j, _n, a in pairs)

    def test_large_groups_pair_in_line_order(self) -> None:
        old = [IdentityRecord("R", "f", n, keys={"stmt": "k"}) for n in range(1, 80)]
        new = [IdentityRecord("R", "f", n + 3, keys={"stmt": "k"}) for n in range(1, 81)]
        pairs = match(old, new, MatchConfig(group_cap=10))
        assert len(pairs) == 79 and all(m.ambiguous for m in pairs)
        assert [m.new for m in pairs] == list(range(79))

    def test_strict_match_never_steals_from_a_loose_one(self) -> None:
        # The exact key pairs first; the renamed-scope copy is left for nscope.
        old = _records(f"def h(a):\n    return {EV}(a)\n\ndef k(a):\n    return {EV}(a)\n")
        new = _records(f"def h(a):\n    return {EV}(a)\n\ndef m(a):\n    return {EV}(a)\n")
        assert sorted(_pairs(old, new)) == [(0, 0, "stmt", False), (1, 1, "nscope", False)]


class TestSimilarity:
    def test_jaccard(self) -> None:
        assert jaccard(frozenset("ab"), frozenset("bc")) == 1 / 3
        assert jaccard(frozenset(), frozenset("a")) == 0.0

    def test_cap_skips_large_groups(self) -> None:
        old = [IdentityRecord("R", "f", n, tokens=frozenset({"a", str(n)})) for n in range(5)]
        new = [IdentityRecord("R", "f", n, tokens=frozenset({"a", str(n)})) for n in range(5)]
        assert match(old, new, MatchConfig(similarity_cap=2, similarity_threshold=0.5)) == []
        assert len(match(old, new, MatchConfig(similarity_threshold=0.5))) == 5

    def test_same_scope_preferred(self) -> None:
        old = [IdentityRecord("R", "f", 1, scope="a", tokens=frozenset("xyz"))]
        new = [
            IdentityRecord("R", "f", 1, scope="b", tokens=frozenset("xyz")),
            IdentityRecord("R", "f", 9, scope="a", tokens=frozenset("xyz")),
        ]
        [m] = match(old, new)
        assert m.new == 1


class TestPerformance:
    def test_hundred_thousand_findings(self) -> None:
        rng = random.Random(7)
        n = 100_000
        old = []
        new = []
        for k in range(n):
            key = f"k{rng.randrange(n // 2)}"  # about two copies per key
            old.append(IdentityRecord("R", "f", k, keys={"stmt": key, "ctx_next": f"c{k}"}))
            new.append(IdentityRecord("R", "f", k + 5, keys={"stmt": key, "ctx_next": f"c{k}"}))
        start = time.perf_counter()
        pairs = match(old, new)
        assert len(pairs) == n
        assert time.perf_counter() - start < 10


# ---------------------------------------------------------------------------
# File pairing
# ---------------------------------------------------------------------------


class TestFilePairs:
    def test_same_path_then_renames_then_content(self) -> None:
        pairs = pair_files(
            ["a.py", "b.py", "c.py", "d.py"],
            ["a.py", "b2.py", "c2.py", "e.js"],
            renames={"b.py": "b2.py"},
            old_keys={"c.py": ["h1", "h2", "h3"], "d.py": ["h9"]},
            new_keys={"c2.py": ["h1", "h2", "h4"], "e.js": ["h9"]},
        )
        assert [(p.old, p.new, p.how) for p in pairs] == [
            ("a.py", "a.py", "path"),
            ("b.py", "b2.py", "rename"),
            ("c.py", "c2.py", "content"),
        ]

    def test_content_threshold_and_switch(self) -> None:
        kw = {
            "old_keys": {"c.py": ["h1", "h2", "h3", "h4"]},
            "new_keys": {"c2.py": ["h1", "h5", "h6", "h7"]},
        }
        assert pair_files(["c.py"], ["c2.py"], **kw) == []  # type: ignore[arg-type]
        loose = PairConfig(content_threshold=0.1)
        assert len(pair_files(["c.py"], ["c2.py"], config=loose, **kw)) == 1  # type: ignore[arg-type]
        off = PairConfig(content_threshold=0.1, pair_by_content=False)
        assert pair_files(["c.py"], ["c2.py"], config=off, **kw) == []  # type: ignore[arg-type]


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_git_renames_since(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "old.py").write_text("x = 1\ny = 2\nz = 3\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    commit = gitdiff.head_commit(tmp_path)
    assert commit and len(commit) == 40
    (tmp_path / "old.py").rename(tmp_path / "new.py")
    _git(tmp_path, "add", "-A")
    assert gitdiff.renames_since(commit, root=tmp_path) == {"old.py": "new.py"}
    assert gitdiff.renames_since("0" * 40, root=tmp_path) is None
    assert gitdiff.head_commit(tmp_path / "nowhere") is None
