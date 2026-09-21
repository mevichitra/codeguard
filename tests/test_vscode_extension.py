# SPDX-License-Identifier: Apache-2.0
"""Static contract tests for the bundled VS Code development extension."""

from __future__ import annotations

import json
from pathlib import Path


def test_vscode_extension_manifest_contract() -> None:
    root = Path(__file__).parents[1]
    manifest_path = root / "editors/vscode/package.json"
    assert manifest_path.exists(), "package.json must exist"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["name"] == "codeguard"
    assert manifest["displayName"] == "CodeGuard"
    assert manifest["main"] == "./out/extension.js"

    # Activation events for all supported languages
    activation_events = set(manifest.get("activationEvents", []))
    assert {
        "onLanguage:python",
        "onLanguage:javascript",
        "onLanguage:javascriptreact",
        "onLanguage:typescript",
        "onLanguage:typescriptreact",
    }.issubset(activation_events)

    # Commands registered
    commands = {cmd["command"] for cmd in manifest.get("contributes", {}).get("commands", [])}
    assert "codeguard.openDashboard" in commands
    assert "codeguard.restartServer" in commands

    # Settings contributed
    props = manifest.get("contributes", {}).get("configuration", {}).get("properties", {})
    assert "codeguard.enable" in props
    assert "codeguard.path" in props
    assert "codeguard.trace.server" in props

    # Dependencies
    deps = manifest.get("dependencies", {})
    assert "vscode-languageclient" in deps


def test_vscode_extension_source_contract() -> None:
    root = Path(__file__).parents[1]
    ext_source = (root / "editors/vscode/src/extension.ts").read_text(encoding="utf-8")
    locate_source = (root / "editors/vscode/src/locate.ts").read_text(encoding="utf-8")

    # Verifies LSP args
    assert 'args: ["lsp"]' in ext_source or 'args: ["lsp"]' in locate_source

    # Verifies supported languages in client options
    for lang in ["python", "javascript", "javascriptreact", "typescript", "typescriptreact"]:
        assert f'language: "{lang}"' in ext_source or f"language: '{lang}'" in ext_source

    # Verifies config file watchers
    for config_pattern in [
        "**/codeguard.toml",
        "**/.codeguard.toml",
        "**/pyproject.toml",
        "**/.codeguard-baseline.json",
    ]:
        assert config_pattern in ext_source

    # Verifies executable discovery in locate.ts
    assert ".venv" in locate_source
    assert "process.env.PATH" in locate_source
    assert "codeguard" in locate_source
