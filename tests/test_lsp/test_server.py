# SPDX-License-Identifier: Apache-2.0
"""Tests for CodeGuard's Language Server Protocol adapter."""

from __future__ import annotations

import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from codeguard.cli.main import cli
from codeguard.engine.finding import Category, Finding, Location, Severity
from codeguard.lsp.server import CodeGuardLanguageServer, finding_to_diagnostic

VULNERABLE = 'password = "secret-value"\n'


class RecordingTransport:
    def __init__(self) -> None:
        self.notifications: list[tuple[str, dict[str, Any]]] = []
        self._lock = threading.Lock()

    def notify(self, method: str, params: dict[str, Any]) -> None:
        with self._lock:
            self.notifications.append((method, params))


def _server(tmp_path: Path) -> tuple[CodeGuardLanguageServer, RecordingTransport]:
    (tmp_path / ".git").mkdir(exist_ok=True)
    server = CodeGuardLanguageServer(BytesIO(), BytesIO())
    transport = RecordingTransport()
    server.transport = transport  # type: ignore[assignment]
    server.workspace_root = tmp_path
    return server, transport


def test_finding_maps_to_native_diagnostic() -> None:
    finding = Finding(
        rule_id="CG-SEC-001",
        title="Unsafe query",
        description="Query contains interpolated input.",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        location=Location(file="app.py", line=3, col=5, end_line=3, end_col=10),
        fix_suggestion="Use parameters.",
    )

    diagnostic = finding_to_diagnostic(finding)

    assert diagnostic["range"]["start"] == {"line": 2, "character": 4}
    assert diagnostic["range"]["end"] == {"line": 2, "character": 9}
    assert diagnostic["severity"] == 1
    assert diagnostic["code"] == "CG-SEC-001"
    assert diagnostic["source"] == "CodeGuard"
    assert "Fix: Use parameters." in diagnostic["message"]
    assert diagnostic["codeDescription"]["href"].endswith("cg-sec-001/")


def test_workspace_scan_publishes_findings_for_unopened_files(tmp_path: Path) -> None:
    source = tmp_path / "bad.py"
    source.write_text(VULNERABLE, encoding="utf-8")
    server, transport = _server(tmp_path)

    server._scan_workspace()
    server.close()

    published = [
        params
        for method, params in transport.notifications
        if method.endswith("publishDiagnostics")
    ]
    assert any(params["uri"] == source.as_uri() and params["diagnostics"] for params in published)


def test_live_changes_publish_only_latest_generation(tmp_path: Path, monkeypatch: Any) -> None:
    import codeguard.lsp.server as server_module

    monkeypatch.setattr(server_module, "DEBOUNCE_SECONDS", 0.02)
    source = tmp_path / "live.py"
    source.write_text("x = 1\n", encoding="utf-8")
    server, transport = _server(tmp_path)
    uri = source.as_uri()
    server._did_open(
        {"textDocument": {"uri": uri, "text": VULNERABLE, "version": 1}}
    )
    server._did_change(
        {
            "textDocument": {"uri": uri, "version": 2},
            "contentChanges": [{"text": "x = 1\n"}],
        }
    )
    time.sleep(0.1)
    server.close()

    published = [
        params
        for method, params in transport.notifications
        if method.endswith("publishDiagnostics")
    ]
    assert published
    assert published[-1]["diagnostics"] == []
    assert not any(params["diagnostics"] for params in published)


def test_lsp_command_is_registered() -> None:
    result = CliRunner().invoke(cli, ["lsp", "--help"])
    assert result.exit_code == 0
    assert "language server" in result.output.lower()
