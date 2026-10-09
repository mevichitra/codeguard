# CG-META-002: Suppression has expired

**Severity:** MEDIUM · **Category:** meta · **Languages:** all

## What it catches
A suppression whose `until=YYYY-MM-DD` date has passed. The underlying finding is
active again.

## How to fix
Fix the finding, or renew the suppression with a new date and reason. List every
expired suppression with:

```bash
codeguard suppressions list --expired
```

See [Suppressions](../suppressions.md).
