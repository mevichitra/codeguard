"""Each transformation: valid output, exact line map, behaviour kept where it should be."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("libcst")

from research.finding_identity.schemes import split_lines
from research.finding_identity.transforms import (
    BELOW_LINE,
    TOP_LINES,
    AIRefactor,
    NotApplicable,
    Source,
    deterministic_transforms,
    node_line_map,
    split_keepends,
)

SAMPLE = '''\
"""Sample module."""
from __future__ import annotations

import subprocess

SCALE = 3


def helper(x):
    return x * SCALE


def compute(expr, items):
    total = helper(len(items))
    result = eval(expr, {"n": total})
    for item in items:
        result += item
    return result


class Box:
    def __init__(self, base):
        self.base = base

    def get(self, expr):
        value = eval(expr) + self.base
        return value

    def use(self):
        return self.get("1 + 1")


def run(cmd):
    return subprocess.call(cmd, shell=True)
'''
LINES = split_lines(SAMPLE)


def line_of(marker: str, lines: list[str] = LINES) -> int:
    return next(i for i, text in enumerate(lines, start=1) if marker in text)


COMPUTE = line_of("result = eval(")
GET = line_of("value = eval(")
TRANSFORMS = deterministic_transforms()
#: Transformations that keep the file's behaviour (checked by running it).
PRESERVING = (
    "reformat",
    "insert_top",
    "insert_below",
    "rename_local",
    "rename_function",
    "move_function",
    "extract_helper",
)
#: Transformations that only move or copy lines (indentation aside).
MOVING = ("insert_top", "insert_below", "move_function", "extract_helper", "duplicate_above",
          "duplicate_below")  # fmt: skip


def behaviour(text: str) -> tuple[Any, ...]:
    ns: dict[str, Any] = {}
    exec(compile(text, "sample.py", "exec"), ns)  # noqa: S102  (trusted test code)
    compute = ns.get("compute") or ns["compute_renamed"]
    box = ns["Box"](5)
    get = getattr(box, "get", None) or box.get_renamed
    return compute("n * 2", [1, 2]), box.use(), get("2"), ns["helper"](4)


def apply(name: str, line: int) -> tuple[str, dict[int, int]]:
    if name == "reformat":
        pytest.importorskip("black")
    edit = TRANSFORMS[name](Source(SAMPLE), line)
    ast.parse(edit.text)
    return edit.text, edit.line_map


def test_split_keepends_counts_lines_like_the_parser() -> None:
    text = "a\r\nb\rc\n\x0cd\ne"
    assert [ln.rstrip("\r\n") for ln in split_keepends(text)] == split_lines(text)
    assert split_keepends("x\n") == ["x\n"]


@pytest.mark.parametrize("line", [COMPUTE, GET])
@pytest.mark.parametrize("name", list(TRANSFORMS))
def test_line_map_is_exact(name: str, line: int) -> None:
    if (name, line) == ("change_literal", GET):
        pytest.skip("no literal on the line (see test_not_applicable)")
    text, line_map = apply(name, line)
    new = split_lines(text)
    if name != "reformat":
        assert len(set(line_map.values())) == len(line_map), "two old lines on one new line"
    if name in MOVING:
        for old, target in line_map.items():
            assert LINES[old - 1].strip() == new[target - 1].strip(), (old, target)
    elif name != "reformat":
        changed = [old for old, target in line_map.items() if LINES[old - 1] != new[target - 1]]
        assert changed
        if name != "rename_function":  # renames the def line, not the flagged line
            assert line in changed


@pytest.mark.parametrize("line", [COMPUTE, GET])
@pytest.mark.parametrize("name", PRESERVING)
def test_behaviour_is_preserved(name: str, line: int) -> None:
    text, _ = apply(name, line)
    assert text != SAMPLE
    assert behaviour(text) == behaviour(SAMPLE)


def test_insert_top_goes_below_future_imports() -> None:
    text, line_map = apply("insert_top", COMPUTE)
    new = split_lines(text)
    assert new[2:4] == list(TOP_LINES)
    assert line_map[2] == 2 and line_map[COMPUTE] == COMPUTE + 2


def test_insert_below_follows_the_flagged_statement() -> None:
    text, line_map = apply("insert_below", COMPUTE)
    new = split_lines(text)
    assert line_map[COMPUTE] == COMPUTE
    assert new[COMPUTE] == "    " + BELOW_LINE
    assert line_map[COMPUTE + 1] == COMPUTE + 2


def test_rename_local_renames_every_use_in_the_function() -> None:
    text, _ = apply("rename_local", COMPUTE)
    assert text.count("result_v2") == 3
    assert "value = eval" in text


def test_rename_function_updates_method_calls() -> None:
    text, _ = apply("rename_function", GET)
    assert "def get_renamed(self, expr):" in text
    assert 'self.get_renamed("1 + 1")' in text


def test_move_function_swaps_with_the_previous_function() -> None:
    text, line_map = apply("move_function", COMPUTE)
    new = split_lines(text)
    assert new.index("def compute(expr, items):") < new.index("def helper(x):")
    assert new[line_map[COMPUTE] - 1] == LINES[COMPUTE - 1]


def test_extract_helper_moves_the_statement_into_a_helper() -> None:
    text, line_map = apply("extract_helper", GET)
    new = split_lines(text)
    target = line_map[GET]
    assert new[target - 2] == "def _get_extracted(expr, self):"
    assert new[target - 1] == "    value = eval(expr) + self.base"
    assert target < line_of("class Box:", new)
    assert "        value = _get_extracted(expr, self)" in new


@pytest.mark.parametrize("name", ["duplicate_above", "duplicate_below"])
def test_duplicate_adds_an_unmapped_copy(name: str) -> None:
    text, line_map = apply(name, COMPUTE)
    new = split_lines(text)
    copies = [k for k, t in enumerate(new, start=1) if t == LINES[COMPUTE - 1]]
    assert len(copies) == 2
    (unmapped,) = set(copies) - set(line_map.values())
    assert unmapped == (COMPUTE if name == "duplicate_above" else COMPUTE + 1)


def test_change_literal_changes_a_literal_on_the_line() -> None:
    text, line_map = apply("change_literal", COMPUTE)
    assert split_lines(text)[line_map[COMPUTE] - 1] == '    result = eval(expr, {"n_v2": total})'


@pytest.mark.parametrize(
    ("name", "marker"),
    [
        ("rename_local", "return subprocess.call"),  # only a parameter on the line
        ("rename_function", "self.base = base"),  # __init__
        ("extract_helper", "SCALE = 3"),  # module level
        ("duplicate_above", "def compute("),  # compound statement header
        ("change_literal", "value = eval("),  # no literal
    ],
)
def test_not_applicable(name: str, marker: str) -> None:
    with pytest.raises(NotApplicable):
        TRANSFORMS[name](Source(SAMPLE), line_of(marker))


def test_reformat_maps_split_lines_to_every_node_start() -> None:
    pytest.importorskip("black")
    text = (
        "x = foo(aaaaaaaaaaaaaaaa, bbbbbbbbbbbbbbbbbbbb, eval(ccccccccccccccccc), ddddddddddddd)\n"
    )
    edit = TRANSFORMS["reformat"](Source(text), 1)
    assert split_lines(edit.text)[3].strip() == "eval(ccccccccccccccccc),"
    assert edit.line_map == {1: 1}
    assert 4 in edit.alternatives[1]
    assert node_line_map(ast.parse(text), ast.parse(edit.text))[1] == edit.alternatives[1]


REFACTORED = """\
```python
def get(self, expr):
    return eval(expr) + self.base
```"""


def test_ai_refactor_uses_the_cache_and_a_line_diff(tmp_path: Path) -> None:
    prompts: list[str] = []

    def ask(prompt: str) -> str:
        prompts.append(prompt)
        return REFACTORED

    first = AIRefactor("some-model", tmp_path, ask=ask)
    edit = first(Source(SAMPLE), GET)
    assert edit.needs_review and "def get(self, expr):" in edit.review["old"]
    new = split_lines(edit.text)
    assert new[GET - 1] == "        return eval(expr) + self.base"
    # Ground truth from the line diff: the edited eval line still pairs with the old one.
    assert edit.line_map[GET] == GET
    assert edit.line_map[GET - 1] == GET - 1 and edit.line_map[GET + 2] == GET + 1
    assert GET + 1 not in edit.line_map  # "return value" was deleted
    assert behaviour(edit.text) == behaviour(SAMPLE)

    cached = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert cached["model"] == "some-model" and cached["response"] == REFACTORED
    offline = AIRefactor("some-model", tmp_path, offline=True)
    assert offline(Source(SAMPLE), GET).text == edit.text
    assert len(prompts) == 1 and offline.cache_hits == 1
    with pytest.raises(NotApplicable):
        AIRefactor("other-model", tmp_path, offline=True)(Source(SAMPLE), GET)


def test_ai_refactor_rejects_a_different_function(tmp_path: Path) -> None:
    ai = AIRefactor("m", tmp_path, ask=lambda _: "```python\ndef other(self):\n    pass\n```")
    with pytest.raises(NotApplicable):
        ai(Source(SAMPLE), GET)
