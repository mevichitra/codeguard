# Suppressions

Waive a finding with a comment. The leader is `#` for Python, `//` for
JavaScript / TypeScript.

## Inline (one line)

```python
query = f"SELECT * FROM users WHERE id = {uid}"  # codeguard: ignore[CG-SEC-001] reason: uid is an int
```

```javascript
const html = build(input); // codeguard: ignore[CG-SEC-103] reason: input is sanitized above
```

Multiple rules: `# codeguard: ignore[CG-SEC-001, CG-SEC-003] reason: …`.

## File-level

Anywhere in the file:

```python
# codeguard: ignore-file[CG-SEC-002] reason: this module generates test fixtures
```

(`# codeguard: disable[…]` is a deprecated spelling of `ignore-file`.)

## Reasons are required

Every suppression should carry `reason: <short explanation>`. One without a
reason still suppresses, but CodeGuard also raises **`CG-META-001`** (severity
`low`) at the comment — so unexplained waivers show up in review.

## Expiry

```python
risky()  # codeguard: ignore[CG-SEC-005] reason: pending refactor  until=2026-12-31
```

After the date the suppression stops working — the finding is active again — and
CodeGuard raises **`CG-META-002`** (severity `medium`). The expiry is evaluated
against today's date; pass `--now YYYY-MM-DD` to `scan` / `ci` /
`suppressions list` to pin it for reproducible CI.

## Audit them

```bash
codeguard suppressions list              # every suppression, with status
codeguard suppressions list --expired    # only expired ones (exit 1 if any)
codeguard suppressions list --unused     # ones that no longer suppress anything
codeguard suppressions list --format json
```

Status is `active` (currently suppressing a finding), `expired`, or `unused`
(the named rule doesn't fire there any more — safe to delete).

## Visibility

Suppressed findings are hidden by default. `--show-suppressed` reveals them
(tagged `(suppressed)`); JSON keeps `"suppressed": true`, and SARIF emits a
`suppressions[]` entry with the reason as the justification.
