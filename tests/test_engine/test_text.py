# SPDX-License-Identifier: Apache-2.0
"""Tests for splitting source into parser-numbered lines."""

from __future__ import annotations

import pytest

from codeguard.engine.text import split_lines


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("", []),
        ("a", ["a"]),
        ("a\n", ["a"]),
        ("a\nb", ["a", "b"]),
        ("a\r\nb\r\n", ["a", "b"]),
        ("a\rb\r", ["a", "b"]),
        ("a\n\nb\n", ["a", "", "b"]),
        ("a\r\n\rb", ["a", "", "b"]),
    ],
)
def test_matches_splitlines_on_newlines(source: str, expected: list[str]) -> None:
    assert split_lines(source) == expected == source.splitlines()


def test_other_line_breaks_stay_inside_the_line() -> None:
    src = "a\x0bb\x0cc\x1cd\x1de\x1ef\x85g\u2028h\u2029i\nj\n"
    assert split_lines(src) == ["a\x0bb\x0cc\x1cd\x1de\x1ef\x85g\u2028h\u2029i", "j"]
