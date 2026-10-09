# SPDX-License-Identifier: Apache-2.0
"""UTF-8 byte columns (CodeGuard) <-> UTF-16 characters (LSP)."""

from __future__ import annotations

from codeguard.engine.finding import Location, TextEdit
from codeguard.lsp.positions import LineIndex, byte_to_utf16, contains, overlaps, utf16_to_byte


def test_ascii_is_identity() -> None:
    assert byte_to_utf16("hello", 3) == 3
    assert utf16_to_byte("hello", 3) == 3


def test_multibyte_and_astral_characters() -> None:
    line = 'x = "é😀" + y'
    # bytes: x(1) space(1) =(1) space(1) "(1) é(2) 😀(4) "(1) ...
    y_byte = line.encode("utf-8").index(b"y")
    y_utf16 = len(line[: line.index("y")].encode("utf-16-le")) // 2
    assert byte_to_utf16(line, y_byte) == y_utf16
    assert utf16_to_byte(line, y_utf16) == y_byte


def test_offset_past_known_text_counts_one_to_one() -> None:
    assert byte_to_utf16("", 4) == 4


def test_location_range_and_text_edit_with_emoji() -> None:
    index = LineIndex('s = "😀"; t = d.keys()\r\n')
    line = index.line(0)
    start = line.encode("utf-8").index(b"d.keys") + 1
    end = start + len("d.keys()")
    rng = index.location_range(Location("f.py", 1, start, 1, end))
    expected_start = len(line[: line.index("d.keys")].encode("utf-16-le")) // 2
    assert rng["start"] == {"line": 0, "character": expected_start}
    assert rng["end"]["character"] == expected_start + len("d.keys()")
    edit = index.text_edit(TextEdit(1, start, 1, end, "d"))
    assert edit["range"] == rng and edit["newText"] == "d"
    assert index.line_end(0) == {"line": 0, "character": len(line.encode("utf-16-le")) // 2}


def test_degenerate_range_widened() -> None:
    rng = LineIndex("abc").location_range(Location("f", 1, 2, 1, 2))
    assert rng["end"]["character"] == rng["start"]["character"] + 1


def test_contains_and_overlaps() -> None:
    rng = {"start": {"line": 1, "character": 2}, "end": {"line": 1, "character": 6}}
    assert contains(rng, {"line": 1, "character": 4})
    assert not contains(rng, {"line": 2, "character": 0})
    other = {"start": {"line": 1, "character": 6}, "end": {"line": 3, "character": 0}}
    assert overlaps(rng, other)
    far = {"start": {"line": 5, "character": 0}, "end": {"line": 5, "character": 1}}
    assert not overlaps(rng, far)
