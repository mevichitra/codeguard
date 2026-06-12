## Summary

<!-- What does this PR do? One paragraph. -->

## Type of change

- [ ] Bug fix (false positive / false negative correction)
- [ ] New rule (attach rule ID from the tracker)
- [ ] Engine / runner change
- [ ] CLI change
- [ ] Docs only
- [ ] Tooling / CI

## Checklist

- [ ] `git commit -s` — DCO sign-off on all commits
- [ ] `pytest` passes locally
- [ ] `ruff check src/ tests/` clean
- [ ] `mypy src/` clean
- [ ] If adding a rule: vulnerable fixture triggers, safe fixture does NOT trigger
- [ ] If adding a rule: docs page added in `docs/rules/`
- [ ] If adding a rule: rule registered in category `__init__.py`
- [ ] CHANGELOG updated (if user-visible change)

## Rule ID (if applicable)

<!-- e.g. CG-SEC-006 -->

## Test evidence

<!-- Paste the pytest output showing the relevant tests passing -->

```
$ pytest tests/test_rules/security/test_cg_sec_NNN.py -v
```

## Notes for reviewer

<!-- Anything tricky about the implementation, known limitations, false-positive patterns to watch for -->
