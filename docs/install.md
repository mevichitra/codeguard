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

## Verify

```bash
codeguard --version
codeguard scan .
```

## Other channels (v2.0)

Docker image, standalone binaries, a Homebrew tap, a GitHub Action, and a
`.pre-commit-hooks.yaml` land with v2.0. See [CI integration](ci.md).
