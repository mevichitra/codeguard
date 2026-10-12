# Rules

Every rule has a stable ID (`CG-<CATEGORY>-<NNN>`), a severity, and a fix suggestion.
Security rules also map to CWE and OWASP. IDs are permanent: never renumbered or reused.

`0xx` IDs are Python; `1xx` IDs are JavaScript / TypeScript.

!!! note "Which rules run"
    `codeguard scan` and `codeguard ci` run **security** rules by default, so upgrading
    never changes a pipeline's exit code. Turn on more with `--category performance`
    or `categories = ["security", "performance", "quality"]` in `codeguard.toml`.
    Editors show all three categories by default. Rules named with `--rule` or
    `[rules] enable` always run.

## Security

| ID | Title | Severity | Languages | Autofix | CWE |
|---|---|---|---|---|---|
| [CG-SEC-001](CG-SEC-001.md) | SQL query built with string formatting | HIGH | Python |  | CWE-89 |
| [CG-SEC-002](CG-SEC-002.md) | Hardcoded secret | HIGH | Python |  | CWE-798 |
| [CG-SEC-003](CG-SEC-003.md) | eval() / exec() on dynamic input | HIGH | Python |  | CWE-95 |
| [CG-SEC-004](CG-SEC-004.md) | Unsafe deserialization | HIGH | Python |  | CWE-502 |
| [CG-SEC-005](CG-SEC-005.md) | subprocess with shell=True and dynamic command | HIGH | Python |  | CWE-78 |
| [CG-SEC-006](CG-SEC-006.md) | Weak hash (MD5 / SHA-1) used for a security value | MEDIUM | Python |  | CWE-328 |
| [CG-SEC-007](CG-SEC-007.md) | TLS certificate verification disabled | HIGH | Python |  | CWE-295 |
| [CG-SEC-008](CG-SEC-008.md) | Insecure temporary file name (tempfile.mktemp) | MEDIUM | Python |  | CWE-377 |
| [CG-SEC-009](CG-SEC-009.md) | random module used for a security value | MEDIUM | Python | safe | CWE-338 |
| [CG-SEC-010](CG-SEC-010.md) | Untrusted input reaches a SQL query | HIGH | Python |  | CWE-89 |
| [CG-SEC-011](CG-SEC-011.md) | Untrusted input reaches a shell command | CRITICAL | Python |  | CWE-78 |
| [CG-SEC-012](CG-SEC-012.md) | Untrusted input reaches eval() / exec() | CRITICAL | Python |  | CWE-95 |
| [CG-SEC-013](CG-SEC-013.md) | Request data used as a file path | HIGH | Python |  | CWE-22 |
| [CG-SEC-014](CG-SEC-014.md) | Request data used as a redirect target | MEDIUM | Python |  | CWE-601 |
| [CG-SEC-101](CG-SEC-101.md) | Dynamic code execution (eval / Function / string timer) | HIGH | JS, TS |  | CWE-95 |
| [CG-SEC-102](CG-SEC-102.md) | child_process.exec with a dynamic command | HIGH | JS, TS |  | CWE-78 |
| [CG-SEC-103](CG-SEC-103.md) | DOM XSS sink assigned a non-literal value | HIGH | JS, TS |  | CWE-79 |
| [CG-SEC-104](CG-SEC-104.md) | dangerouslySetInnerHTML with a non-literal value | HIGH | JS, TS |  | CWE-79 |
| [CG-SEC-105](CG-SEC-105.md) | Hardcoded secret | HIGH | JS, TS |  | CWE-798 |
| [CG-SEC-106](CG-SEC-106.md) | Math.random() used for a security value | MEDIUM | JS, TS |  | CWE-338 |
| [CG-SEC-107](CG-SEC-107.md) | Weak hash (MD5 / SHA-1) used for a security value | MEDIUM | JS, TS |  | CWE-328 |
| [CG-SEC-108](CG-SEC-108.md) | TLS certificate verification disabled | HIGH | JS, TS |  | CWE-295 |
| [CG-SEC-109](CG-SEC-109.md) | Redirect to a URL taken from the request | MEDIUM | JS, TS |  | CWE-601 |
| [CG-SEC-110](CG-SEC-110.md) | File path built from request data | HIGH | JS, TS |  | CWE-22 |
| [CG-SEC-111](CG-SEC-111.md) | Deep merge of request data (prototype pollution) | MEDIUM | JS, TS |  | CWE-1321 |

## Performance

| ID | Title | Severity | Languages | Autofix | CWE |
|---|---|---|---|---|---|
| [CG-PERF-001](CG-PERF-001.md) | Membership test against a list literal inside a loop | LOW | Python | safe |  |
| [CG-PERF-002](CG-PERF-002.md) | String built with += inside a loop | LOW | Python |  |  |
| [CG-PERF-003](CG-PERF-003.md) | for i in range(len(seq)) used to index seq | INFO | Python |  |  |
| [CG-PERF-004](CG-PERF-004.md) | Redundant .keys() in iteration or membership test | INFO | Python | safe |  |
| [CG-PERF-005](CG-PERF-005.md) | Regular expression compiled inside a loop | INFO | Python |  |  |
| [CG-PERF-101](CG-PERF-101.md) | await inside a loop runs the iterations one after another | LOW | JS, TS |  |  |
| [CG-PERF-102](CG-PERF-102.md) | Deep clone with JSON.parse(JSON.stringify(x)) | INFO | JS, TS |  |  |
| [CG-PERF-103](CG-PERF-103.md) | Accumulator copied with spread inside reduce | LOW | JS, TS |  |  |
| [CG-PERF-104](CG-PERF-104.md) | new RegExp() with a constant pattern inside a loop | LOW | JS, TS |  |  |
| [CG-PERF-105](CG-PERF-105.md) | includes() / indexOf() on an array literal inside a loop | LOW | JS, TS |  |  |

## Code quality

| ID | Title | Severity | Languages | Autofix | CWE |
|---|---|---|---|---|---|
| [CG-QUAL-001](CG-QUAL-001.md) | Mutable default argument | MEDIUM | Python |  |  |
| [CG-QUAL-002](CG-QUAL-002.md) | Exception silently swallowed | LOW | Python |  |  |
| [CG-QUAL-003](CG-QUAL-003.md) | Function is too complex | LOW | Python |  |  |
| [CG-QUAL-004](CG-QUAL-004.md) | Code is nested too deeply | LOW | Python |  |  |
| [CG-QUAL-005](CG-QUAL-005.md) | Function takes too many parameters | INFO | Python |  |  |
| [CG-QUAL-101](CG-QUAL-101.md) | Loose equality (== / !=) | LOW | JS, TS | safe |  |
| [CG-QUAL-102](CG-QUAL-102.md) | Empty catch block | LOW | JS, TS |  |  |
| [CG-QUAL-103](CG-QUAL-103.md) | Function is too complex | LOW | JS, TS |  |  |
| [CG-QUAL-104](CG-QUAL-104.md) | var declaration | INFO | JS, TS |  |  |

## Suppression hygiene

| ID | Title | Severity | Languages | Autofix | CWE |
|---|---|---|---|---|---|
| [CG-META-001](CG-META-001.md) | Suppression comment has no reason | LOW | all |  |  |
| [CG-META-002](CG-META-002.md) | Suppression has expired | MEDIUM | all |  |  |

`CG-SEC-010`..`014` use [taint tracking](../taint.md). `CG-META-*` are raised by the
suppression engine, not by code analysis; see [Suppressions](../suppressions.md).

```bash
codeguard list-rules
codeguard list-rules --category performance --fixable
codeguard explain CG-SEC-011
```
