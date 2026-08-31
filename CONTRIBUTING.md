# Contributing to CodeGuard

Thanks for considering a contribution. This guide covers everything you need.

## Quick orientation

CodeGuard is a pure Python library + CLI. No database, no web stack. The core abstraction is:

```
Rule → AnalysisRunner → [Finding, ...]
```

Each rule is self-contained: one file, independently testable, zero knowledge of other rules.

## Developer setup

```bash
git clone https://github.com/mevichitra/codeguard
cd codeguard
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

Run tests:

```bash
pytest                          # all tests
pytest tests/test_rules/        # just rules
pytest -k CG-SEC-001            # one rule
```

Type check:

```bash
mypy src/
```

Lint:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## DCO — sign your commits

We use the [Developer Certificate of Origin](https://developercertificate.org/) instead of a CLA.  
Sign every commit with `-s`:

```bash
git commit -s -m "feat(rules): add CG-SEC-006 open-redirect detection"
```

This adds a `Signed-off-by: Your Name <your@email.com>` trailer.  
PRs without DCO sign-off will not be merged.

## Changelog fragments

Any PR that touches `src/codeguard/` and has a user-visible effect must add a news
fragment under `changelog.d/` — CI enforces this. The filename is
`<id>.<type>.md` (`<id>` = issue/PR number or a short slug prefixed with `+`;
`<type>` = `breaking`, `feature`, `bugfix`, `doc`, or `internal`). One or two
past-tense sentences describing the change for a user. See `changelog.d/README.md`.
Preview with `towncrier build --draft`.

## Adding a rule

This is the most common contribution. A rule requires exactly:

1. **A rule module** in `src/codeguard/rules/<category>/`
2. **A vulnerable fixture** that the rule must trigger on
3. **A safe fixture** that the rule must NOT trigger on
4. **A docs page** in `docs/rules/<category>/`
5. Registration in the category's `__init__.py`

### Step-by-step

#### 1. Claim a rule ID

Check [docs/rules/](docs/rules/) for the next available ID. IDs are never reused or renumbered. Format: `CG-{CATEGORY}-{NNN}` where CATEGORY is one of `SEC`, `QUAL`, `PERF`, `AISM`.

Open a draft PR or issue to claim the ID before writing code, to avoid collisions.

#### 2. Write the rule module

```python
# src/codeguard/rules/security/cg_sec_NNN_my_rule.py
# SPDX-License-Identifier: Apache-2.0

"""CG-SEC-NNN — Short title.

What it catches, why it matters, CWE/OWASP reference.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import Rule


class MyRule(Rule):
    id = "CG-SEC-NNN"
    title = "Short title (≤80 chars)"
    description = (
        "What this rule detects and why it is a problem. "
        "Be specific enough that a developer who's never heard of this can understand."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-NNN"
    owasp = "ANNN:YYYY – Category Name"

    def check(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Scan the AST and return findings."""
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if self._is_vulnerable(node):
                findings.append(
                    self._make_finding(
                        node=node,
                        filename=filename,
                        fix_suggestion="How to fix this in one sentence.",
                    )
                )
        return findings

    def _is_vulnerable(self, node: ast.AST) -> bool:
        # Your detection logic here
        return False


REGISTRY.register(MyRule())
```

#### 3. Write fixtures

```
tests/fixtures/security/cg_sec_NNN/
├── vulnerable.py   # MUST trigger — code that the rule should flag
└── safe.py         # MUST NOT trigger — correct code that looks similar
```

Fixtures are real Python files. Keep them minimal: the smallest snippet that demonstrates the point. Add a comment explaining what each fixture tests.

#### 4. Write the test

```python
# tests/test_rules/security/test_cg_sec_NNN.py
from codeguard.engine.runner import AnalysisRunner

RUNNER = AnalysisRunner(rule_ids=["CG-SEC-NNN"])


def _findings_for(fixture: str) -> list:
    from pathlib import Path
    src = (Path(__file__).parent.parent.parent / "fixtures" / "security" / "cg_sec_NNN" / fixture).read_text()
    return [f for f in RUNNER.run(src, filename=fixture) if not f.suppressed]


def test_vulnerable_triggers():
    findings = _findings_for("vulnerable.py")
    assert len(findings) >= 1
    assert all(f.rule_id == "CG-SEC-NNN" for f in findings)


def test_safe_does_not_trigger():
    findings = _findings_for("safe.py")
    assert findings == []
```

#### 5. Write the docs page

```markdown
# CG-SEC-NNN — Short title

**Severity**: HIGH  
**Category**: Security  
**CWE**: [CWE-NNN](https://cwe.mitre.org/data/definitions/NNN.html)  
**OWASP**: [ANNN:YYYY](https://owasp.org/Top10/)

## What it catches

...

## Why it matters

...

## How to fix

...

## How to suppress (use sparingly)

```python
risky_call()  # codeguard: ignore[CG-SEC-NNN]
```

## False positives

...
```

#### 6. Register the rule

Add an import to `src/codeguard/rules/security/__init__.py`:

```python
from . import cg_sec_NNN_my_rule as _  # noqa: F401  (import for side-effect: registers rule)
```

### Rule quality bar

- False positives are bugs. If your rule has a known false-positive pattern, document it.
- `confidence` should be < 1.0 if the detection is heuristic.
- Rules detect one thing. If you're tempted to add a second check, make a second rule.
- Every rule needs both a vulnerable AND a safe fixture.

## Filing a bug report

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml). Include:
- CodeGuard version (`codeguard --version`)
- The code snippet that triggers (or fails to trigger) the issue
- Expected vs. actual output

## Filing a feature request / new rule request

Use the [rule request template](.github/ISSUE_TEMPLATE/rule_request.yml).

## Conventional commits

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(rules): add CG-SEC-006 open-redirect detection
fix(runner): handle files with BOM correctly
docs(CG-SEC-001): add false-positive note for Django ORM
test(CG-SEC-003): add fixture for compile() with non-literal
chore(deps): bump ruff to 0.4
```

Categories: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`.

## Code style

- `ruff` enforces style — run it before pushing, `pre-commit` will catch it anyway.
- `mypy --strict` — all public functions need type annotations and docstrings.
- Keep lines ≤ 100 chars.
- Plain language in comments and docstrings. No marketing voice.
