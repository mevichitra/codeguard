# SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for the 2.2 language-server features."""

from __future__ import annotations

import json
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

import codeguard.lsp.server as server_module
from codeguard.lsp.protocol import JsonRpcTransport
from codeguard.lsp.server import CodeGuardLanguageServer

TAINTED = (
    "import os\nfrom flask import request\n\n"
    "def run():\n    cmd = request.args['c']\n    os.system(cmd)\n"
)
KEYS = 'label = "café ☕"; ok = "x" in d.keys()\nfor k in d.keys():\n    pass\n'


class Recorder:
    """Transport stand-in that records everything the server sends."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def _add(self, message: dict[str, Any]) -> None:
        with self._lock:
            self.sent.append(message)

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._add({"method": method, "params": params})

    def send(self, message: dict[str, Any]) -> None:
        self._add(dict(message))

    def respond(self, request_id: object, result: object) -> None:
        self._add({"id": request_id, "result": result})

    def error(self, request_id: object, code: int, message: str) -> None:
        self._add({"id": request_id, "error": {"code": code, "message": message}})

    def of(self, method: str) -> list[dict[str, Any]]:
        with self._lock:
            return [m["params"] for m in self.sent if m.get("method") == method]


@pytest.fixture
def make_server(tmp_path: Path):  # type: ignore[no-untyped-def]
    servers: list[CodeGuardLanguageServer] = []

    def factory(
        files: dict[str, str],
        options: dict[str, Any] | None = None,
        caps: dict[str, Any] | None = None,
    ):  # type: ignore[no-untyped-def]
        (tmp_path / ".git").mkdir(exist_ok=True)
        for name, body in files.items():
            (tmp_path / name).write_text(body, encoding="utf-8")
        server = CodeGuardLanguageServer(BytesIO(), BytesIO())
        recorder = Recorder()
        server.transport = recorder  # type: ignore[assignment]
        server._initialize(
            {
                "rootUri": tmp_path.as_uri(),
                "capabilities": caps or {},
                "initializationOptions": options or {},
            }
        )
        servers.append(server)
        return server, recorder

    yield factory
    for s in servers:
        s.close()


def _diagnostics_for(recorder: Recorder, uri: str) -> list[dict[str, Any]]:
    published = [p for p in recorder.of("textDocument/publishDiagnostics") if p["uri"] == uri]
    assert published, f"nothing published for {uri}"
    return published[-1]["diagnostics"]


def test_taint_finding_has_error_severity_and_related_information(make_server, tmp_path):  # type: ignore[no-untyped-def]
    server, rec = make_server({"app.py": TAINTED})
    server._scan_workspace()
    (diag,) = _diagnostics_for(rec, (tmp_path / "app.py").resolve().as_uri())
    assert diag["code"] == "CG-SEC-011"
    assert diag["severity"] == 1
    messages = [r["message"] for r in diag["relatedInformation"]]
    assert messages[0] == "Untrusted input: flask request.args"
    assert diag["relatedInformation"][0]["location"]["range"]["start"]["line"] == 4


def test_editor_shows_performance_findings_with_utf16_ranges(make_server, tmp_path):  # type: ignore[no-untyped-def]
    server, rec = make_server({"m.py": KEYS})
    uri = (tmp_path / "m.py").resolve().as_uri()
    server._scan_workspace()
    diags = _diagnostics_for(rec, uri)
    assert {d["code"] for d in diags} == {"CG-PERF-004"}
    first = min(diags, key=lambda d: d["range"]["start"]["line"])
    line = KEYS.splitlines()[0]
    utf16_col = len(line[: line.index("d.keys")].encode("utf-16-le")) // 2
    assert first["range"]["start"] == {"line": 0, "character": utf16_col}
    assert first["range"]["end"]["character"] == utf16_col + len("d.keys()")
    assert first["data"]["fix"]["edits"][0]["newText"] == "d"


def test_settings_control_categories_and_severity(make_server, tmp_path):  # type: ignore[no-untyped-def]
    uri = (tmp_path / "m.py").resolve().as_uri()
    server, rec = make_server({"m.py": KEYS}, {"categories": {"performance": False}})
    server._scan_workspace()
    assert _diagnostics_for(rec, uri) == []

    server2, rec2 = make_server({"m.py": KEYS}, {"severityMap": {"info": "error"}})
    server2._scan_workspace()
    assert {d["severity"] for d in _diagnostics_for(rec2, uri)} == {1}

    server3, rec3 = make_server({"m.py": KEYS}, {"severityMap": {"info": "off"}})
    server3._scan_workspace()
    assert _diagnostics_for(rec3, uri) == []


def test_did_change_configuration_rescans(make_server, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    uri = (tmp_path / "m.py").resolve().as_uri()
    server, rec = make_server({"m.py": KEYS})
    server._scan_workspace()
    assert _diagnostics_for(rec, uri)
    monkeypatch.setattr(server, "_submit", lambda fn, *a: fn(*a))
    server._dispatch(
        {
            "jsonrpc": "2.0",
            "method": "workspace/didChangeConfiguration",
            "params": {"settings": {"codeguard": {"categories": {"performance": False}}}},
        }
    )
    assert _diagnostics_for(rec, uri) == []


def test_project_config_categories_respected_when_editor_silent(make_server, tmp_path):  # type: ignore[no-untyped-def]
    (tmp_path / "codeguard.toml").write_text('[codeguard]\ncategories = ["security"]\n')
    server, rec = make_server({"m.py": KEYS})
    server._scan_workspace()
    assert _diagnostics_for(rec, (tmp_path / "m.py").resolve().as_uri()) == []


def test_summary_request_and_changed_notification(make_server, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(server_module, "SUMMARY_DEBOUNCE_SECONDS", 0.01)
    server, rec = make_server({"app.py": TAINTED, "m.py": KEYS, "ok.py": "x = 1\n"})
    server._scan_workspace()
    server._dispatch({"jsonrpc": "2.0", "id": 9, "method": "codeguard/summary", "params": {}})
    summary = next(m["result"] for m in rec.sent if m.get("id") == 9)
    assert summary["schemaVersion"] == 1
    assert summary["counts"]["total"] == 3
    assert summary["counts"]["bySeverity"]["critical"] == 1
    assert summary["counts"]["byCategory"] == {"performance": 2, "security": 1}
    assert summary["counts"]["fixable"] == 2 and summary["counts"]["files"] == 2
    assert [f["path"] for f in summary["files"]] == ["app.py", "m.py"]
    assert summary["rules"][0] == {
        "id": "CG-PERF-004",
        "title": summary["rules"][0]["title"],
        "severity": "info",
        "category": "performance",
        "count": 2,
        "hasFix": True,
    }
    deadline = time.time() + 2
    while not rec.of("codeguard/summaryChanged") and time.time() < deadline:
        time.sleep(0.01)
    assert rec.of("codeguard/summaryChanged")[-1]["counts"]["total"] == 3


def test_hover_through_server(make_server, tmp_path):  # type: ignore[no-untyped-def]
    server, _ = make_server({"app.py": TAINTED})
    uri = (tmp_path / "app.py").resolve().as_uri()
    server._scan_workspace()
    hover = server._hover({"textDocument": {"uri": uri}, "position": {"line": 5, "character": 6}})
    assert hover is not None
    assert "CG-SEC-011" in hover["contents"]["value"]
    assert "Data flow" in hover["contents"]["value"]
    assert (
        server._hover({"textDocument": {"uri": uri}, "position": {"line": 0, "character": 0}})
        is None
    )


def test_fix_all_request_and_command(make_server, tmp_path):  # type: ignore[no-untyped-def]
    server, rec = make_server({"m.py": KEYS})
    uri = (tmp_path / "m.py").resolve().as_uri()
    server._scan_workspace()
    server._dispatch(
        {"jsonrpc": "2.0", "id": 3, "method": "codeguard/fixAll", "params": {"uri": uri}}
    )
    result = next(m["result"] for m in rec.sent if m.get("id") == 3)
    assert result["count"] == 2
    assert all(e["newText"] == "d" for e in result["edit"]["changes"][uri])

    server._dispatch(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "workspace/executeCommand",
            "params": {"command": "codeguard.lsp.fixAll", "arguments": []},
        }
    )
    assert next(m["result"] for m in rec.sent if m.get("id") == 4) == {"applied": 2}
    apply = [m for m in rec.sent if m.get("method") == "workspace/applyEdit"]
    assert apply and uri in apply[-1]["params"]["edit"]["changes"]


def test_explain_opens_docs_externally(make_server):  # type: ignore[no-untyped-def]
    server, rec = make_server({})
    server._execute_command({"command": "codeguard.lsp.explain", "arguments": ["CG-SEC-011"]})
    show = [m for m in rec.sent if m.get("method") == "window/showDocument"][-1]["params"]
    assert show == {
        "uri": "https://mevichitra.github.io/codeguard/rules/CG-SEC-011/",
        "external": True,
    }


def test_code_action_quick_fix_via_server(make_server, tmp_path):  # type: ignore[no-untyped-def]
    server, _ = make_server({"m.py": KEYS})
    uri = (tmp_path / "m.py").resolve().as_uri()
    server._scan_workspace()
    acts = server._code_actions(
        {
            "textDocument": {"uri": uri},
            "range": {"start": {"line": 1, "character": 10}, "end": {"line": 1, "character": 10}},
            "context": {"diagnostics": [{"source": "CodeGuard"}]},
        }
    )
    assert acts[0]["kind"] == "quickfix" and acts[0]["isPreferred"]
    on_save = server._code_actions(
        {
            "textDocument": {"uri": uri},
            "context": {"diagnostics": [], "only": ["source.fixAll.codeguard"]},
        }
    )
    assert [a["kind"] for a in on_save] == ["source.fixAll.codeguard"]


def test_workspace_progress_when_client_supports_it(make_server):  # type: ignore[no-untyped-def]
    server, rec = make_server({"app.py": TAINTED}, caps={"window": {"workDoneProgress": True}})

    def answer_create() -> None:
        deadline = time.time() + 2
        while time.time() < deadline:
            creates = [m for m in rec.sent if m.get("method") == "window/workDoneProgress/create"]
            if creates:
                server._on_response({"jsonrpc": "2.0", "id": creates[-1]["id"], "result": None})
                return
            time.sleep(0.005)

    responder = threading.Thread(target=answer_create)
    responder.start()
    server._scan_workspace()
    responder.join()
    kinds = [p["value"]["kind"] for p in rec.of("$/progress")]
    assert kinds == ["begin", "report", "end"]
    assert rec.of("$/progress")[-1]["value"]["message"] == "1 finding(s)"


def test_no_progress_without_capability(make_server):  # type: ignore[no-untyped-def]
    server, rec = make_server({"app.py": TAINTED})
    server._scan_workspace()
    assert rec.of("$/progress") == []


def test_open_document_results_are_cached(make_server, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    server, rec = make_server({"m.py": "x = 1\n"})
    uri = (tmp_path / "m.py").resolve().as_uri()
    analyzer = server._get_analyzer()
    calls = {"n": 0}
    original = analyzer.scan_document

    def counting(text: str, path: Path):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return original(text, path)

    monkeypatch.setattr(analyzer, "scan_document", counting)
    server.documents[uri] = server_module.Document(tmp_path / "m.py", KEYS, 1)
    server._scan_open_document(uri)
    server.documents[uri].text = "x = 2\n"
    server._scan_open_document(uri)
    server.documents[uri].text = KEYS  # an undo back to the first text: served from cache
    server._scan_open_document(uri)
    assert calls["n"] == 2
    assert {d["code"] for d in _diagnostics_for(rec, uri)} == {"CG-PERF-004"}


def test_invalid_config_reports_error_and_recovers(make_server, tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    (tmp_path / "codeguard.toml").write_text("[codeguard]\nnot_a_key = 1\n")
    server, rec = make_server({"m.py": KEYS})
    assert server._analyzer is None
    assert any("not_a_key" in p["message"] for p in rec.of("window/showMessage"))
    (tmp_path / "codeguard.toml").write_text("[codeguard]\n")
    monkeypatch.setattr(server, "_submit", lambda fn, *a: fn(*a))
    server._dispatch({"jsonrpc": "2.0", "method": "workspace/didChangeWatchedFiles", "params": {}})
    assert _diagnostics_for(rec, (tmp_path / "m.py").resolve().as_uri())


def test_stdio_summary_round_trip(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "app.py").write_text(TAINTED, encoding="utf-8")

    def frame(message: dict[str, Any]) -> bytes:
        payload = json.dumps(message).encode("utf-8")
        return f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload

    server = CodeGuardLanguageServer(BytesIO(), BytesIO())
    out = BytesIO()
    server.transport = JsonRpcTransport(BytesIO(), out)
    server._dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"rootUri": tmp_path.as_uri()},
        }
    )
    init = json.loads(out.getvalue().split(b"\r\n\r\n", 1)[1])
    caps = init["result"]["capabilities"]
    assert caps["hoverProvider"] is True
    assert "source.fixAll.codeguard" in caps["codeActionProvider"]["codeActionKinds"]
    assert caps["executeCommandProvider"]["commands"][0] == "codeguard.lsp.openDashboard"
    assert caps["experimental"]["codeguard"]["summary"] is True
    server.close()
