# SPDX-License-Identifier: Apache-2.0
"""Convert CodeGuard positions to LSP positions.

CodeGuard columns are 1-indexed UTF-8 **byte** offsets (what ``ast`` and
tree-sitter report).  LSP positions are 0-indexed and count UTF-16 code units.
The two agree only on ASCII lines, so every conversion needs the line's text.
"""

from __future__ import annotations

from typing import Any

from codeguard.engine.finding import Location, TextEdit

LspPosition = dict[str, int]
LspRange = dict[str, LspPosition]


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def byte_to_utf16(line_text: str, byte_offset: int) -> int:
    """UTF-16 offset of the character at 0-indexed *byte_offset* within *line_text*."""
    if byte_offset <= 0:
        return 0
    data = line_text.encode("utf-8")
    prefix = data[:byte_offset].decode("utf-8", "ignore")
    # Past the known text (or no text at all): count the rest one-to-one.
    return _utf16_len(prefix) + max(byte_offset - len(data), 0)


def utf16_to_byte(line_text: str, utf16_offset: int) -> int:
    """0-indexed UTF-8 byte offset for a UTF-16 *utf16_offset* within *line_text*."""
    units = 0
    for i, ch in enumerate(line_text):
        if units >= utf16_offset:
            return len(line_text[:i].encode("utf-8"))
        units += 2 if ord(ch) > 0xFFFF else 1
    return len(line_text.encode("utf-8"))


class LineIndex:
    """Lines of one document, for position conversion."""

    def __init__(self, text: str) -> None:
        self.lines = text.split("\n")

    def line(self, index: int) -> str:
        if 0 <= index < len(self.lines):
            return self.lines[index].rstrip("\r")
        return ""

    def position(self, line: int, col: int) -> LspPosition:
        """LSP position for a 1-indexed *line* and 1-indexed byte *col*."""
        index = max(line - 1, 0)
        return {"line": index, "character": byte_to_utf16(self.line(index), col - 1)}

    def line_end(self, index: int) -> LspPosition:
        return {"line": index, "character": _utf16_len(self.line(index))}

    def location_range(self, loc: Location) -> LspRange:
        start = self.position(loc.line, loc.col)
        end_line = loc.end_line or loc.line
        if loc.end_col is not None:
            end = self.position(end_line, loc.end_col)
        else:
            end = {"line": start["line"], "character": start["character"] + 1}
        if (end["line"], end["character"]) <= (start["line"], start["character"]):
            end = {"line": start["line"], "character": start["character"] + 1}
        return {"start": start, "end": end}

    def text_edit(self, edit: TextEdit) -> dict[str, Any]:
        return {
            "range": {
                "start": self.position(edit.start_line, edit.start_col),
                "end": self.position(edit.end_line, edit.end_col),
            },
            "newText": edit.replacement,
        }


def contains(rng: LspRange, pos: LspPosition) -> bool:
    start, end = rng["start"], rng["end"]
    point = (pos["line"], pos["character"])
    return (start["line"], start["character"]) <= point <= (end["line"], end["character"])


def overlaps(a: LspRange, b: LspRange) -> bool:
    a0 = (a["start"]["line"], a["start"]["character"])
    a1 = (a["end"]["line"], a["end"]["character"])
    b0 = (b["start"]["line"], b["start"]["character"])
    b1 = (b["end"]["line"], b["end"]["character"])
    return a0 <= b1 and b0 <= a1
