# Contributing

The full guide lives in
[`CONTRIBUTING.md`](https://github.com/mevichitra/codeguard/blob/main/CONTRIBUTING.md)
at the repository root. In short:

- **Setup:** `pip install -e ".[dev]"` then `pre-commit install`.
- **Tests:** `pytest`. **Types:** `mypy src/`. **Lint:** `ruff check src/ tests/`.
- **Sign your commits:** `git commit -s` (Developer Certificate of Origin).
- **Add a news fragment:** any user-visible change needs a file in `changelog.d/`
  (see `changelog.d/README.md`).
- **Adding a rule:** one rule module + a vulnerable fixture + a safe fixture + a docs
  page + registration in the category `__init__.py`.
