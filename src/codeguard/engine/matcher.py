# SPDX-License-Identifier: Apache-2.0
"""Pair the findings of one file version with those of another, one to one.

:func:`match` runs the identity keys of :mod:`codeguard.engine.identity` as passes,
strictest first.  Each pass groups the findings still unmatched on both sides by one
key and pairs the groups; a finding paired once is never paired again, so a loose key
cannot steal a strict match.  Inside a group with several candidates the tie is broken
by the neighbouring lines (``ctx_next`` first, then ``ctx_prev``) and then by line
distance; a pairing that line distance alone decided is marked *ambiguous*.  A final
pass pairs what is left of one rule by the Jaccard similarity of the statements'
token sets, for edited lines.

The function is pure and deterministic, and the research harness calls it on its own
observations, so the paper measures the code that ships.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from .identity import IdentityRecord

#: The pass names ``MatchConfig.passes`` accepts, in the default order.
PASSES = ("stmt", "v1", "nscope", "body", "ident", "sim")


@dataclass(frozen=True)
class MatchConfig:
    """What the matcher tries, and how loosely.

    ``passes``: the key passes to run, in order; ``"sim"`` is the similarity pass.
    ``similarity_threshold``: the least token-set Jaccard the similarity pass accepts.
    ``similarity_cap``: the similarity pass skips a (rule) group with more than this
    many unmatched findings on either side, keeping the cost bounded.
    ``group_cap``: a key group larger than this on either side is paired in line order
    without scoring the neighbours, again for cost.
    ``context_tiebreak``: whether the neighbouring lines take part in tie-breaking.
    ``same_scope_first``: in the similarity pass, prefer candidates in the same scope.
    """

    passes: tuple[str, ...] = PASSES
    similarity_threshold: float = 0.7
    similarity_cap: int = 64
    group_cap: int = 64
    context_tiebreak: bool = True
    same_scope_first: bool = True


DEFAULT_CONFIG = MatchConfig()


@dataclass(frozen=True)
class Match:
    """One pairing: index into the old list, index into the new list, the pass that
    made it, whether a tie-break had to guess, and the pass's score (1.0 for a key
    pass, the Jaccard similarity for the similarity pass)."""

    old: int
    new: int
    pass_name: str
    ambiguous: bool
    score: float = 1.0


def match(
    old: Sequence[IdentityRecord],
    new: Sequence[IdentityRecord],
    config: MatchConfig | None = None,
) -> list[Match]:
    """Pair *old* and *new* findings of one file (or one pair of renamed files).

    Returns the matches sorted by new index.  Findings of different rules never pair:
    every key includes the rule, and the similarity pass groups by rule.
    """
    cfg = config or DEFAULT_CONFIG
    matched_old: set[int] = set()
    matched_new: set[int] = set()
    out: list[Match] = []
    for name in cfg.passes:
        if len(matched_new) == len(new) or len(matched_old) == len(old):
            break
        if name == "sim":
            out.extend(_similarity_pass(old, new, matched_old, matched_new, cfg))
        else:
            out.extend(_key_pass(name, old, new, matched_old, matched_new, cfg))
    out.sort(key=lambda m: (m.new, m.old))
    return out


# ---------------------------------------------------------------------------
# Key passes
# ---------------------------------------------------------------------------


def _key_pass(
    name: str,
    old: Sequence[IdentityRecord],
    new: Sequence[IdentityRecord],
    matched_old: set[int],
    matched_new: set[int],
    cfg: MatchConfig,
) -> list[Match]:
    old_by: dict[str, list[int]] = defaultdict(list)
    for i, rec in enumerate(old):
        if i not in matched_old:
            key = rec.key(name)
            if key:
                old_by[key].append(i)
    new_by: dict[str, list[int]] = defaultdict(list)
    for j, rec in enumerate(new):
        if j not in matched_new:
            key = rec.key(name)
            if key and key in old_by:
                new_by[key].append(j)
    out: list[Match] = []
    gated = name == "ident"
    for key, news in new_by.items():
        olds = old_by[key]
        if gated:
            olds = [i for i in olds if any(identifier_gate(old[i], new[j]) for j in news)]
            news = [j for j in news if any(identifier_gate(old[i], new[j]) for i in olds)]
            if not olds or not news:
                continue
        if len(olds) == 1 and len(news) == 1:
            out.append(_take(olds[0], news[0], name, False, matched_old, matched_new))
            continue
        out.extend(
            _pair_group(olds, news, name, old, new, matched_old, matched_new, cfg, gated=gated)
        )
    return out


def identifier_gate(a: IdentityRecord, b: IdentityRecord) -> bool:
    """Whether a pairing that differs in identifiers is a rename and not a new name.

    An identifier masked on one side that still exists in the other side's scope was
    not renamed: ``eval(b)`` next to a surviving ``a`` is a new statement, while
    ``eval(payload)`` after ``data`` vanished from the function is the old one.
    Records without scope words (baseline entries) do not constrain the pairing.
    """
    gone_old = a.idents - b.idents
    if gone_old and b.scope_words and gone_old & b.scope_words:
        return False
    gone_new = b.idents - a.idents
    return not (gone_new and a.scope_words and gone_new & a.scope_words)


def _take(
    i: int, j: int, name: str, ambiguous: bool, matched_old: set[int], matched_new: set[int]
) -> Match:
    matched_old.add(i)
    matched_new.add(j)
    return Match(i, j, name, ambiguous)


def _context_score(a: IdentityRecord, b: IdentityRecord) -> int:
    """How many neighbouring lines agree; the following line counts double, so a copy
    pasted directly above the original leaves the original the better candidate."""
    score = 0
    nxt = a.key("ctx_next")
    if nxt and nxt == b.key("ctx_next"):
        score += 2
    prv = a.key("ctx_prev")
    if prv and prv == b.key("ctx_prev"):
        score += 1
    return score


def _pair_group(
    olds: list[int],
    news: list[int],
    name: str,
    old: Sequence[IdentityRecord],
    new: Sequence[IdentityRecord],
    matched_old: set[int],
    matched_new: set[int],
    cfg: MatchConfig,
    *,
    gated: bool = False,
) -> list[Match]:
    """Pair two groups of findings with equal keys, best candidates first."""
    out: list[Match] = []
    if len(olds) > cfg.group_cap or len(news) > cfg.group_cap:
        # Too many copies to score: pair in line order and say so.
        for i, j in zip(
            sorted(olds, key=lambda k: old[k].line),
            sorted(news, key=lambda k: new[k].line),
            strict=False,
        ):
            out.append(_take(i, j, name, True, matched_old, matched_new))
        return out
    # (-context score, line distance, old line, new line, old index, new index)
    cands: list[tuple[int, int, int, int, int, int]] = []
    for i in olds:
        for j in news:
            if gated and not identifier_gate(old[i], new[j]):
                continue
            ctx = _context_score(old[i], new[j]) if cfg.context_tiebreak else 0
            dist = abs(old[i].line - new[j].line)
            cands.append((-ctx, dist, old[i].line, new[j].line, i, j))
    cands.sort()
    scores_old: dict[int, list[int]] = defaultdict(list)
    scores_new: dict[int, list[int]] = defaultdict(list)
    for neg_ctx, _dist, _lo, _ln, i, j in cands:
        scores_old[i].append(-neg_ctx)
        scores_new[j].append(-neg_ctx)
    for neg_ctx, _dist, _lo, _ln, i, j in cands:
        if i in matched_old or j in matched_new:
            continue
        ctx = -neg_ctx
        ambiguous = _is_guess(ctx, scores_old[i]) or _is_guess(ctx, scores_new[j])
        out.append(_take(i, j, name, ambiguous, matched_old, matched_new))
    return out


def _is_guess(chosen: int, scores: list[int]) -> bool:
    """A pairing is a guess unless its context score beats every competitor's and no
    competitor has context evidence of its own (a pasted copy keeps one neighbour,
    the original the other: conflicting evidence, so both are reported in strict
    mode)."""
    others = list(scores)
    others.remove(chosen)
    return any(s >= chosen or (s > 0 and chosen < 3) for s in others)


# ---------------------------------------------------------------------------
# Similarity pass
# ---------------------------------------------------------------------------


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Token-set Jaccard similarity; 0 when either set is empty."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _similarity_pass(
    old: Sequence[IdentityRecord],
    new: Sequence[IdentityRecord],
    matched_old: set[int],
    matched_new: set[int],
    cfg: MatchConfig,
) -> list[Match]:
    old_by_rule: dict[str, list[int]] = defaultdict(list)
    for i, rec in enumerate(old):
        if i not in matched_old and rec.tokens:
            old_by_rule[rec.rule].append(i)
    new_by_rule: dict[str, list[int]] = defaultdict(list)
    for j, rec in enumerate(new):
        if j not in matched_new and rec.tokens and rec.rule in old_by_rule:
            new_by_rule[rec.rule].append(j)
    out: list[Match] = []
    for rule, news in new_by_rule.items():
        olds = old_by_rule[rule]
        if len(olds) > cfg.similarity_cap or len(news) > cfg.similarity_cap:
            continue
        # (-similarity, scope penalty, line distance, old line, new line, i, j)
        cands: list[tuple[float, int, int, int, int, int, int]] = []
        for i in olds:
            for j in news:
                sim = jaccard(old[i].tokens, new[j].tokens)
                if sim < cfg.similarity_threshold or not identifier_gate(old[i], new[j]):
                    continue
                penalty = int(cfg.same_scope_first and old[i].scope != new[j].scope)
                dist = abs(old[i].line - new[j].line)
                cands.append((-sim, penalty, dist, old[i].line, new[j].line, i, j))
        cands.sort()
        per_old: Counter[tuple[float, int, int]] = Counter((c[0], c[1], c[5]) for c in cands)
        per_new: Counter[tuple[float, int, int]] = Counter((c[0], c[1], c[6]) for c in cands)
        for neg_sim, penalty, _dist, _lo, _ln, i, j in cands:
            if i in matched_old or j in matched_new:
                continue
            ambiguous = per_old[(neg_sim, penalty, i)] > 1 or per_new[(neg_sim, penalty, j)] > 1
            matched_old.add(i)
            matched_new.add(j)
            out.append(Match(i, j, "sim", ambiguous, -neg_sim))
    return out
