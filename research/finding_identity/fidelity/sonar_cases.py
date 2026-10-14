"""Check the SonarQube tracker port against SonarQube's own tracker.

Generates file-version pairs with issues (seeded, so they can be regenerated), runs the
original ``Tracker`` through ``sonar/SonarTrackerHarness.java`` and the port in
:mod:`research.finding_identity.trackers`, and compares the matches. The cases stress the
passes that are easy to get wrong: repeated lines and duplicated blocks (block hashes that
are not unique, ties between line pairs), shifted and moved code, changed messages, and
enough issue lines to resize Java's HashMap. Separate cases check the port of HashMap's
key order (``JavaHashMap``) against Guava's ``ArrayListMultimap`` directly, including
treeified buckets and removals.

    bash research/finding_identity/fidelity/sonar/build.sh
    python -m research.finding_identity.fidelity.sonar_cases --count 2000
    python -m research.finding_identity.fidelity.sonar_cases --write   # refresh the fixture
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..matching import Observation
from ..trackers import JavaHashMap, sonar_track

HERE = Path(__file__).parent
BUILD = HERE / ".build" / "sonar"
FIXTURE = HERE.parent / "tests" / "fixtures" / "sonar_tracker.json"
FIXTURE_SEED = 20261014
FIXTURE_COUNT = 400
FIXTURE_ORDER_COUNT = 400

_VOCAB = [
    "",
    "x = 1",
    "y = compute(x)",
    "    return x",
    "foo()",
    "if x:",
    "    pass",
    "eval(data)",
    "\teval( data )",
    "for i in range(10):",
    "    total += i",
    "# comment",
    "}",
    "print('hello')",
]
_RULES = ["R1", "R2", "R3"]
_MESSAGES = ["", "bad call", "bad call to eval", "Possible injection"]


@dataclass(frozen=True)
class Issue:
    rule: str
    line: int
    message: str


@dataclass(frozen=True)
class Case:
    old: list[str]
    new: list[str]
    base: list[Issue]
    raw: list[Issue]


def _line(rng: random.Random) -> str:
    if rng.random() < 0.3:
        return f"v{rng.randrange(1000)} = call({rng.randrange(50)})"
    return rng.choice(_VOCAB)


def _edit(rng: random.Random, old: list[str]) -> tuple[list[str], list[int | None]]:
    """A new version of *old*, and where each old line went (``None``: gone or changed)."""
    new = list(old)
    where: list[int | None] = list(range(len(old)))
    for _ in range(rng.randrange(1, 5)):
        op = rng.choice(["insert", "delete", "change", "move", "duplicate"])
        if op == "insert" or not new:
            at = rng.randrange(len(new) + 1)
            block = [_line(rng) for _ in range(rng.randrange(1, 15))]
            new[at:at] = block
            where = [w if w is None or w < at else w + len(block) for w in where]
        elif op == "delete":
            at = rng.randrange(len(new))
            n = min(rng.randrange(1, 6), len(new) - at)
            del new[at : at + n]
            where = [
                None if w is not None and at <= w < at + n else w if w is None or w < at else w - n
                for w in where
            ]
        elif op == "change":
            at = rng.randrange(len(new))
            new[at] = _line(rng)
            where = [None if w == at else w for w in where]
        elif op == "move":
            at = rng.randrange(len(new))
            n = min(rng.randrange(1, 12), len(new) - at)
            block = new[at : at + n]
            del new[at : at + n]
            to = rng.randrange(len(new) + 1)
            new[to:to] = block

            def moved(w: int | None, at: int = at, n: int = n, to: int = to) -> int | None:
                if w is None:
                    return None
                if at <= w < at + n:
                    return to + (w - at)
                w2 = w if w < at else w - n
                return w2 if w2 < to else w2 + n

            where = [moved(w) for w in where]
        else:  # duplicate a block elsewhere: repeated block hashes
            at = rng.randrange(len(new))
            n = min(rng.randrange(1, 12), len(new) - at)
            to = rng.randrange(len(new) + 1)
            new[to:to] = new[at : at + n]
            where = [w if w is None or w < to else w + n for w in where]
    return new, where


def make_case(rng: random.Random) -> Case:
    size = rng.choice([5, 20, 60, 200, 700])
    if rng.random() < 0.3:  # a file built from one repeated block
        block = [_line(rng) for _ in range(rng.randrange(2, 8))]
        old = (block * (size // len(block) + 1))[:size]
    else:
        old = [_line(rng) for _ in range(size)]
    new, where = _edit(rng, old)
    many = rng.random() < 0.25
    n_issues = rng.randrange(10, 60) if many else rng.randrange(0, 12)
    if rng.random() < 0.1 and len(old) > 600:  # many issue lines in one HashMap bucket
        stride = rng.choice([16, 32, 64])
        first = 1 + rng.randrange(stride)
        count = rng.randrange(9, len(old) // stride + 1)
        lines = [first + stride * k for k in range(count) if first + stride * k <= len(old)]
    else:
        lines = [rng.randrange(1, len(old) + 1) for _ in range(n_issues)]
    base = [Issue(rng.choice(_RULES), ln, rng.choice(_MESSAGES)) for ln in sorted(lines)]
    raw = []
    for issue in base:
        w = where[issue.line - 1]
        if w is not None and rng.random() < 0.85:
            msg = issue.message if rng.random() < 0.8 else rng.choice(_MESSAGES)
            raw.append(Issue(issue.rule, w + 1, msg))
    for _ in range(rng.randrange(0, 6) if new else 0):
        raw.append(Issue(rng.choice(_RULES), rng.randrange(1, len(new) + 1), rng.choice(_MESSAGES)))
    raw.sort(key=lambda i: i.line)
    return Case(old, new, base, raw)


def make_cases(seed: int, count: int) -> list[Case]:
    rng = random.Random(seed)  # noqa: S311  (test data, not security)
    return [make_case(rng) for _ in range(count)]


def cases_digest(cases: list[Case]) -> str:
    """A hash of the generated cases, to notice when the generator changes."""
    h = hashlib.sha256()
    for c in cases:
        h.update(
            json.dumps([c.old, c.new, [vars(i) for i in c.base], [vars(i) for i in c.raw]]).encode()
        )
    return h.hexdigest()


@dataclass(frozen=True)
class OrderCase:
    puts: list[int]
    removes: list[int]


def make_order_cases(seed: int, count: int) -> list[OrderCase]:
    rng = random.Random(seed)  # noqa: S311  (test data, not security)
    out = []
    for _ in range(count):
        kind = rng.choice(["random", "stride", "large", "mixed", "signed"])
        n = rng.randrange(1, 150)
        if kind == "random":
            puts = [rng.randrange(1, 3000) for _ in range(n)]
        elif kind == "stride":  # one bucket: resizes, then a treeified bucket
            stride = rng.choice([16, 32, 64, 128, 256])
            first = rng.randrange(1, stride + 1)
            puts = [first + stride * k for k in range(n)]
            if rng.random() < 0.5:
                rng.shuffle(puts)
        elif kind == "large":
            puts = [rng.randrange(1, 1 << 20) for _ in range(n)]
        elif kind == "signed":  # block hashes are any Java int
            puts = [rng.randrange(-(1 << 31), 1 << 31) for _ in range(n)]
        else:
            stride = rng.choice([16, 32, 64])
            first = rng.randrange(1, stride + 1)
            puts = [first + stride * k for k in range(rng.randrange(5, 40))]
            puts += [rng.randrange(1, 2000) for _ in range(n)]
            rng.shuffle(puts)
        keys = list(dict.fromkeys(puts))
        removes = rng.sample(keys, rng.randrange(0, len(keys) + 1)) if rng.random() < 0.6 else []
        out.append(OrderCase(puts, removes))
    return out


def port_order(case: OrderCase) -> list[int]:
    m = JavaHashMap()
    for k in case.puts:
        m.put(k)
    for k in case.removes:
        m.remove(k)
    return m.keys()


def port_matches(case: Case) -> list[int]:
    def obs(issues: list[Issue], lines: list[str]) -> list[Observation]:
        return [Observation(i.rule, i.line, 1, {}, message=i.message, lines=lines) for i in issues]

    pairs = sonar_track(obs(case.base, case.old), obs(case.raw, case.new))
    return [pairs.get(j, -1) for j in range(len(case.raw))]


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _run_java(lines: list[str]) -> list[list[int]]:
    classpath = (BUILD / "classpath").read_text().strip()
    proc = subprocess.run(
        ["java", "-cp", classpath, "SonarTrackerHarness"],
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
        check=True,
    )
    return [[int(x) for x in line.split()] for line in proc.stdout.splitlines()]


def java_orders(cases: list[OrderCase]) -> list[list[int]]:
    return _run_java(
        [
            "ORDER " + " ".join(map(str, c.puts)) + (" | " + " ".join(map(str, c.removes)))
            for c in cases
        ]
    )


def java_matches(cases: list[Case]) -> list[list[int]]:
    out = []
    for c in cases:
        out.append("CASE")
        for tag, lines in (("OLD", c.old), ("NEW", c.new)):
            out.append(f"{tag} {len(lines)}")
            out += [_b64(line) for line in lines]
        for tag, issues in (("BASE", c.base), ("RAW", c.raw)):
            out.append(f"{tag} {len(issues)}")
            out += [f"{_b64(i.rule)} {i.line} {_b64(i.message)}" for i in issues]
        out.append("END")
    return _run_java(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=FIXTURE_SEED)
    parser.add_argument("--count", type=int, default=FIXTURE_COUNT)
    parser.add_argument("--order-count", type=int, default=FIXTURE_ORDER_COUNT)
    parser.add_argument("--write", action="store_true", help=f"write {FIXTURE.name}")
    args = parser.parse_args(argv)

    cases = make_cases(args.seed, args.count)
    expected = java_matches(cases)
    mismatches = 0
    for n, (case, want) in enumerate(zip(cases, expected, strict=True)):
        got = port_matches(case)
        if got != want:
            mismatches += 1
            print(f"case {n}: java {want}\n         port {got}", file=sys.stderr)
    matched = sum(1 for want in expected for b in want if b >= 0)
    raws = sum(len(want) for want in expected)
    print(f"{len(cases)} cases, {raws} raw issues ({matched} matched): {mismatches} mismatches")

    order_cases = make_order_cases(args.seed, args.order_count)
    orders = java_orders(order_cases)
    order_mismatches = sum(
        port_order(c) != want for c, want in zip(order_cases, orders, strict=True)
    )
    print(f"{len(order_cases)} HashMap orders: {order_mismatches} mismatches")
    mismatches += order_mismatches
    if args.write and not mismatches:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(
            json.dumps(
                {
                    "sonarqube": "26.10.0.133078",
                    "seed": args.seed,
                    "count": args.count,
                    "cases_sha256": cases_digest(cases),
                    "expected": expected,
                    "order_count": args.order_count,
                    "orders": orders,
                },
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
