# SPDX-License-Identifier: Apache-2.0
"""Static contract tests for the bundled Zed development extension."""

from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]
from pathlib import Path


def test_zed_extension_manifest_registers_codeguard_lsp() -> None:
    root = Path(__file__).parents[1]
    manifest = tomllib.loads((root / "editors/zed/extension.toml").read_text(encoding="utf-8"))

    assert manifest["id"] == "codeguard"
    assert manifest["lib"] == {"kind": "Rust", "version": "0.7.0"}
    server = manifest["language_servers"]["codeguard"]
    assert set(server["languages"]) == {
        "Python",
        "JavaScript",
        "JSX",
        "TypeScript",
        "TSX",
    }


def test_zed_extension_starts_lsp_subcommand() -> None:
    root = Path(__file__).parents[1]
    source = (root / "editors/zed/src/lib.rs").read_text(encoding="utf-8")

    assert 'worktree.which("codeguard")' in source
    assert 'let relative = ".venv/bin/codeguard"' in source
    assert 'args: vec!["lsp".to_string()]' in source
