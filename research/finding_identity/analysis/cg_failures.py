# SPDX-License-Identifier: Apache-2.0
"""Classify every error the ``codeguard`` (and ``sonar``) scheme makes in a replay.

``python -m research.finding_identity.analysis.cg_failures RESULTS --repos .repos``
reads ``pairs.jsonl`` and ``findings.jsonl`` of each repository, fetches the old and
new file versions from the clone, recomputes the scheme's key parts (enclosing scope,
normalized statement) on both sides, and sorts each false-new, hidden and mispaired
finding into a cause. It writes ``cases.jsonl`` (one classified case per line) and
``summary.md`` to ``--out``.

Causes for a false-new finding on a file that kept its path:

- ``scope``: the normalized statement is unchanged, the enclosing scope changed
  (renamed, or the statement moved into another function);
- ``parse``: one side has no AST (syntax error), so the scope is empty on that side;
- ``reformat``: the statement (as the AST statement node, comments and whitespace
  removed, literals masked) is unchanged but its first line changed, so the line was
  re-wrapped or the finding moved to another line of the same statement;
- ``literal``: only string or number tokens differ (masking missed them: f-strings,
  template literals, regex literals, multi-line strings);
- ``comment``: only a comment differs (``//`` inside a string, ``#`` in a string);
- ``identifier``, ``call``, ``attribute``, ``keyword``, ``operator``, ``structure``:
  which kind of token the edit touched (``structure``: tokens were added or removed);
- ``def_line``: the flagged line is a ``def``/``class``/``function`` header (whole-function
  rules), whatever changed on it.

For hidden and mispaired findings the script counts how many lines of the old and new
version carry the finding's key (``n_old``, ``n_new``), which says whether a copy was
added (``n_new > n_old``) or the old occurrence went away (``n_new == n_old``).
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from codeguard.engine import fingerprint as cg_fp

from ..gitrepo import GitRepo
from ..schemes import FileContext
from ..trackers import sonar_line_hash

_TOKEN_RE = re.compile(
    r"""(?P<comment>\#.*|//.*)
      | (?P<string>'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`)
      | (?P<number>(?<![A-Za-z_])\d[\d_]*(?:\.\d[\d_]*)?)
      | (?P<ident>[A-Za-z_$][A-Za-z0-9_$]*)
      | (?P<punct>[^\sA-Za-z0-9_$]+)""",
    re.VERBOSE,
)
_KEYWORDS = {
    "if",
    "else",
    "elif",
    "for",
    "while",
    "return",
    "def",
    "class",
    "import",
    "from",
    "await",
    "async",
    "not",
    "and",
    "or",
    "in",
    "is",
    "try",
    "except",
    "with",
    "as",
    "const",
    "let",
    "var",
    "function",
    "new",
    "this",
    "self",
    "lambda",
    "yield",
    "raise",
    "pass",
    "None",
    "True",
    "False",
    "null",
    "true",
    "false",
    "undefined",
    "typeof",
}
_DEF_RE = re.compile(r"^\s*(async\s+def|def|class|(?:export\s+)?(?:async\s+)?function)\b")
_SCHEMES = ("codeguard", "sonar")
_ERRORS = ("false_new", "false_known", "mispaired")


def tokens(line: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _TOKEN_RE.finditer(line):
        kind = m.lastgroup or "punct"
        text = m.group()
        if kind == "ident" and text in _KEYWORDS:
            kind = "keyword"
        out.append((kind, text))
    return out


def token_change(old: str, new: str) -> str:
    """What kind of token an edit of one line touched."""
    a, b = tokens(old), tokens(new)
    kinds: Counter[str] = Counter()
    added_removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag in ("insert", "delete") or (i2 - i1) != (j2 - j1):
            added_removed += abs((i2 - i1) - (j2 - j1))
        for seq, lo, hi in ((a, i1, i2), (b, j1, j2)):
            for k in range(lo, hi):
                kind, _text = seq[k]
                if kind == "ident":
                    nxt = seq[k + 1][1] if k + 1 < len(seq) else ""
                    prev = seq[k - 1][1] if k > 0 else ""
                    if nxt.startswith("("):
                        kind = "call"
                    elif prev.endswith("."):
                        kind = "attribute"
                kinds[kind] += 1
    if not kinds:
        return "whitespace"
    if set(kinds) <= {"comment"}:
        return "comment"
    if set(kinds) <= {"string", "number"}:
        return "literal"
    if set(kinds) <= {"string", "number", "comment"}:
        return "literal"
    if added_removed and added_removed >= sum(kinds.values()) / 2:
        return "structure"
    for kind in ("call", "attribute", "ident", "keyword", "punct"):
        if kind in kinds:
            return {"ident": "identifier", "punct": "operator"}.get(kind, kind)
    return "other"


def python_statement(tree: ast.Module | None, line: int) -> str | None:
    """The source span (as line range) of the smallest statement containing *line*."""
    if tree is None:
        return None
    best: ast.stmt | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            end = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= line <= end and (
                best is None or end - node.lineno < getattr(best, "end_lineno", 0) - best.lineno
            ):
                best = node
    if best is None:
        return None
    return f"{best.lineno}-{getattr(best, 'end_lineno', best.lineno)}"


def statement_text(ctx: FileContext, line: int) -> str:
    """The normalized text of the whole statement (Python) or line (other) at *line*."""
    span = python_statement(ctx.tree, line)
    if span is None:
        return cg_fp._normalize(ctx.raw_line(line))
    lo, hi = (int(x) for x in span.split("-"))
    return cg_fp._normalize("\n".join(ctx.lines[lo - 1 : hi]))


def key_parts(ctx: FileContext, line: int) -> tuple[str, str]:
    return ctx.scope(line), cg_fp._normalize(ctx.raw_line(line))


def key_lines(ctx: FileContext, scope: str, norm: str) -> list[int]:
    """Lines of *ctx* whose scope and normalized text equal the given parts."""
    out = []
    for i, raw in enumerate(ctx.lines, start=1):
        if cg_fp._normalize(raw) == norm and ctx.scope(i) == scope:
            out.append(i)
    return out


def hash_lines(ctx: FileContext, h: str) -> list[int]:
    return [i for i, raw in enumerate(ctx.lines, start=1) if sonar_line_hash(raw) == h]


class Repo:
    def __init__(self, path: Path) -> None:
        self.git = GitRepo(path)
        self._trees: dict[str, dict[str, str]] = {}
        self._ctx: dict[tuple[str, str], FileContext | None] = {}

    def context(self, commit: str, path: str) -> FileContext | None:
        key = (commit, path)
        if key not in self._ctx:
            tree = self._trees.get(commit)
            if tree is None:
                tree = self._trees[commit] = self.git.files(commit)
            sha = tree.get(path)
            if sha is None:
                self._ctx[key] = None
            else:
                text = self.git.blob(sha).decode("utf-8", "replace")
                self._ctx[key] = FileContext.build(path, text, is_python=path.endswith(".py"))
        return self._ctx[key]


def classify_false_new(
    rec: dict[str, Any], old: FileContext, new: FileContext, scheme: str
) -> dict[str, Any]:
    o_line, n_line = rec["old_line"], rec["line"]
    o_raw, n_raw = old.raw_line(o_line), new.raw_line(n_line)
    out: dict[str, Any] = {
        "old_raw": o_raw.strip()[:160],
        "new_raw": n_raw.strip()[:160],
        "def_line": bool(_DEF_RE.match(n_raw)),
    }
    if rec["status"] == "R":
        (os_, on), (ns, nn) = key_parts(old, o_line), key_parts(new, n_line)
        out["cause"] = (
            "path"
            if (os_, on) == (ns, nn)
            else "path+" + ("scope" if on == nn else token_change(o_raw, n_raw))
        )
        return out
    if scheme == "sonar":
        same_hash = sonar_line_hash(o_raw) == sonar_line_hash(n_raw)
        out["cause"] = "moved_same_hash" if same_hash else token_change(o_raw, n_raw)
        if statement_text(old, o_line) == statement_text(new, n_line) and not same_hash:
            out["cause"] = "reformat"
        return out
    (os_, on), (ns, nn) = key_parts(old, o_line), key_parts(new, n_line)
    if on == nn:
        if os_ == ns:
            out["cause"] = "same_key"  # should not happen for a key scheme
        elif (old.tree is None) != (new.tree is None):
            out["cause"] = "parse"
        else:
            out["cause"] = "scope"
            out["scopes"] = [os_, ns]
            out["scope_kind"] = (
                "renamed" if os_.rsplit(".", 1)[:-1] == ns.rsplit(".", 1)[:-1] else "moved"
            )
        return out
    if statement_text(old, o_line) == statement_text(new, n_line):
        out["cause"] = "reformat"
        return out
    out["cause"] = token_change(o_raw, n_raw)
    out["scope_changed"] = os_ != ns
    return out


def classify_hidden(
    rec: dict[str, Any], old: FileContext, new: FileContext, scheme: str
) -> dict[str, Any]:
    n_line = rec["line"]
    n_raw = new.raw_line(n_line)
    if scheme == "sonar":
        h = sonar_line_hash(n_raw)
        o_lines, n_lines = hash_lines(old, h), hash_lines(new, h)
    else:
        scope, norm = key_parts(new, n_line)
        o_lines, n_lines = key_lines(old, scope, norm), key_lines(new, scope, norm)
    # Is there an old line near the matched one that this line may be a rewrite of?
    near = [
        difflib.SequenceMatcher(
            None, old.raw_line(i).strip(), n_raw.strip(), autojunk=False
        ).ratio()
        for i in range(max(1, n_line - 3), min(len(old.lines), n_line + 3) + 1)
    ]
    kind = (
        "copy_added"
        if len(n_lines) > len(o_lines)
        else "old_occurrence_gone"
        if len(n_lines) == len(o_lines)
        else "fewer_copies"
    )
    return {
        "new_raw": n_raw.strip()[:160],
        "n_old": len(o_lines),
        "n_new": len(n_lines),
        "old_lines": o_lines[:6],
        "new_lines": n_lines[:6],
        "kind": kind,
        "best_nearby_similarity": round(max(near), 2) if near else None,
        "def_line": bool(_DEF_RE.match(n_raw)),
        "test_path": "test" in rec["path"].lower(),
    }


def classify_mispair(
    rec: dict[str, Any], old: FileContext, new: FileContext, scheme: str
) -> dict[str, Any]:
    out = classify_hidden(rec, old, new, scheme)
    out["old_line_truth"] = rec["old_line"]
    out["truth_kind"] = rec["truth_kind"]
    return out


def load_pairs(path: Path) -> dict[str, str]:
    out = {}
    with (path / "pairs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[r["new"]] = r["old"]
    return out


def run(results: Path, repos: Path, out: Path, schemes: Sequence[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    for repo_dir in sorted(p for p in results.iterdir() if (p / "findings.jsonl").exists()):
        label = repo_dir.name
        clone = repos / label
        if not clone.is_dir():
            print(f"skip {label}: no clone")
            continue
        repo = Repo(clone)
        pairs = load_pairs(repo_dir)
        by_version: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        with (repo_dir / "findings.jsonl").open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                by_version[(rec["commit"], rec["path"])].append(rec)
        for (commit, path), recs in by_version.items():
            wanted = [r for r in recs if any(r["outcomes"].get(s) in _ERRORS for s in schemes)]
            new = repo.context(commit, path)
            if new is None:
                continue
            # Collision population of this file version under the codeguard key.
            keys = Counter((*key_parts(new, r["line"]), r["rule"]) for r in recs)
            for r in recs:
                k = (*key_parts(new, r["line"]), r["rule"])
                if keys[k] > 1:
                    collisions.append(
                        {
                            "repo": label,
                            "rule": r["rule"],
                            "scope": k[0],
                            "norm": k[1][:80],
                            "copies": keys[k],
                            "def_line": bool(_DEF_RE.match(new.raw_line(r["line"]))),
                            "test_path": "test" in path.lower(),
                            "truth": r["truth"],
                        }
                    )
            if not wanted:
                continue
            old_commit = pairs.get(commit)
            for r in wanted:
                old_path = r.get("old_path") or path
                old = repo.context(old_commit, old_path) if old_commit else None
                for scheme in schemes:
                    oc = r["outcomes"].get(scheme)
                    if oc not in _ERRORS:
                        continue
                    base = {
                        "repo": label,
                        "scheme": scheme,
                        "outcome": oc,
                        "rule": r["rule"],
                        "path": path,
                        "status": r["status"],
                        "truth_kind": r.get("truth_kind"),
                        "line": r["line"],
                        "old_line": r.get("old_line"),
                        "commit": commit,
                        "sonar": r["outcomes"].get("sonar"),
                        "codeguard": r["outcomes"].get("codeguard"),
                        "cg_no_scope": r["outcomes"].get("cg_no_scope"),
                        "github": r["outcomes"].get("github"),
                    }
                    if old is None:
                        base["cause"] = "no_old_version"
                    elif oc == "false_new":
                        base.update(classify_false_new(r, old, new, scheme))
                    elif oc == "false_known":
                        base.update(classify_hidden(r, old, new, scheme))
                    else:
                        base.update(classify_mispair(r, old, new, scheme))
                    cases.append(base)
        repo.git.close()
        print(f"{label}: {sum(c['repo'] == label for c in cases)} cases")
    with (out / "cases.jsonl").open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    with (out / "collisions.jsonl").open("w", encoding="utf-8") as f:
        for c in collisions:
            f.write(json.dumps(c) + "\n")
    (out / "summary.md").write_text(summary(cases, collisions), encoding="utf-8")
    print(f"wrote {out}")


def _table(counter: Counter[Any], title: str) -> list[str]:
    lines = [f"### {title}", "", "| value | n |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in counter.most_common()]
    return [*lines, ""]


def summary(cases: Sequence[dict[str, Any]], collisions: Sequence[dict[str, Any]]) -> str:
    out = ["# Scheme failures", ""]
    for scheme in _SCHEMES:
        out.append(f"## `{scheme}`")
        out.append("")
        for oc in _ERRORS:
            sel = [c for c in cases if c["scheme"] == scheme and c["outcome"] == oc]
            if not sel:
                continue
            out.append(f"{len(sel)} `{oc}`.")
            out.append("")
            if oc == "false_new":
                same = [c for c in sel if c["status"] != "R"]
                out += _table(Counter(c["status"] for c in sel), "by file status")
                out += _table(Counter(c.get("cause") for c in same), "cause, same path")
                out += _table(
                    Counter((c.get("cause"), c.get("truth_kind")) for c in same),
                    "cause by truth kind, same path",
                )
                out += _table(
                    Counter(c["rule"] for c in same if c.get("def_line")),
                    "def-line findings by rule, same path",
                )
                out += _table(
                    Counter(c.get("cause") for c in sel if c["status"] == "R"), "cause, renamed"
                )
                out += _table(
                    Counter(c.get("scope_kind") for c in same if c.get("cause") == "scope"),
                    "scope changes",
                )
            else:
                out += _table(Counter(c.get("kind") for c in sel), "kind")
                out += _table(Counter(c["rule"] for c in sel), "rule")
                out += _table(
                    Counter(
                        (c.get("kind"), c.get("sonar") if scheme != "sonar" else c.get("codeguard"))
                        for c in sel
                    ),
                    "kind by the other tracker's outcome",
                )
                out += _table(Counter(c.get("def_line") for c in sel), "on a def line")
                out += _table(Counter(c.get("test_path") for c in sel), "in test code")
                sims = Counter(
                    "rewrite_candidate (nearby similarity >= 0.3)"
                    if (c.get("best_nearby_similarity") or 0) >= 0.3
                    else "no similar old line nearby"
                    for c in sel
                )
                out += _table(sims, "nearby rewrite")
    out.append("## Collisions (codeguard key, new versions of changed files)")
    out.append("")
    out.append(f"{len(collisions)} findings share their key with another in the same version.")
    out.append("")
    out += _table(Counter(c["rule"] for c in collisions), "rule")
    out += _table(Counter(c["scope"] == "" for c in collisions), "module level (True) or scoped")
    out += _table(Counter(c["test_path"] for c in collisions), "in test code")
    out += _table(Counter(c["def_line"] for c in collisions), "on a def line")
    out += _table(Counter(c["copies"] for c in collisions), "copies per key")
    top = Counter(c["norm"] for c in collisions)
    out += _table(Counter(dict(top.most_common(15))), "most repeated statements")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("--repos", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--schemes", default="codeguard,sonar")
    args = ap.parse_args(argv)
    run(args.results, args.repos, args.out, args.schemes.split(","))


if __name__ == "__main__":
    main()
