# SPDX-License-Identifier: Apache-2.0
"""Split source text into lines the way parsers number them."""

from __future__ import annotations


def split_lines(source: str) -> list[str]:
    """Split *source* on ``\\r\\n``, ``\\r`` and ``\\n`` only.

    Line *N* of a finding is ``split_lines(source)[N - 1]``.  Unlike
    :meth:`str.splitlines`, form feeds, vertical tabs, ``\\x1c``-``\\x1e``,
    ``\\x85``, U+2028 and U+2029 do not end a line -- ``ast`` and tree-sitter
    don't count them either.  Like :meth:`str.splitlines`, a trailing line
    break does not produce an extra empty line.
    """
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines
