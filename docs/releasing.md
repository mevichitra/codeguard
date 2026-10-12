# Releasing

CodeGuard publishes three things, each with its own version and changelog:

| Artifact | Version lives in | Changelog |
|---|---|---|
| `codeguard-cli` (PyPI, Docker, GitHub release) | `src/codeguard/__init__.py` | `CHANGELOG.md`, built from `changelog.d/` |
| VS Code extension | `editors/vscode/package.json` | `editors/vscode/CHANGELOG.md` |
| Zed extension | `editors/zed/extension.toml` and `Cargo.toml` | `editors/zed/CHANGELOG.md` |

## During development

- Every PR with a user-visible change to `src/codeguard/` adds a news fragment to
  `changelog.d/` (see [its README](https://github.com/mevichitra/codeguard/blob/main/changelog.d/README.md)).
  CI fails without one.
- A PR that changes an editor extension adds its entry under `## [x.y.z] - Unreleased`
  in that extension's `CHANGELOG.md`. CI fails without one.
- Preview the next CLI release notes at any time:

    ```bash
    towncrier build --draft --version X.Y.Z
    ```

## Cutting a CLI release

1. Pick the version with [Semantic Versioning](https://semver.org/): any `breaking`
   fragment means a major bump, any `feature` fragment a minor bump, otherwise a patch.
2. Set `__version__` in `src/codeguard/__init__.py`.
3. Build the changelog. This writes the new section into `CHANGELOG.md` and deletes the
   fragments it used:

    ```bash
    towncrier build --version X.Y.Z --yes
    ```

4. Open a release PR with those changes. Its edit to `CHANGELOG.md` satisfies the
   fragment check.
5. After it merges, tag the merge commit and push the tag:

    ```bash
    git tag -s vX.Y.Z -m "CodeGuard X.Y.Z"
    git push origin vX.Y.Z
    ```

    The release workflow checks that the tag matches `__version__` and that
    `CHANGELOG.md` has a `## [X.Y.Z]` section. It then runs lint, types, and tests,
    publishes to PyPI and GHCR, and creates the GitHub release.

## Releasing an editor extension

1. Make sure the extension's `CHANGELOG.md` has a `## [x.y.z] - Unreleased` section and
   that its version matches the manifest.
2. Replace `Unreleased` with the release date, in the same PR that bumps the version or
   just before tagging.
3. Build it from the [Editors workflow](https://github.com/mevichitra/codeguard/actions/workflows/editors.yml)
   artifacts or locally. `vsce package` includes `CHANGELOG.md`, and the Marketplace
   shows it on the extension page.
4. After publishing, start the next `## [x.y.z] - Unreleased` section when the next
   change lands.
