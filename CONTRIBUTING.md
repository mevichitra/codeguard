# Contributing to CodeGuard

Thanks for considering a contribution. This guide covers everything you need.

## Quick orientation

CodeGuard is a pure Python library + CLI. No database, no web stack. The core abstraction is:

```
Rule → AnalysisRunner → [Finding, ...]   (optionally with Fix and related locations)
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

1. **A rule module** in the package for its category: `src/codeguard/rules/security/`
   (Python security), `rules/javascript/` (JS/TS security), `rules/performance/`, or
   `rules/quality/`
2. **A `vulnerable` fixture** that the rule must trigger on, and a **`safe` fixture** it
   must NOT trigger on (for performance and quality rules these mean "reported" and "not
   reported")
3. **A `fixed` fixture** if the rule has an autofix
4. **A test**
5. **A docs page** in `docs/rules/<ID>.md`, listed in `docs/rules/index.md` and the
   `mkdocs.yml` nav (`tests/test_docs.py` enforces this)
6. Registration in the package's `__init__.py`

### Step-by-step

#### 1. Claim a rule ID

Check [docs/rules/](docs/rules/) for the next available ID. IDs are never reused or
renumbered. Format: `CG-{CATEGORY}-{NNN}` where CATEGORY is one of `SEC`, `PERF`, `QUAL`,
`AISM`; `0xx` numbers are Python and `1xx` are JavaScript / TypeScript.

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
from codeguard.engine.rule import AstRule


class MyRule(AstRule):
    id = "CG-SEC-NNN"
    title = "Short title (<= 80 chars)"
    description = (
        "What this rule detects and why it is a problem. "
        "Be specific enough that a developer who's never heard of this can understand."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-NNN"
    owasp = "ANNN:YYYY - Category Name"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
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

**Python rules subclass `AstRule`** and implement `check_ast(tree, source, filename)`.
**JavaScript / TypeScript rules subclass `TreeSitterRule`** with
`languages = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})` and implement
`check_tree(root, ctx)` over the uniform `SourceNode` API.

Reuse the shared helpers instead of re-walking trees:

| Helper | For |
|---|---|
| `rules/_pyimports.ImportMap` | resolving `from x import y` / `import x as z` |
| `rules/_pysinks` | what counts as a SQL / shell / eval / path / redirect call |
| `rules/_pyparents.PyParents` | parents, enclosing loop or function, security-flavoured binding names |
| `rules/_pycomplexity`, `rules/_jscomplexity` | cyclomatic complexity, nesting, parameters |
| `rules/_jsnodes` | calls, arguments, literals, enclosing loop and binding, request-data patterns |

**Options.** Tunable thresholds go in `default_options = {"max_complexity": 15}`; read
them with `ctx.option("max_complexity")` from `analyze(ctx)`. Users override them under
`[rules.<ID>]`, and unknown names are rejected.

**Autofix.** Set `autofix = True` and pass `fix=Fix(description, (edit, ...))` to
`_make_finding`. Build edits with `engine.fixes.edit_for_ast_node`,
`edit_for_source_node`, or `line_insert`. Only attach a fix when the rewrite provably
keeps behaviour; otherwise give a `fix_suggestion` and no fix. See
[docs/autofix.md](docs/autofix.md).

**Taint rules.** Subclass `rules/security/_taint.TaintRule` and implement
`sink(call, imports)`, returning the argument to check. Sources, sanitizers, and
propagators live in `engine/dataflow/catalog.py`. If the rule replaces a pattern rule's
finding on the same line, set `supersedes = frozenset({"CG-SEC-00X"})`.

**Categories.** `scan` / `ci` run security rules by default. Performance and quality
rules run when a project opts in, and always in editors. Pick severities accordingly:
performance and quality rules are usually `LOW` or `INFO`.

#### 3. Write fixtures

```
tests/fixtures/<language>/<category>/<rule_id>/
├── vulnerable.<ext>   # MUST trigger
├── safe.<ext>         # MUST NOT trigger -- correct code that looks similar
└── fixed.<ext>        # autofix rules only: vulnerable.<ext> after the fixes
```

`<language>` is `python` / `javascript` / `typescript`; `<category>` is `security` /
`performance` / `quality`; `<ext>` is `py` / `js` / `ts` / `tsx`. Keep fixtures minimal,
with a comment explaining what each case tests.

#### 4. Write the test

New rules add one line to `CASES` in `tests/test_rules/test_rule_packs.py`:

```python
("python", "security", "cg_sec_NNN", "CG-SEC-NNN", 2),  # 2 findings in vulnerable.py
```

That checks the vulnerable count, a clean `safe` fixture, the category, and (for
autofix rules) that applying the fixes reproduces `fixed.*` byte for byte and still
parses. Add focused tests for tricky cases next to it (see
`tests/test_rules/security/test_cg_sec_00*.py` and `test_taint_rules.py`).

For rules where precision matters, add true/false-positive samples under
`benchmarks/corpus/<RULE-ID>/{tp,tn}/` and check `python benchmarks/run_benchmark.py`.

#### 5. Write the docs page

Generate a starter page from the rule's metadata and fixtures, then edit it:

```bash
python scripts/scaffold_rule_docs.py
```

Add the page to the Rules section of `mkdocs.yml` and to `docs/rules/index.md`.

#### 6. Register the rule

Import the module in its package `__init__.py`:

```python
from . import cg_sec_NNN_my_rule as _NNN  # noqa: F401  (import registers the rule)
```

### Rule quality bar

- False positives are bugs. If your rule has a known false-positive pattern, document it.
- `confidence` should be < 1.0 if the detection is heuristic.
- Rules detect one thing. If you're tempted to add a second check, make a second rule.
- Every rule needs both a vulnerable AND a safe fixture.
- Run CodeGuard on a real project (`codeguard scan . --category <yours>`) and look at what
  it reports before opening the PR.

## Editor extensions

- **VS Code** (`editors/vscode`): `npm ci && npm test` compiles and runs the unit tests;
  press `F5` in VS Code to try it.
- **Zed** (`editors/zed`): `cargo test`, then
  `cargo build --release --target wasm32-wasip2`; install it with **Install Dev Extension**.
- The protocol both use is documented in [docs/editors.md](docs/editors.md). Server-side
  changes go in `src/codeguard/lsp/` with tests in `tests/test_lsp/`.

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
