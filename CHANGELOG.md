# Changelog

All notable changes to CodeGuard are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
CodeGuard follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html); until
`2.0.0` the public interfaces (rule IDs, `Finding` schema, CLI flags) are not stable.

Entries under a released version are assembled by [towncrier](https://towncrier.readthedocs.io/)
from news fragments in `changelog.d/`. Unreleased changes live as fragments in that
directory — run `towncrier build --draft` to preview them.

The road to **v2.0** is a multi-language (Python + JavaScript + TypeScript) SAST CLI;
see `docs/` and the milestone plan. Planned breaking changes are tracked as `breaking`
fragments so the migration guide can be written incrementally.

<!-- towncrier release notes start -->

## [0.1.0]

Initial alpha: AST rule engine, CLI (`scan`), and five security rules
(CG-SEC-001..005) with human / JSON / SARIF output and inline suppression comments.

[0.1.0]: https://github.com/mevichitra/codeguard/releases/tag/v0.1.0
