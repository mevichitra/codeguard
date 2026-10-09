# SPDX-License-Identifier: Apache-2.0
"""Static contract tests for the VS Code extension (behaviour is tested by `npm test`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
EXT = ROOT / "editors" / "vscode"
MANIFEST = json.loads((EXT / "package.json").read_text(encoding="utf-8"))
SOURCES = {p.name: p.read_text(encoding="utf-8") for p in (EXT / "src").glob("*.ts")}
ALL_SOURCE = "\n".join(SOURCES.values())
LANGS = ["python", "javascript", "javascriptreact", "typescript", "typescriptreact"]


def test_manifest_basics() -> None:
    assert MANIFEST["name"] == "codeguard"
    assert MANIFEST["displayName"] == "CodeGuard"
    assert MANIFEST["main"] == "./out/extension.js"
    assert MANIFEST["version"] == "0.2.0"
    # vscode-languageclient 9 refuses to run on VS Code older than 1.82.
    assert MANIFEST["engines"]["vscode"] == "^1.82.0"
    assert MANIFEST["devDependencies"]["@types/vscode"].lstrip("~^") == "1.82.0"
    assert "vscode-languageclient" in MANIFEST["dependencies"]
    assert {f"onLanguage:{lang}" for lang in LANGS} <= set(MANIFEST["activationEvents"])


def test_every_contributed_command_is_registered_in_code() -> None:
    contributed = {c["command"] for c in MANIFEST["contributes"]["commands"]}
    registered = set(re.findall(r'register\("([\w.]+)"', SOURCES["extension.ts"]))
    assert contributed == registered
    for required in (
        "codeguard.openDashboard",
        "codeguard.restartServer",
        "codeguard.showOverview",
        "codeguard.fixAllInWorkspace",
        "codeguard.exportSarif",
    ):
        assert required in contributed


def test_commands_referenced_in_menus_and_markdown_exist() -> None:
    contributed = {c["command"] for c in MANIFEST["contributes"]["commands"]}
    menus = MANIFEST["contributes"]["menus"]
    for entries in menus.values():
        for entry in entries:
            assert entry["command"] in contributed, entry
    text = json.dumps(MANIFEST["contributes"]) + ALL_SOURCE
    for command in re.findall(r"command:(codeguard\.[\w]+)", text):
        assert command in contributed, command


def test_server_commands_do_not_collide_with_extension_commands() -> None:
    contributed = {c["command"] for c in MANIFEST["contributes"]["commands"]}
    server = set(re.findall(r'"(codeguard\.lsp\.\w+)"', SOURCES["protocol.ts"] + SOURCES["lsp.ts"]))
    assert server and not (server & contributed)
    from codeguard.lsp.actions import COMMANDS

    assert server == set(COMMANDS)


def test_views_settings_and_walkthrough() -> None:
    c = MANIFEST["contributes"]
    assert c["viewsContainers"]["activitybar"][0]["id"] == "codeguard"
    assert (EXT / c["viewsContainers"]["activitybar"][0]["icon"]).is_file()
    assert c["views"]["codeguard"][0]["id"] == "codeguard.findings"
    assert "codeguard.findings" in SOURCES["extension.ts"]
    props = c["configuration"]["properties"]
    for key in (
        "codeguard.enable",
        "codeguard.path",
        "codeguard.trace.server",
        "codeguard.categories",
        "codeguard.severity.map",
        "codeguard.rules.disable",
        "codeguard.scanWorkspaceOnStartup",
    ):
        assert key in props
    walkthrough = c["walkthroughs"][0]
    for step in walkthrough["steps"]:
        assert (EXT / step["media"]["markdown"]).is_file()
    assert f'#{walkthrough["id"]}"' in SOURCES["extension.ts"]
    assert (EXT / "media" / "sample" / "vulnerable.py").is_file()


def test_settings_keys_match_server_parser() -> None:
    # Keys the extension sends must be the keys lsp/actions.Settings.from_dict reads.
    for key in (
        "severityMap",
        "categories",
        "rules",
        "scanWorkspaceOnStartup",
        "codeDescription",
        "client",
    ):
        assert f"{key}:" in SOURCES["lsp.ts"]
    server = (ROOT / "src" / "codeguard" / "lsp" / "actions.py").read_text(encoding="utf-8")
    for key in (
        "severityMap",
        "categories",
        "rules",
        "scanWorkspaceOnStartup",
        "codeDescription",
        "client",
    ):
        assert f'"{key}"' in server


def test_client_wiring() -> None:
    lsp = SOURCES["lsp.ts"]
    assert 'args: ["lsp"]' in lsp
    for lang in LANGS:
        assert f'language: "{lang}"' in lsp
    for pattern in (
        "**/codeguard.toml",
        "**/.codeguard.toml",
        "**/pyproject.toml",
        "**/.codeguard-baseline.json",
    ):
        assert pattern in lsp
    assert '"codeguard/summary"' in lsp and '"codeguard/fixAll"' in lsp
    assert '"codeguard/summaryChanged"' in lsp
    locate = SOURCES["locate.ts"]
    assert ".venv" in locate and "process.env.PATH" in locate


def test_webview_has_csp() -> None:
    overview = SOURCES["overview.ts"]
    assert "Content-Security-Policy" in overview
    assert "default-src 'none'" in overview
    assert "escapeHtml" in overview
