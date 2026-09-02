# SPDX-License-Identifier: Apache-2.0
"""Tests for CodeGuard's Language Server Protocol adapter."""

from __future__ import annotations

import json
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from codeguard.cli.main import cli
from codeguard.engine.finding import Category, Finding, Location, Severity
from codeguard.lsp.protocol import JsonRpcTransport
from codeguard.lsp.server import (
    CodeGuardLanguageServer,
    Document,
    finding_to_diagnostic,
    uri_to_path,
)

VULNERABLE = 'password = "secret-value"\n'


class RecordingTransport:
    def __init__(self) -> None:
        self.notifications: list[tuple[str, dict[str, Any]]] = []
        self._lock = threading.Lock()

    def notify(self, method: str, params: dict[str, Any]) -> None:
        with self._lock:
            self.notifications.append((method, params))

    def send(self, message: dict[str, Any]) -> None:
        with self._lock:
            self.notifications.append((message["method"], message["params"]))


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
    assert diagnostic["severity"] == 2
    assert diagnostic["code"] == "CG-SEC-001"
    assert diagnostic["source"] == "CodeGuard"
    assert diagnostic["message"].startswith("🛡 Unsafe query")
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
    diagnostic = next(
        params["diagnostics"][0]
        for params in published
        if params["uri"] == source.as_uri() and params["diagnostics"]
    )
    assert diagnostic["codeDescription"]["href"].startswith("file://")


def test_live_changes_publish_only_latest_generation(tmp_path: Path, monkeypatch: Any) -> None:
    import codeguard.lsp.server as server_module

    monkeypatch.setattr(server_module, "DEBOUNCE_SECONDS", 0.02)
    source = tmp_path / "live.py"
    source.write_text("x = 1\n", encoding="utf-8")
    server, transport = _server(tmp_path)
    uri = source.as_uri()
    server._did_open({"textDocument": {"uri": uri, "text": VULNERABLE, "version": 1}})
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


def test_invalid_intermediate_syntax_clears_codeguard_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "broken.py"
    source.write_text(VULNERABLE, encoding="utf-8")
    server, transport = _server(tmp_path)
    uri = source.as_uri()
    server.documents[uri] = Document(source, "def broken(:\n", 1)

    server._scan_open_document(uri)
    server.close()

    assert transport.notifications[-1][1]["diagnostics"] == []


def test_registers_config_watchers_when_client_supports_them(tmp_path: Path) -> None:
    server, transport = _server(tmp_path)
    server._client_capabilities = {
        "workspace": {"didChangeWatchedFiles": {"dynamicRegistration": True}}
    }

    server._register_config_watchers()
    server.close()

    method, params = transport.notifications[-1]
    assert method == "client/registerCapability"
    patterns = {
        watcher["globPattern"]
        for watcher in params["registrations"][0]["registerOptions"]["watchers"]
    }
    assert "**/codeguard.toml" in patterns


def test_code_lens_summarizes_workspace_warnings(tmp_path: Path) -> None:
    source = tmp_path / "bad.py"
    source.write_text(VULNERABLE, encoding="utf-8")
    server, _ = _server(tmp_path)
    uri = source.as_uri()
    server._scan_workspace()

    lenses = server._code_lenses({"textDocument": {"uri": uri}})
    server.close()

    command = lenses[0]["command"]
    assert command["command"] == "codeguard.openDashboard"
    assert "🛡 CodeGuard" in command["title"]
    assert "1 workspace warning" in command["title"]


def test_code_action_opens_dashboard_for_codeguard_warning(tmp_path: Path) -> None:
    server, _ = _server(tmp_path)
    uri = (tmp_path / "bad.py").as_uri()

    actions = server._code_actions(
        {
            "textDocument": {"uri": uri},
            "context": {"diagnostics": [{"source": "CodeGuard"}]},
        }
    )
    server.close()

    assert actions[0]["title"] == "🛡 Open CodeGuard Dashboard"
    assert actions[0]["command"]["command"] == "codeguard.openDashboard"


def test_open_dashboard_requests_local_markdown_document(tmp_path: Path, monkeypatch: Any) -> None:
    import codeguard.lsp.server as server_module

    source = tmp_path / "bad.py"
    source.write_text(VULNERABLE, encoding="utf-8")
    server, transport = _server(tmp_path)
    original_write = server_module.write_dashboard
    monkeypatch.setattr(
        server_module,
        "write_dashboard",
        lambda findings, root: original_write(findings, root, output=tmp_path / "dashboard.md"),
    )

    server._open_dashboard()
    server.close()

    show_requests = [
        params for method, params in transport.notifications if method == "window/showDocument"
    ]
    assert show_requests
    report_path = uri_to_path(show_requests[-1]["uri"])
    assert report_path.is_file()
    assert "CodeGuard Dashboard" in report_path.read_text(encoding="utf-8")


def test_lsp_command_is_registered() -> None:
    result = CliRunner().invoke(cli, ["lsp", "--help"])
    assert result.exit_code == 0
    assert "language server" in result.output.lower()


def test_stdio_protocol_initialize_shutdown_round_trip(tmp_path: Path) -> None:
    def frame(message: dict[str, Any]) -> bytes:
        payload = json.dumps(message).encode("utf-8")
        return f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload

    incoming = BytesIO(
        b"".join(
            [
                frame(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"rootUri": tmp_path.as_uri()},
                    }
                ),
                frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}),
                frame({"jsonrpc": "2.0", "method": "exit"}),
            ]
        )
    )
    outgoing = BytesIO()

    CodeGuardLanguageServer(incoming, outgoing).run()
    output_reader = JsonRpcTransport(BytesIO(outgoing.getvalue()), BytesIO())

    initialize = output_reader.read()
    shutdown = output_reader.read()
    assert initialize is not None
    assert initialize["id"] == 1
    assert initialize["result"]["serverInfo"]["name"] == "CodeGuard"
    assert shutdown == {"jsonrpc": "2.0", "id": 2, "result": None}
