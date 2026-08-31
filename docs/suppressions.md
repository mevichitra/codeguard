# Suppressions

## Inline (one line)

```python
query = f"SELECT * FROM users WHERE id = {uid}"  # codeguard: ignore[CG-SEC-001]
```

Multiple rules on one line:

```python
risky()  # codeguard: ignore[CG-SEC-001, CG-SEC-003]
```

## File-level

Anywhere in the file:

```python
# codeguard: disable[CG-SEC-002]
```

## Visibility

Suppressed findings are not lost. They appear with `--show-suppressed`, as
`"suppressed": true` in JSON, and as `suppressions[]` entries in SARIF, so suppression
usage can be audited.

!!! note "Changing in v2.0"
    Suppressions gain a **mandatory `reason:`** (a bare suppression still works but raises
    `CG-META-001`), an optional `until=YYYY-MM-DD` expiry (`CG-META-002` once expired),
    per-language comment syntax (`//` for JS/TS), and a `codeguard suppressions list
    --expired` command. `disable[…]` is renamed to `ignore-file[…]` (old spelling kept as
    a deprecated alias).
