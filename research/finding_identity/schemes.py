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
| sonar         | SonarQube issue tracking: multi-pass matcher (:mod:`trackers`)     |
| bandit        | ``bandit -b baseline.json``: message, severity, confidence, CWE   |
| semgrep       | Semgrep ``match_based_id`` (Semgrep findings only)                 |

``sonar`` and ``bandit`` decide matches with an algorithm (see :mod:`trackers`); their keys
here hold what that algorithm compares and serve the collision count.
"""

from __future__ import annotations

import ast
import hashlib
import sys
from array import array
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from codeguard.engine import fingerprint as cg_fp

from .trackers import sonar_line_hash

PRIMARY_SCHEMES = ("line", "line_text", "github", "codeguard")
ABLATION_SCHEMES = ("cg_no_scope", "cg_no_mask", "cg_raw")
#: Matching methods of shipped tools that apply to findings from any analyzer.
TOOL_SCHEMES = ("sonar", "bandit")
#: Schemes every analyzer supports.
ALL_SCHEMES = PRIMARY_SCHEMES + ABLATION_SCHEMES + TOOL_SCHEMES
#: Needs Semgrep's rule formula and metavariable bindings, so Semgrep findings only.
SEMGREP_SCHEMES = ("semgrep",)
ANALYZERS = ("codeguard", "bandit", "semgrep")


def schemes_for(analyzer: str) -> tuple[str, ...]:
    """The schemes the harness can compute for findings from *analyzer*."""
    if analyzer not in ANALYZERS:
        raise ValueError(f"unknown analyzer {analyzer!r}")
    return ALL_SCHEMES + SEMGREP_SCHEMES if analyzer == "semgrep" else ALL_SCHEMES


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
# Semgrep match_based_id
# ---------------------------------------------------------------------------
# Port of Semgrep 1.180.0 (PyPI semgrep==1.180.0), LGPL-2.1, Copyright Semgrep Inc.:
#   semgrep/rule.py        Rule.formula_string             the rule's patterns as one string
#   semgrep/rule_match.py  RuleMatch.get_match_based_key   (formula with metavariables
#                                                           replaced by their bound code,
#                                                           path, rule id)
#                          RuleMatch.get_match_based_id    blake2b(str(key)) + "_" + index
#                          RuleMatches.add                 index: how many earlier matches in
#                                                           the scan share the key
# The CLI emits the value as `extra.fingerprint` in JSON and as
# `fingerprints["matchBasedId/v1"]` in SARIF (both redacted to "requires login" unless an
# app token is set). The ID does not contain the line, the column or the matched code
# beyond the metavariable bindings: a rule without metavariables gives every match in a
# file the same key, told apart only by its ordinal. Matches are counted in the order
# semgrep-core reports them, which for one file is the order of the JSON results.

#: semgrep.rule_lang.RuleValidation.PATTERN_KEYS in semgrep 1.180.0.
SEMGREP_PATTERN_KEYS = (
    "join",
    "match",
    "pattern",
    "pattern-either",
    "pattern-regex",
    "pattern-sinks",
    "pattern-sources",
    "patterns",
    "postprocessor-patterns",
    "request",
    "response",
    "taint",
)


def semgrep_formula_string(rule: Mapping[str, Any]) -> str:
    """``Rule.formula_string``: every pattern of the rule, sorted and joined by spaces."""

    def subrules(raw: object) -> str:
        parts: list[str] = []
        if isinstance(raw, str):
            parts.append(raw)
        elif isinstance(raw, dict):
            for key in sorted(raw):
                if raw.get(key) is not None:
                    parts.append(subrules(raw[key]))
        elif isinstance(raw, list):
            parts.extend(subrules(p) for p in raw)
        else:
            raise ValueError(f"unexpected pattern value {raw!r}")
        return " ".join(sorted(parts))

    try:
        parts: list[str] = []
        for key in sorted(SEMGREP_PATTERN_KEYS):
            raw = rule.get(key)
            if raw is not None:
                parts.append(subrules(raw))
                if key == "join" and "on" in raw:
                    # list += str adds the characters one by one, as in the original.
                    parts += subrules(raw["on"])
        result = " ".join(sorted(parts))
        if not result:
            raise ValueError("no hashable patterns")
    except ValueError:
        result = ""
    return result


@dataclass(frozen=True)
class SemgrepMatch:
    """What ``match_based_id`` reads from one Semgrep result."""

    rule_id: str
    path: str
    formula: str
    #: ``{"$X": abstract_content}`` in the order Semgrep reports the bindings.
    metavars: Mapping[str, str]


def _semgrep_key(m: SemgrepMatch) -> str:
    formula = m.formula
    # Longest names first, so that $REQ does not replace the prefix of $REQFUNC.
    for name in sorted(m.metavars, key=len, reverse=True):
        formula = formula.replace(name, m.metavars[name])
    # str() of the tuple (formula, pathlib.PosixPath(path), rule id) on a POSIX system.
    path = f"PosixPath({str(PurePosixPath(m.path))!r})"
    return f"({formula!r}, {path}, {m.rule_id!r})"


def semgrep_match_based_ids(matches: Sequence[SemgrepMatch]) -> list[str]:
    """``match_based_id`` of each match, for the matches of one scan in report order."""
    counts: dict[str, int] = {}
    out = []
    for m in matches:
        key = _semgrep_key(m)
        index = counts.get(key, 0)
        counts[key] = index + 1
        out.append(f"{hashlib.blake2b(key.encode()).hexdigest()}_{index}")
    return out


# ---------------------------------------------------------------------------
# Per-file context and key computation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FindingMeta:
    """Analyzer fields that some tools' identity methods compare, beyond rule and line.

    For Bandit's baseline equality: ``message`` is ``issue_text``, ``test`` the plugin
    name, and the rule ID is ``test_id``. Other analyzers fill the closest fields.
    """

    message: str = ""
    severity: str = ""
    confidence: str = ""
    cwe: str = ""
    test: str = ""
    #: The ``match_based_id`` Semgrep emitted, for the ``semgrep`` scheme.
    semgrep_id: str | None = None


def bandit_key(rule: str, path: str, meta: FindingMeta) -> str:
    """The fields ``bandit.core.issue.Issue.__eq__`` compares (``fname`` is the path)."""
    return _sha(
        "bandit", meta.message, meta.severity, meta.cwe, meta.confidence, path, meta.test, rule
    )


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


def keys_for(
    rule: str,
    line: int,
    ctx: FileContext,
    schemes: Sequence[str],
    *,
    meta: FindingMeta | None = None,
) -> dict[str, str]:
    """The key of one finding under each of *schemes*."""
    meta = meta or FindingMeta()
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
        elif name == "sonar":
            # The weakest pass of SonarQube's tracker: same rule and line hash.
            out[name] = _sha(rule, ctx.path, sonar_line_hash(raw))
        elif name == "bandit":
            out[name] = bandit_key(rule, ctx.path, meta)
        elif name == "semgrep":
            if meta.semgrep_id is None:
                raise ValueError("the semgrep scheme needs the match_based_id of a Semgrep finding")
            out[name] = meta.semgrep_id
        else:
            raise ValueError(f"unknown scheme {name!r}")
    return out
