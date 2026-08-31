# changelog.d/ — news fragments

Every PR with a user-visible change adds a fragment here. At release time
`towncrier build` folds them into `CHANGELOG.md` and deletes them.

**Filename:** `<id>.<type>.md` where `<id>` is the issue or PR number (or a short
slug if there is none), and `<type>` is one of:

| type | section |
|---|---|
| `breaking` | Breaking changes |
| `feature` | Added |
| `bugfix` | Fixed |
| `doc` | Documentation |
| `internal` | Internal (tooling, refactors, CI) |

**Content:** one or two sentences, past tense, describing the change from a user's
point of view. Example — `123.feature.md`:

```
`codeguard ci` scans only files changed since the merge-base and uploads SARIF.
```

Preview the assembled changelog without writing it:

```
towncrier build --draft
```
