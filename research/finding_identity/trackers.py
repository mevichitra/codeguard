"""Matchers for schemes that real tools implement as an algorithm rather than a key.

Key schemes pair findings with equal keys (:func:`matching.scheme_pairs`). Two tools decide
"same finding" differently, so their schemes plug in a matcher here instead:

- ``sonar``: SonarQube's multi-pass issue tracker, ported line by line below. A renamed
  file's findings are tracked against the old file, as in a pull-request analysis, which
  takes renames from the SCM.
- ``sonar_branch``: the same tracker as a branch analysis runs it. A renamed file is the
  old file only if SonarQube's own file move detection says so (:func:`sonar_file_moved`);
  otherwise its findings are all new.
- ``bandit``: ``bandit -b baseline.json``, which asks only whether an *equal* issue exists
  in the baseline (set membership, not one-to-one pairing).

A matcher takes the old and new findings of one file and returns
``{new index: old index}``. It sees the observations through :class:`Trackable`, so this
module does not import :mod:`matching`.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Protocol


class Trackable(Protocol):
    """What a matcher may read about one finding (implemented by ``Observation``)."""

    @property
    def rule(self) -> str: ...
    @property
    def line(self) -> int: ...
    @property
    def col(self) -> int: ...
    @property
    def keys(self) -> dict[str, str]: ...
    @property
    def message(self) -> str: ...
    @property
    def lines(self) -> Sequence[str]: ...


Matcher = Callable[[Sequence[Trackable], Sequence[Trackable]], dict[int, int]]


# ---------------------------------------------------------------------------
# SonarQube issue tracking
# ---------------------------------------------------------------------------
# Port of SonarQube 26.10.0.133078 (tag 26.10.0.133078, commit 55989c64), LGPL-3.0,
# Copyright SonarSource SA. Sources, all under sonar-core/src/main/java/org/sonar/core/:
#
#   issue/tracking/Tracker.java           Tracker.trackNonClosed      the pass order
#   issue/tracking/AbstractTracker.java   AbstractTracker.match       one key-based pass
#                                         LineAndLineHashAndMessage, LineAndLineHashKey,
#                                         LineHashAndMessageKey, LineAndMessageKey,
#                                         LineHashKey                 the pass keys
#   issue/tracking/BlockRecognizer.java   BlockRecognizer.match       code-move detection
#                                         lengthOfMaximalBlock, LinePairComparator
#   issue/tracking/BlockHashSequence.java BlockHashSequence, BlockHashFactory
#   hash/SourceLineHashesComputer.java    computeHash                 the line hash
#
# and, for how the compute engine feeds the tracker,
# server/sonar-ce-task-projectanalysis/.../issue/TrackerRawInputFactory.java
# (toExternalIssue: an issue's line hash is the hash of its start line) and
# .../source/SourceLinesRepositoryImpl.java (the file's lines, with a trailing empty line
# when the file ends with a line break, as :func:`schemes.split_lines` returns them).
#
# The passes, in order, each over the issues still unmatched:
#   1. same rule, line, line hash and message
#   2. same rule, line and line hash
#   3. code moves: issues on lines whose surrounding 11-line block hash is unique in both
#      versions, then on line pairs ranked by the length of the identical block around them
#   4. same rule, line hash and message
#   5. same rule, line and message
#   6. same rule and line hash
#
# Where the port fixes what SonarQube leaves to its environment:
# - All issues of the previous analysis get the same update date, so a pass that finds
#   several candidates takes the first in input order (the Java sort is stable).
# - Issues are given to the tracker in the analyzer's report order.
# - BlockRecognizer iterates Guava ArrayListMultimap key sets backed by java.util.HashMap,
#   and that order breaks ties between line pairs of equal weight and distance. The port
#   reproduces HashMap's iteration order exactly (JavaHashMap below).
# - Line hashes are computed over the whole line. SonarQube hashes only "significant code"
#   when a language plugin reports such ranges; external issues on files whose plugin does
#   not (and every file of a language SonarQube does not analyse) use whole lines.
# - Only the non-closed tracking runs: the harness compares one version with the next, so
#   there are no closed issues to reopen.
#
# research/finding_identity/fidelity/sonar/ compiles the original classes and runs them on
# generated cases; tests/test_tools.py checks the port against their recorded output.

_INT_MASK = (1 << 32) - 1
_SONAR_MESSAGE_MAX = 4000  # DefaultIssue.MESSAGE_MAX_SIZE
_HALF_BLOCK = 5  # BlockHashSequence.DEFAULT_HALF_BLOCK_SIZE
_PRIME_BASE = 31
_MAX_LINE_PAIRS = 250_000  # BlockRecognizer.isOverLimit


def _int32(value: int) -> int:
    value &= _INT_MASK
    return value - (1 << 32) if value >= 1 << 31 else value


def _java_string_hash(text: str) -> int:
    h = 0
    for unit in text.encode("utf-16-le", "surrogatepass")[::2]:
        h = (31 * h + unit) & _INT_MASK
    return _int32(h)


def sonar_line_hash(line: str) -> str:
    """``SourceLineHashesComputer.computeHash``: MD5 of the line without spaces and tabs."""
    reduced = line.replace("\t", "").replace(" ", "")
    if not reduced:
        return ""
    return hashlib.md5(reduced.encode("utf-8"), usedforsecurity=False).hexdigest()


def sonar_line_hashes(lines: Sequence[str]) -> list[str]:
    return [sonar_line_hash(line) for line in lines]


def sonar_message(message: str) -> str | None:
    """The message as ``DefaultIssue`` stores it: abbreviated, and ``None`` when empty."""
    if not message:
        return None
    if len(message) > _SONAR_MESSAGE_MAX:
        return message[: _SONAR_MESSAGE_MAX - 3] + "..."
    return message


def block_hashes(hashes: Sequence[str], half: int = _HALF_BLOCK) -> list[int]:
    """``BlockHashSequence``: a rolling hash over the line hashes of lines L-5 .. L+5."""
    power = pow(_PRIME_BASE, 2 * half, 1 << 32)
    n = len(hashes)
    value = 0
    for i in range(1, min(n, half + 1) + 1):
        value = _PRIME_BASE * value + _java_string_hash(hashes[i - 1])
    out = []
    for line in range(1, n + 1):
        out.append(_int32(value))
        if line - half > 0:
            value -= power * _java_string_hash(hashes[line - half - 1])
        nxt = _java_string_hash(hashes[line + half]) if line + 1 + half <= n else 0
        value = (_PRIME_BASE * value + nxt) & _INT_MASK
    return out


def _hash_at(hashes: Sequence[str], line: int) -> str:
    return hashes[line - 1] if 0 < line <= len(hashes) else ""


def _length_of_maximal_block(a: Sequence[str], la: int, b: Sequence[str], lb: int) -> int:
    if _hash_at(a, la) != _hash_at(b, lb):
        return 0
    length = 0
    ai, bi = la, lb
    while ai <= len(a) and bi <= len(b) and _hash_at(a, ai) == _hash_at(b, bi):
        ai, bi, length = ai + 1, bi + 1, length + 1
    ai, bi = la, lb
    while ai > 0 and bi > 0 and _hash_at(a, ai) == _hash_at(b, bi):
        ai, bi, length = ai - 1, bi - 1, length + 1
    return length - 1


class _Node:
    __slots__ = ("hash", "key", "left", "next", "parent", "prev", "red", "right", "tree")

    def __init__(self, h: int, key: int, nxt: _Node | None = None) -> None:
        self.hash, self.key, self.next = h, key, nxt
        self.prev: _Node | None = None
        self.parent: _Node | None = None
        self.left: _Node | None = None
        self.right: _Node | None = None
        self.red = False
        self.tree = False


class JavaHashMap:
    """The key order of ``java.util.HashMap<Integer, V>``, for BlockRecognizer's ties.

    A port of the parts of OpenJDK's ``java/util/HashMap.java`` (unchanged from JDK 8 to
    21, GPL-2.0 with Classpath Exception) that decide iteration order: ``putVal``,
    ``resize``, ``treeifyBin``, ``removeNode``, and in ``TreeNode`` ``treeify``,
    ``untreeify``, ``split``, ``putTreeVal``, ``removeTreeNode``, ``moveRootToFront`` and
    the red-black balancing. A bucket lists its keys in insertion order until it holds
    nine keys in a table of 64 or more buckets; then it becomes a tree, which keeps its
    root first and inserts each key after its tree parent. Guava's
    ``ArrayListMultimap.create()`` starts the map with 16 buckets (expected size 12).
    """

    def __init__(self, capacity: int = 16) -> None:
        self._tab: list[_Node | None] = [None] * capacity
        self._threshold = capacity * 3 // 4
        self._size = 0

    @staticmethod
    def _spread(key: int) -> int:
        k = key & _INT_MASK
        return _int32(k ^ (k >> 16))

    def keys(self) -> list[int]:
        out = []
        for e in self._tab:
            while e is not None:
                out.append(e.key)
                e = e.next
        return out

    # -- HashMap.putVal / treeifyBin / resize -------------------------------------------

    def put(self, key: int) -> None:
        tab = self._tab
        h = self._spread(key)
        i = h & (len(tab) - 1)
        p = tab[i]
        if p is None:
            tab[i] = _Node(h, key)
        elif p.key == key:
            return
        elif p.tree:
            if not self._put_tree_val(p, h, key):
                return
        else:
            bin_count = 0
            while True:
                e = p.next
                if e is None:
                    p.next = _Node(h, key)
                    if bin_count >= 7:
                        self._treeify_bin(h)
                    break
                if e.key == key:
                    return
                p = e
                bin_count += 1
        self._size += 1
        if self._size > self._threshold:
            self._resize()

    def _treeify_bin(self, h: int) -> None:
        tab = self._tab
        if len(tab) < 64:
            self._resize()
            return
        index = h & (len(tab) - 1)
        e = tab[index]
        hd = tl = None
        while e is not None:
            e.tree = True
            e.prev = tl
            if tl is None:
                hd = e
            else:
                tl.next = e
            tl = e
            e = e.next
        if hd is not None:
            self._treeify(hd)

    def _resize(self) -> None:
        old = self._tab
        old_cap = len(old)
        new: list[_Node | None] = [None] * (old_cap * 2)
        self._tab = new
        self._threshold *= 2
        for j in range(old_cap):
            e = old[j]
            if e is None:
                continue
            if e.next is None:
                new[e.hash & (len(new) - 1)] = e
            elif e.tree:
                self._split(e, j, old_cap)
            else:
                lo: list[_Node] = []
                hi: list[_Node] = []
                while e is not None:
                    (lo if e.hash & old_cap == 0 else hi).append(e)
                    e = e.next
                for part, at in ((lo, j), (hi, j + old_cap)):
                    for a, b in pairwise(part):
                        a.next = b
                    if part:
                        part[-1].next = None
                        new[at] = part[0]

    # -- TreeNode -------------------------------------------------------------------------

    @staticmethod
    def _root(x: _Node) -> _Node:
        while x.parent is not None:
            x = x.parent
        return x

    def _move_root_to_front(self, root: _Node) -> None:
        tab = self._tab
        index = root.hash & (len(tab) - 1)
        first = tab[index]
        if root is not first:
            tab[index] = root
            rp, rn = root.prev, root.next
            if rn is not None:
                rn.prev = rp
            if rp is not None:
                rp.next = rn
            if first is not None:
                first.prev = root
            root.next = first
            root.prev = None

    def _treeify(self, head: _Node) -> None:
        root: _Node | None = None
        x: _Node | None = head
        while x is not None:
            nxt = x.next
            x.left = x.right = None
            if root is None:
                x.parent = None
                x.red = False
                root = x
            else:
                p = root
                while True:
                    # Keys are distinct Integers, so their spread hashes differ.
                    left = p.hash > x.hash
                    xp = p
                    child = p.left if left else p.right
                    if child is None:
                        x.parent = xp
                        if left:
                            xp.left = x
                        else:
                            xp.right = x
                        root = self._balance_insertion(root, x)
                        break
                    p = child
            x = nxt
        assert root is not None
        self._move_root_to_front(root)

    def _untreeify(self, head: _Node) -> _Node:
        e: _Node | None = head
        while e is not None:
            e.tree = False
            e.prev = e.parent = e.left = e.right = None
            e = e.next
        return head

    def _split(self, b: _Node, index: int, bit: int) -> None:
        lo: list[_Node] = []
        hi: list[_Node] = []
        e: _Node | None = b
        while e is not None:
            nxt = e.next
            e.next = None
            (lo if e.hash & bit == 0 else hi).append(e)
            e = nxt
        for part in (lo, hi):
            prev = None
            for node in part:
                node.prev = prev
                if prev is not None:
                    prev.next = node
                prev = node
        tab = self._tab
        if lo:
            if len(lo) <= 6:
                tab[index] = self._untreeify(lo[0])
            else:
                tab[index] = lo[0]
                if hi:
                    self._treeify(lo[0])
        if hi:
            if len(hi) <= 6:
                tab[index + bit] = self._untreeify(hi[0])
            else:
                tab[index + bit] = hi[0]
                if lo:
                    self._treeify(hi[0])

    def _put_tree_val(self, first: _Node, h: int, key: int) -> bool:
        root = self._root(first)
        p = root
        while True:
            if p.key == key:
                return False
            left = p.hash > h
            xp = p
            child = p.left if left else p.right
            if child is None:
                xpn = xp.next
                x = _Node(h, key, xpn)
                x.tree = True
                if left:
                    xp.left = x
                else:
                    xp.right = x
                xp.next = x
                x.parent = x.prev = xp
                if xpn is not None:
                    xpn.prev = x
                self._move_root_to_front(self._balance_insertion(root, x))
                return True
            p = child

    @staticmethod
    def _rotate_left(root: _Node, p: _Node | None) -> _Node:
        if p is not None and (r := p.right) is not None:
            rl = p.right = r.left
            if rl is not None:
                rl.parent = p
            pp = r.parent = p.parent
            if pp is None:
                root = r
                r.red = False
            elif pp.left is p:
                pp.left = r
            else:
                pp.right = r
            r.left = p
            p.parent = r
        return root

    @staticmethod
    def _rotate_right(root: _Node, p: _Node | None) -> _Node:
        if p is not None and (lft := p.left) is not None:
            lr = p.left = lft.right
            if lr is not None:
                lr.parent = p
            pp = lft.parent = p.parent
            if pp is None:
                root = lft
                lft.red = False
            elif pp.right is p:
                pp.right = lft
            else:
                pp.left = lft
            lft.right = p
            p.parent = lft
        return root

    def _balance_insertion(self, root: _Node, x: _Node) -> _Node:
        x.red = True
        while True:
            xp = x.parent
            if xp is None:
                x.red = False
                return x
            xpp = xp.parent
            if not xp.red or xpp is None:
                return root
            xppl = xpp.left
            if xp is xppl:
                xppr = xpp.right
                if xppr is not None and xppr.red:
                    xppr.red = xp.red = False
                    xpp.red = True
                    x = xpp
                else:
                    if x is xp.right:
                        x = xp
                        root = self._rotate_left(root, x)
                        xp = x.parent
                        xpp = None if xp is None else xp.parent
                    if xp is not None:
                        xp.red = False
                        if xpp is not None:
                            xpp.red = True
                            root = self._rotate_right(root, xpp)
            else:
                if xppl is not None and xppl.red:
                    xppl.red = xp.red = False
                    xpp.red = True
                    x = xpp
                else:
                    if x is xp.left:
                        x = xp
                        root = self._rotate_right(root, x)
                        xp = x.parent
                        xpp = None if xp is None else xp.parent
                    if xp is not None:
                        xp.red = False
                        if xpp is not None:
                            xpp.red = True
                            root = self._rotate_left(root, xpp)

    def _balance_deletion(self, root: _Node, x: _Node | None) -> _Node:
        while True:
            if x is None or x is root:
                return root
            xp = x.parent
            if xp is None:
                x.red = False
                return x
            if x.red:
                x.red = False
                return root
            xpl = xp.left
            if xpl is x:
                xpr = xp.right
                if xpr is not None and xpr.red:
                    xpr.red = False
                    xp.red = True
                    root = self._rotate_left(root, xp)
                    xp = x.parent
                    xpr = None if xp is None else xp.right
                if xpr is None:
                    x = xp
                else:
                    sl, sr = xpr.left, xpr.right
                    if (sr is None or not sr.red) and (sl is None or not sl.red):
                        xpr.red = True
                        x = xp
                    else:
                        if sr is None or not sr.red:
                            if sl is not None:
                                sl.red = False
                            xpr.red = True
                            root = self._rotate_right(root, xpr)
                            xp = x.parent
                            xpr = None if xp is None else xp.right
                        if xpr is not None:
                            xpr.red = False if xp is None else xp.red
                            sr = xpr.right
                            if sr is not None:
                                sr.red = False
                        if xp is not None:
                            xp.red = False
                            root = self._rotate_left(root, xp)
                        x = root
            else:
                if xpl is not None and xpl.red:
                    xpl.red = False
                    xp.red = True
                    root = self._rotate_right(root, xp)
                    xp = x.parent
                    xpl = None if xp is None else xp.left
                if xpl is None:
                    x = xp
                else:
                    sl, sr = xpl.left, xpl.right
                    if (sl is None or not sl.red) and (sr is None or not sr.red):
                        xpl.red = True
                        x = xp
                    else:
                        if sl is None or not sl.red:
                            if sr is not None:
                                sr.red = False
                            xpl.red = True
                            root = self._rotate_left(root, xpl)
                            xp = x.parent
                            xpl = None if xp is None else xp.left
                        if xpl is not None:
                            xpl.red = False if xp is None else xp.red
                            sl = xpl.left
                            if sl is not None:
                                sl.red = False
                        if xp is not None:
                            xp.red = False
                            root = self._rotate_right(root, xp)
                        x = root

    # -- HashMap.removeNode / TreeNode.removeTreeNode --------------------------------------

    def remove(self, key: int) -> None:
        tab = self._tab
        h = self._spread(key)
        index = h & (len(tab) - 1)
        p = tab[index]
        node = None
        while p is not None and node is None:
            if p.key == key:
                node = p
            p = p.next
        if node is None:
            return
        if node.tree:
            self._remove_tree_node(node)
        else:
            first = tab[index]
            if first is node:
                tab[index] = node.next
            else:
                q = first
                while q is not None and q.next is not node:
                    q = q.next
                if q is not None:
                    q.next = node.next
        self._size -= 1

    def _remove_tree_node(self, p: _Node) -> None:
        tab = self._tab
        index = p.hash & (len(tab) - 1)
        first = tab[index]
        root = first
        succ, pred = p.next, p.prev
        if pred is None:
            tab[index] = first = succ
        else:
            pred.next = succ
        if succ is not None:
            succ.prev = pred
        if first is None:
            return
        assert root is not None
        if root.parent is not None:
            root = self._root(root)
        rl = root.left
        if root.right is None or rl is None or rl.left is None:
            tab[index] = self._untreeify(first)  # too small
            return
        pl, pr = p.left, p.right
        if pl is not None and pr is not None:
            s = pr
            while s.left is not None:
                s = s.left
            s.red, p.red = p.red, s.red
            sr = s.right
            pp = p.parent
            if s is pr:
                p.parent = s
                s.right = p
            else:
                sp = s.parent
                p.parent = sp
                if sp is not None:
                    if s is sp.left:
                        sp.left = p
                    else:
                        sp.right = p
                s.right = pr
                pr.parent = s
            p.left = None
            p.right = sr
            if sr is not None:
                sr.parent = p
            s.left = pl
            pl.parent = s
            s.parent = pp
            if pp is None:
                root = s
            elif p is pp.left:
                pp.left = s
            else:
                pp.right = s
            replacement = sr if sr is not None else p
        elif pl is not None:
            replacement = pl
        elif pr is not None:
            replacement = pr
        else:
            replacement = p
        if replacement is not p:
            pp = replacement.parent = p.parent
            if pp is None:
                root = replacement
                replacement.red = False
            elif p is pp.left:
                pp.left = replacement
            else:
                pp.right = replacement
            p.left = p.right = p.parent = None
        r = root if p.red else self._balance_deletion(root, replacement)
        if replacement is p:
            pp = p.parent
            p.parent = None
            if pp is not None:
                if p is pp.left:
                    pp.left = None
                elif p is pp.right:
                    pp.right = None
        self._move_root_to_front(r)


class _Tracking:
    def __init__(self, raws: Sequence[Trackable], bases: Sequence[Trackable]) -> None:
        self.raws = raws
        self.bases = bases
        self.raw_to_base: dict[int, int] = {}
        self.base_to_raw: dict[int, int] = {}

    def unmatched_raws(self) -> list[int]:
        return [i for i in range(len(self.raws)) if i not in self.raw_to_base]

    def unmatched_bases(self) -> list[int]:
        return [i for i in range(len(self.bases)) if i not in self.base_to_raw]

    def match(self, raw: int, base: int) -> None:
        if raw not in self.raw_to_base:
            self.raw_to_base[raw] = base
            self.base_to_raw[base] = raw

    def complete(self) -> bool:
        return len(self.raw_to_base) == len(self.raws)


@dataclass(frozen=True)
class _Side:
    issues: Sequence[Trackable]
    hashes: list[str]
    blocks: list[int]

    @classmethod
    def of(cls, issues: Sequence[Trackable]) -> _Side:
        hashes = sonar_line_hashes(issues[0].lines) if issues else []
        return cls(issues, hashes, block_hashes(hashes))

    def line_hash(self, t: Trackable) -> str:
        return _hash_at(self.hashes, t.line)


def _match_pass(
    tr: _Tracking, raw: _Side, base: _Side, key: Callable[[_Side, Trackable], Hashable]
) -> None:
    """``AbstractTracker.match``: pair each unmatched raw issue with the first base one."""
    if tr.complete():
        return
    search: dict[Hashable, list[int]] = defaultdict(list)
    for b in tr.unmatched_bases():
        search[key(base, base.issues[b])].append(b)
    for r in tr.unmatched_raws():
        candidates = search.get(key(raw, raw.issues[r]))
        if candidates:
            tr.match(r, candidates.pop(0))


def _line_line_hash_message(side: _Side, t: Trackable) -> Hashable:
    return (t.rule, t.line, side.line_hash(t), sonar_message(t.message))


def _line_line_hash(side: _Side, t: Trackable) -> Hashable:
    return (t.rule, t.line, side.line_hash(t))


def _line_hash_message(side: _Side, t: Trackable) -> Hashable:
    return (t.rule, side.line_hash(t), sonar_message(t.message))


def _line_message(side: _Side, t: Trackable) -> Hashable:
    return (t.rule, t.line, sonar_message(t.message))


def _line_hash_only(side: _Side, t: Trackable) -> Hashable:
    return (t.rule, side.line_hash(t))


def _group_by_line(idx: Iterable[int], side: _Side) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for i in idx:
        line = side.issues[i].line
        if 0 < line <= len(side.blocks):
            out.setdefault(line, []).append(i)
    return out


def _detect_code_moves(tr: _Tracking, raw: _Side, base: _Side) -> None:
    """``BlockRecognizer.match``."""
    if tr.complete():
        return
    raws_by_line = _group_by_line(tr.unmatched_raws(), raw)
    bases_by_line = _group_by_line(tr.unmatched_bases(), base)
    raw_keys, base_keys = JavaHashMap(), JavaHashMap()
    for line in raws_by_line:
        raw_keys.put(line)
    for line in bases_by_line:
        base_keys.put(line)
    raw_order, base_order = raw_keys.keys(), base_keys.keys()

    # HashOccurrence per block hash, created from the base lines; the matches it finds are
    # disjoint, but the order of the removals follows occurrencesByHash (a HashMap) and
    # can reorder a treeified bucket of the line maps.
    occurrences = JavaHashMap()
    base_seen: dict[int, list[int]] = defaultdict(list)
    for line in base_order:
        h = base.blocks[line - 1]
        occurrences.put(h)
        base_seen[h].append(line)
    raw_seen: dict[int, list[int]] = defaultdict(list)
    for line in raw_order:
        h = raw.blocks[line - 1]
        if h in base_seen:
            raw_seen[h].append(line)
    for h in occurrences.keys():
        base_lines, raw_lines = base_seen[h], raw_seen.get(h, [])
        if len(base_lines) == 1 and len(raw_lines) == 1:
            _map(tr, raws_by_line[raw_lines[0]], bases_by_line[base_lines[0]])
            base_keys.remove(base_lines[0])
            raw_keys.remove(raw_lines[0])

    # Removing keys can reorder a treeified bucket, so read the order again.
    remaining_base, remaining_raw = base_keys.keys(), raw_keys.keys()
    if len(remaining_base) * len(remaining_raw) >= _MAX_LINE_PAIRS:
        return
    pairs = []
    for bl in remaining_base:
        for rl in remaining_raw:
            weight = _length_of_maximal_block(base.hashes, bl, raw.hashes, rl)
            if weight > 0:
                pairs.append((bl, rl, weight))
    pairs.sort(key=lambda p: (-p[2], abs(p[0] - p[1])))
    for bl, rl, _ in pairs:
        _map(tr, raws_by_line[rl], bases_by_line[bl])


def _map(tr: _Tracking, raws: list[int], bases: list[int]) -> None:
    """``BlockRecognizer.map``: each raw issue takes the first free base issue of its rule."""
    for r in raws:
        for b in bases:
            if b not in tr.base_to_raw and tr.bases[b].rule == tr.raws[r].rule:
                tr.match(r, b)
                break


def sonar_track(old: Sequence[Trackable], new: Sequence[Trackable]) -> dict[int, int]:
    """``Tracker.trackNonClosed`` with *new* as the raw and *old* as the base issues."""
    raw, base = _Side.of(new), _Side.of(old)
    tr = _Tracking(new, old)
    _match_pass(tr, raw, base, _line_line_hash_message)
    _match_pass(tr, raw, base, _line_line_hash)
    _detect_code_moves(tr, raw, base)
    _match_pass(tr, raw, base, _line_hash_message)
    _match_pass(tr, raw, base, _line_message)
    _match_pass(tr, raw, base, _line_hash_only)
    return dict(tr.raw_to_base)


# ---------------------------------------------------------------------------
# Bandit baseline
# ---------------------------------------------------------------------------
# Bandit 1.9.4 (PyPI bandit==1.9.4), Apache-2.0. `bandit -b baseline.json` loads the
# baseline's issues (bandit/core/manager.py, BanditManager.populate_baseline) and keeps a
# result unless `a in baseline` (manager._compare_baseline_results), where equality is
# Issue.__eq__ in bandit/core/issue.py: same text, severity, cwe, confidence, fname, test
# and test_id. The line is not compared. Membership ignores multiplicity: once one equal
# issue is in the baseline, every equal result is treated as known. The `bandit` key
# (schemes.bandit_key) holds exactly the compared fields.
#
# Bandit pairs nothing; it only answers "in the baseline or not". To score mispairs the
# matcher pairs equal issues in line order like a key scheme, and every surplus new issue
# with a key present in the baseline goes to the last old issue with that key.


def bandit_baseline(old: Sequence[Trackable], new: Sequence[Trackable]) -> dict[int, int]:
    old_by_key: dict[str, list[int]] = defaultdict(list)
    for i in sorted(range(len(old)), key=lambda k: (old[k].line, old[k].col)):
        old_by_key[old[i].keys["bandit"]].append(i)
    used: dict[str, int] = defaultdict(int)
    pairs: dict[int, int] = {}
    for j in sorted(range(len(new)), key=lambda k: (new[k].line, new[k].col)):
        key = new[j].keys["bandit"]
        candidates = old_by_key.get(key)
        if not candidates:
            continue
        pairs[j] = candidates[min(used[key], len(candidates) - 1)]
        used[key] += 1
    return pairs


# ---------------------------------------------------------------------------
# SonarQube file move detection (branch analyses)
# ---------------------------------------------------------------------------
# Port of the per-pair decision of FileMoveDetectionStep (computeScoreMatrix and its
# MIN_REQUIRED_SCORE, LOWER_BOUND_RATIO and UPPER_BOUND_RATIO) and of
# SourceSimilarityImpl.score, in sonar-ce-task-projectanalysis
# org/sonar/ce/task/projectanalysis/filemove, SonarQube 26.10.0.133078 (LGPL-3.0). The
# step compares every removed file with every added file and elects the best-scoring
# pairs; the harness already pairs files by git's rename detection, so only the decision
# for that pair is ported. Pull-request analyses skip the step and take renames from the
# SCM (PullRequestFileMoveDetectionStep).

_MOVE_MIN_SCORE = 85
_MOVE_LOWER_BOUND_RATIO = 0.84
_MOVE_UPPER_BOUND_RATIO = 1.18


def sonar_similarity(left: Sequence[str], right: Sequence[str]) -> int:
    """``SourceSimilarityImpl.score``: 100 * (1 - edit distance / longer length), truncated."""
    if not left and not right:
        return 0
    longest = max(len(left), len(right))
    # A common prefix and suffix do not change the edit distance; dropping them first
    # keeps the quadratic part to the lines that differ.
    start = 0
    while start < min(len(left), len(right)) and left[start] == right[start]:
        start += 1
    end = 0
    while end < min(len(left), len(right)) - start and left[-1 - end] == right[-1 - end]:
        end += 1
    a, b = left[start : len(left) - end], right[start : len(right) - end]
    cost = list(range(len(a) + 1))
    for j in range(1, len(b) + 1):
        new_cost = [j] + [0] * len(a)
        for i in range(1, len(a) + 1):
            replace = cost[i - 1] + (a[i - 1] != b[j - 1])
            new_cost[i] = min(cost[i] + 1, new_cost[i - 1] + 1, replace)
        cost = new_cost
    return int(100 * (1.0 - cost[len(a)] / longest))


def sonar_file_moved(old_lines: Sequence[str], new_lines: Sequence[str]) -> bool:
    """Whether a branch analysis takes the added file for the removed one."""
    old_count, new_count = len(old_lines), len(new_lines)
    lower = math.floor(old_count * _MOVE_LOWER_BOUND_RATIO)
    upper = math.ceil(old_count * _MOVE_UPPER_BOUND_RATIO)
    if new_count >= upper or new_count <= lower:
        return False
    score = sonar_similarity(sonar_line_hashes(old_lines), sonar_line_hashes(new_lines))
    return score >= _MOVE_MIN_SCORE


def _sonar_branch_moved(old: Sequence[Trackable], new: Sequence[Trackable]) -> bool:
    # Every finding of a file version carries that version's lines.
    return sonar_file_moved(old[0].lines, new[0].lines)


MATCHERS: dict[str, Matcher] = {
    "sonar": sonar_track,
    "sonar_branch": sonar_track,
    "bandit": bandit_baseline,
}

#: For a renamed file: whether the scheme still takes it for the old file. A scheme
#: listed here pairs nothing across a rename that its check rejects.
RENAME_CHECKS: dict[str, Callable[[Sequence[Trackable], Sequence[Trackable]], bool]] = {
    "sonar_branch": _sonar_branch_moved,
}
