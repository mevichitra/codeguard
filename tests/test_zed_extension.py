# SPDX-License-Identifier: Apache-2.0
"""Static contract tests for the Zed extension (behaviour: `cargo test` in editors/zed)."""

from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]
from pathlib import Path

ROOT = Path(__file__).parents[1]
ZED = ROOT / "editors" / "zed"
MANIFEST = tomllib.loads((ZED / "extension.toml").read_text(encoding="utf-8"))
CARGO = tomllib.loads((ZED / "Cargo.toml").read_text(encoding="utf-8"))
SOURCE = (ZED / "src" / "lib.rs").read_text(encoding="utf-8")


def test_manifest_registers_codeguard_lsp() -> None:
    assert MANIFEST["id"] == "codeguard"
    assert MANIFEST["lib"] == {"kind": "Rust", "version": "0.7.0"}
    assert MANIFEST["version"] == CARGO["package"]["version"] == "0.2.0"
    server = MANIFEST["language_servers"]["codeguard"]
    assert set(server["languages"]) == {"Python", "JavaScript", "JSX", "TypeScript", "TSX"}
    assert "source.fixAll.codeguard" in server["code_action_kinds"]
    assert "quickfix" in server["code_action_kinds"]


def test_code_action_kinds_match_server() -> None:
    from codeguard.lsp.actions import DASHBOARD_KIND, FIX_ALL_KIND

    kinds = set(MANIFEST["language_servers"]["codeguard"]["code_action_kinds"])
    assert {FIX_ALL_KIND, DASHBOARD_KIND, "quickfix"} == kinds


def test_binary_lookup_and_lsp_subcommand() -> None:
    assert 'worktree.which("codeguard")' in SOURCE
    assert '".venv/bin/codeguard"' in SOURCE
    assert '".venv/Scripts/codeguard.exe"' in SOURCE
    assert 'vec!["lsp".to_string()]' in SOURCE
    assert "settings.binary" in SOURCE  # lsp.codeguard.binary.path override


def test_settings_passthrough() -> None:
    assert "fn language_server_initialization_options" in SOURCE
    assert "fn language_server_workspace_configuration" in SOURCE
    assert "LspSettings::for_worktree(SERVER_NAME" in SOURCE
    assert '"client": "zed"' in SOURCE
    # Zed has no webview, so rule links keep opening the local Markdown dashboard.
    assert '"codeDescription": "dashboard"' in SOURCE
    assert 'json!({ "codeguard": section })' in SOURCE
