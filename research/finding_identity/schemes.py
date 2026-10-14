"""Identity schemes: ways of deciding that two findings are "the same finding".

A scheme maps one finding in one file version to a key. Two findings in consecutive
versions of a file are matched when their keys are equal. Every scheme includes the
rule ID and the file path, so a finding never matches across rules or across files.

| Scheme        | Key built from                                                     |
|---------------|--------------------------------------------------------------------|
| line          | line number                                                        |
| line_text     | exact text of the flagged line                                     |
| github        | GitHub code scanning ``primaryLocationLineHash`` (ported below)    |
| codeguard     | enclosing scope + normalized statement (CodeGuard ``codeguard/v1``)|
| cg_no_scope   | ablation: codeguard without the enclosing scope                    |
| cg_no_mask    | ablation: codeguard without masking string and number literals    |
| cg_raw        | ablation: codeguard without any normalization (scope + raw line)  |
"""

from __future__ import annotations

import ast
import hashlib
import sys
from array import array
from collections.abc import Sequence
from dataclasses import dataclass

from codeguard.engine import fingerprint as cg_fp

PRIMARY_SCHEMES = ("line", "line_text", "github", "codeguard")
ABLATION_SCHEMES = ("cg_no_scope", "cg_no_mask", "cg_raw")
ALL_SCHEMES = PRIMARY_SCHEMES + ABLATION_SCHEMES


# ---------------------------------------------------------------------------
# GitHub code scanning line hash
# ---------------------------------------------------------------------------
# Port of hash() in github/codeql-action src/fingerprints.ts (MIT License,
# Copyright GitHub, Inc.). For every line it computes a rolling hash over the next
# 100 characters, ignoring spaces and tabs, starting at the beginning of the line and
# running into the following lines. CR and CRLF are normalized to LF. Arithmetic is
# 64-bit wrapping (the original uses the `long` package). The value is
# "<hex>:<n>", where n counts how many times the same hash occurred earlier in the
# file. JavaScript strings are UTF-16, so the port walks UTF-16 code units.

_BLOCK_SIZE = 100
_MOD = 37
_MASK64 = (1 << 64) - 1
_FIRST_MOD = pow(_MOD, _BLOCK_SIZE, 1 << 64)
_TAB, _SPACE, _LF, _CR, _EOF = 9, 32, 10, 13, 65535


def _utf16_units(text: str) -> array[int]:
    units = array("H")
    units.frombytes(text.encode("utf-16-le", "surrogatepass"))
    if sys.byteorder == "big":
        units.byteswap()
    return units


def github_line_hashes(text: str) -> dict[int, str]:
    """Return ``{line number: primaryLocationLineHash}`` for every line of *text*."""
    window = [0] * _BLOCK_SIZE
    line_numbers = [-1] * _BLOCK_SIZE
    out: dict[int, str] = {}
    counts: dict[str, int] = {}
    hash_raw = 0
    index = 0
    line_number = 0
    line_start = True
    prev_cr = False

    def output_hash() -> None:
        value = format(hash_raw, "x")
        counts[value] = counts.get(value, 0) + 1
        out[line_numbers[index]] = f"{value}:{counts[value]}"
        line_numbers[index] = -1

    def update_hash(current: int) -> None:
        nonlocal hash_raw, index
        begin = window[index]
        window[index] = current
        hash_raw = (_MOD * hash_raw + current - _FIRST_MOD * begin) & _MASK64
        index = (index + 1) % _BLOCK_SIZE

    def process(current: int) -> None:
        nonlocal prev_cr, line_start, line_number
        if current in (_SPACE, _TAB) or (prev_cr and current == _LF):
            prev_cr = False
            return
        if current == _CR:
            current = _LF
            prev_cr = True
        else:
            prev_cr = False
        if line_numbers[index] != -1:
            output_hash()
        if line_start:
            line_start = False
            line_number += 1
            line_numbers[index] = line_number
        if current == _LF:
            line_start = True
        update_hash(current)

    for unit in _utf16_units(text):
        process(unit)
    process(_EOF)
    for _ in range(_BLOCK_SIZE):
        if line_numbers[index] != -1:
            output_hash()
        update_hash(0)
    return out


# ---------------------------------------------------------------------------
# Per-file context and key computation
# ---------------------------------------------------------------------------


def split_lines(text: str) -> list[str]:
    """Split on LF, CRLF and CR only: the line breaks parsers count for line numbers."""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _sha(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]


def _strip_comments_and_space(text: str) -> str:
    # CodeGuard's normalization without the literal masking step. The regexes are
    # CodeGuard's own, so the ablation stays in sync with the tool.
    return str(cg_fp._WS_RE.sub("", cg_fp._COMMENT_RE.sub("", text)))


@dataclass
class FileContext:
    """What every scheme may read about one version of one file."""

    path: str
    text: str
    lines: list[str]
    tree: ast.Module | None
    github: dict[int, str]

    @classmethod
    def build(cls, path: str, text: str, *, is_python: bool) -> FileContext:
        tree = None
        if is_python:
            try:
                tree = ast.parse(text)
            except (SyntaxError, ValueError):
                tree = None
        return cls(path, text, split_lines(text), tree, github_line_hashes(text))

    def raw_line(self, line: int) -> str:
        return self.lines[line - 1] if 1 <= line <= len(self.lines) else ""

    def scope(self, line: int) -> str:
        return cg_fp.python_scope(self.tree, line) if self.tree is not None else ""


def keys_for(rule: str, line: int, ctx: FileContext, schemes: Sequence[str]) -> dict[str, str]:
    """The key of one finding under each of *schemes*."""
    raw = ctx.raw_line(line)
    scope = ctx.scope(line)
    out: dict[str, str] = {}
    for name in schemes:
        if name == "line":
            out[name] = _sha(rule, ctx.path, str(line))
        elif name == "line_text":
            out[name] = _sha(rule, ctx.path, raw)
        elif name == "github":
            out[name] = _sha(rule, ctx.path, ctx.github.get(line, ""))
        elif name == "codeguard":
            out[name] = cg_fp.compute(rule, ctx.path, ctx.text, line, scope=scope)
        elif name == "cg_no_scope":
            out[name] = cg_fp.compute(rule, ctx.path, ctx.text, line, scope="")
        elif name == "cg_no_mask":
            out[name] = _sha(rule, ctx.path, scope, _strip_comments_and_space(raw))
        elif name == "cg_raw":
            out[name] = _sha(rule, ctx.path, scope, raw)
        else:
            raise ValueError(f"unknown scheme {name!r}")
    return out
