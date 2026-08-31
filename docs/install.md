# Install

The PyPI project is **`codeguard-cli`**. The installed command is `codeguard`.

## As a tool (recommended)

```bash
pipx install codeguard-cli
# or
uv tool install codeguard-cli
```

## Into an environment

```bash
pip install codeguard-cli
```

Requires Python 3.10 or newer. No database, no server, no network access at runtime.

## From source

```bash
git clone https://github.com/mevichitra/codeguard
cd codeguard
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Docker

```bash
docker run --rm -v "$PWD:/src:ro" ghcr.io/mevichitra/codeguard:2 scan .
```

Tags: `:2`, `:2.0`, `:2.0.0`, `:latest`. The image runs as a non-root user with
the working directory mounted at `/src`.

## Verify

```bash
codeguard --version
codeguard scan .
```

## Other channels

- **GitHub Action**: `uses: mevichitra/codeguard/action@v2` — see [CI integration](ci.md).
- **pre-commit**: the repo ships a `.pre-commit-hooks.yaml` (ids `codeguard`,
  `codeguard-full`, `codeguard-ci`).
- Standalone single-file binaries and a Homebrew tap are planned for a follow-up release.
