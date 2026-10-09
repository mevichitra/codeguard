# Contributing

The full guide lives in
[`CONTRIBUTING.md`](https://github.com/mevichitra/codeguard/blob/main/CONTRIBUTING.md)
at the repository root. In short:

- **Setup:** `pip install -e ".[dev]"` then `pre-commit install`.
- **Tests:** `pytest`. **Types:** `mypy src/`. **Lint:** `ruff check src/ tests/`.
- **Sign your commits:** `git commit -s` (Developer Certificate of Origin).
- **Add a news fragment:** any user-visible change needs a file in `changelog.d/`
  (see `changelog.d/README.md`).
- **Adding a rule:** one rule module, a vulnerable and a safe fixture (plus a `fixed`
  fixture for autofix rules), a line in `tests/test_rules/test_rule_packs.py`, a docs
  page (`python scripts/scaffold_rule_docs.py` writes a starter), and registration in
  the package `__init__.py`.
- **Editor extensions:** `npm ci && npm test` in `editors/vscode`; `cargo test` and
  `cargo build --release --target wasm32-wasip2` in `editors/zed`.
