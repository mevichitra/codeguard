# SPDX-License-Identifier: Apache-2.0
"""Dependency-free CodeGuard language server."""

from __future__ import annotations

import logging
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import unquote, urlparse

from codeguard import __version__
from codeguard.analysis import ProjectAnalyzer
from codeguard.cli.formatters import finding_help_uri
from codeguard.config import ConfigError
from codeguard.dashboard import write_dashboard
from codeguard.engine.finding import Finding

from .protocol import JsonRpcTransport

LOG = logging.getLogger(__name__)
DEBOUNCE_SECONDS = 0.4


@dataclass
class Document:
    path: Path
    text: str
    version: int | None
    generation: int = 0


def uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    path = unquote(parsed.path)
    if os.name == "nt" and path.startswith("/") and len(path) > 2 and path[2] == ":":
        path = path[1:]
    return Path(path)


def path_to_uri(path: Path) -> str:
    return path.resolve().as_uri()


def finding_to_diagnostic(finding: Finding, *, dashboard_uri: str | None = None) -> dict[str, Any]:
    start_line = finding.location.line - 1
    start_col = finding.location.col - 1
    end_line = (finding.location.end_line or finding.location.line) - 1
    end_col = (
        finding.location.end_col - 1 if finding.location.end_col is not None else start_col + 1
    )
    message = f"🛡 {finding.title}\n{finding.description}"
    if finding.fix_suggestion:
        message += f"\n\nFix: {finding.fix_suggestion}"
    return {
        "range": {
            "start": {"line": start_line, "character": start_col},
            "end": {"line": end_line, "character": max(end_col, start_col + 1)},
        },
        "severity": 2,
        "code": finding.rule_id,
        "codeDescription": {"href": dashboard_uri or finding_help_uri(finding.rule_id)},
        "source": "CodeGuard",
        "message": message,
    }


class CodeGuardLanguageServer:
    def __init__(self, reader: BinaryIO | None = None, writer: BinaryIO | None = None) -> None:
        self.transport = JsonRpcTransport(reader or sys.stdin.buffer, writer or sys.stdout.buffer)
        self.workspace_root = Path.cwd().resolve()
        self.documents: dict[str, Document] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="codeguard-lsp")
        self._lock = threading.RLock()
        self._workspace_uris: set[str] = set()
        self._published_findings: dict[str, list[Finding]] = {}
        self._dashboard_file: Path | None = None
        self._client_capabilities: dict[str, Any] = {}
        self._next_request_id = 1

    def run(self) -> None:
        while True:
            message = self.transport.read()
            if message is None:
                break
            if self._dispatch(message):
                break
        self.close()

    def close(self) -> None:
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _dispatch(self, message: dict[str, Any]) -> bool:
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message.get("id")
        if method is None and "id" in message:
            return False
        try:
            if method == "initialize":
                self._initialize(params)
                self.transport.respond(request_id, self._initialize_result())
            elif method == "initialized":
                self._register_config_watchers()
                self._executor.submit(self._refresh_all)
            elif method == "textDocument/didOpen":
                self._did_open(params)
            elif method == "textDocument/didChange":
                self._did_change(params)
            elif method == "textDocument/didSave":
                self._did_save(params)
            elif method == "textDocument/didClose":
                self._did_close(params)
            elif method == "textDocument/codeLens":
                self.transport.respond(request_id, self._code_lenses(params))
            elif method == "textDocument/codeAction":
                self.transport.respond(request_id, self._code_actions(params))
            elif method == "workspace/executeCommand":
                self.transport.respond(request_id, None)
                if params.get("command") == "codeguard.openDashboard":
                    self._executor.submit(self._open_dashboard)
            elif method == "shutdown":
                self.transport.respond(request_id, None)
            elif method == "exit":
                return True
            elif method in (
                "$/cancelRequest",
                "workspace/didChangeConfiguration",
                "workspace/didChangeWatchedFiles",
            ):
                if method != "$/cancelRequest":
                    self._executor.submit(self._refresh_all)
            elif request_id is not None:
                self.transport.error(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # pragma: no cover - defensive protocol boundary
            LOG.exception("LSP request failed: %s", method)
            if request_id is not None:
                self.transport.error(request_id, -32603, str(exc))
            else:
                self._show_error(str(exc))
        return False

    def _initialize(self, params: dict[str, Any]) -> None:
        root_uri = params.get("rootUri")
        folders = params.get("workspaceFolders") or []
        if folders and folders[0].get("uri"):
            root_uri = folders[0]["uri"]
        if root_uri:
            self.workspace_root = uri_to_path(root_uri).resolve()
        self._client_capabilities = params.get("capabilities") or {}
        ProjectAnalyzer(self.workspace_root)  # validate project configuration during startup

    def _initialize_result(self) -> dict[str, Any]:
        return {
            "capabilities": {
                "textDocumentSync": {
                    "openClose": True,
                    "change": 1,
                    "save": {"includeText": True},
                },
                "codeLensProvider": {"resolveProvider": False},
                "codeActionProvider": True,
                "executeCommandProvider": {"commands": ["codeguard.openDashboard"]},
            },
            "serverInfo": {"name": "CodeGuard", "version": __version__},
        }

    def _register_config_watchers(self) -> None:
        workspace = self._client_capabilities.get("workspace") or {}
        watched = workspace.get("didChangeWatchedFiles") or {}
        if not watched.get("dynamicRegistration"):
            return
        request_id = self._next_request_id
        self._next_request_id += 1
        watchers = [
            {"globPattern": pattern}
            for pattern in (
                "**/codeguard.toml",
                "**/.codeguard.toml",
                "**/pyproject.toml",
                "**/.codeguard-baseline.json",
            )
        ]
        self.transport.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "client/registerCapability",
                "params": {
                    "registrations": [
                        {
                            "id": "codeguard-config-watchers",
                            "method": "workspace/didChangeWatchedFiles",
                            "registerOptions": {"watchers": watchers},
                        }
                    ]
                },
            }
        )

    def _refresh_all(self) -> None:
        self._scan_workspace()
        with self._lock:
            open_uris = list(self.documents)
        for uri in open_uris:
            self._scan_open_document(uri)

    def _code_lenses(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        uri = params["textDocument"]["uri"]
        with self._lock:
            count = sum(
                1
                for findings in self._published_findings.values()
                for finding in findings
                if not finding.suppressed and not finding.baselined
            )
        noun = "warning" if count == 1 else "warnings"
        return [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 0},
                },
                "command": {
                    "title": f"🛡 CodeGuard · {count} workspace {noun} · Open dashboard",
                    "command": "codeguard.openDashboard",
                    "arguments": [uri],
                },
            }
        ]

    def _code_actions(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        diagnostics = params.get("context", {}).get("diagnostics", [])
        if diagnostics and not any(item.get("source") == "CodeGuard" for item in diagnostics):
            return []
        uri = params["textDocument"]["uri"]
        return [
            {
                "title": "🛡 Open CodeGuard Dashboard",
                "kind": "source.codeguard.dashboard",
                "command": {
                    "title": "🛡 Open CodeGuard Dashboard",
                    "command": "codeguard.openDashboard",
                    "arguments": [uri],
                },
            }
        ]

    def _did_open(self, params: dict[str, Any]) -> None:
        item = params["textDocument"]
        uri = item["uri"]
        with self._lock:
            self.documents[uri] = Document(
                path=uri_to_path(uri), text=item["text"], version=item.get("version")
            )
        self._schedule(uri)

    def _did_change(self, params: dict[str, Any]) -> None:
        item = params["textDocument"]
        uri = item["uri"]
        changes = params.get("contentChanges") or []
        if not changes:
            return
        with self._lock:
            document = self.documents.get(uri)
            if document is None:
                document = Document(uri_to_path(uri), changes[-1]["text"], item.get("version"))
                self.documents[uri] = document
            else:
                document.text = changes[-1]["text"]
                document.version = item.get("version")
            document.generation += 1
        self._schedule(uri)

    def _did_save(self, params: dict[str, Any]) -> None:
        uri = params["textDocument"]["uri"]
        with self._lock:
            document = self.documents.get(uri)
            if document is not None and "text" in params:
                document.text = params["text"]
                document.generation += 1
            self._cancel_timer(uri)
        self._executor.submit(self._scan_open_document, uri)

    def _did_close(self, params: dict[str, Any]) -> None:
        uri = params["textDocument"]["uri"]
        with self._lock:
            self._cancel_timer(uri)
            document = self.documents.pop(uri, None)
        path = document.path if document else uri_to_path(uri)
        self._executor.submit(self._scan_saved_document, uri, path)

    def _schedule(self, uri: str) -> None:
        with self._lock:
            self._cancel_timer(uri)
            timer = threading.Timer(
                DEBOUNCE_SECONDS, lambda: self._executor.submit(self._scan_open_document, uri)
            )
            timer.daemon = True
            self._timers[uri] = timer
            timer.start()

    def _cancel_timer(self, uri: str) -> None:
        timer = self._timers.pop(uri, None)
        if timer is not None:
            timer.cancel()

    def _scan_workspace(self) -> None:
        try:
            analyzer = ProjectAnalyzer(self.workspace_root)
            findings = analyzer.scan_workspace()
            dashboard_file = write_dashboard(findings, self.workspace_root)
        except (ConfigError, OSError, ValueError) as exc:
            self._show_error(str(exc))
            return

        self._dashboard_file = dashboard_file

        grouped: dict[str, list[Finding]] = {path_to_uri(path): [] for path in analyzer.files()}
        for finding in findings:
            grouped.setdefault(path_to_uri(Path(finding.location.file)), []).append(finding)
        current_uris = set(grouped)
        stale_uris = self._workspace_uris - current_uris
        self._workspace_uris = current_uris
        for uri in stale_uris:
            with self._lock:
                if uri in self.documents:
                    continue
            self._publish(uri, [], refresh_code_lenses=False, update_dashboard=False)
        for uri, file_findings in grouped.items():
            with self._lock:
                if uri in self.documents:
                    continue
            self._publish(uri, file_findings, refresh_code_lenses=False, update_dashboard=False)
        self._refresh_code_lenses()

    def _scan_open_document(self, uri: str) -> None:
        with self._lock:
            document = self.documents.get(uri)
            if document is None:
                return
            text = document.text
            path = document.path
            generation = document.generation
        try:
            analyzer = ProjectAnalyzer(self.workspace_root)
            findings = analyzer.scan_document(text, path)
        except SyntaxError:
            findings = []
        except (ConfigError, OSError, ValueError) as exc:
            self._show_error(str(exc))
            return
        with self._lock:
            current = self.documents.get(uri)
            if current is None or current.generation != generation:
                return
        self._publish(uri, findings)

    def _scan_saved_document(self, uri: str, path: Path) -> None:
        try:
            analyzer = ProjectAnalyzer(self.workspace_root)
            findings = analyzer.scan_saved_file(path)
        except (ConfigError, OSError, ValueError) as exc:
            self._show_error(str(exc))
            return
        self._publish(uri, findings)

    def _publish(
        self,
        uri: str,
        findings: list[Finding],
        *,
        refresh_code_lenses: bool = True,
        update_dashboard: bool = True,
    ) -> None:
        active = [item for item in findings if not item.suppressed and not item.baselined]
        with self._lock:
            self._published_findings[uri] = list(findings)
            all_findings = [
                item for published in self._published_findings.values() for item in published
            ]
        if update_dashboard:
            try:
                self._dashboard_file = write_dashboard(all_findings, self.workspace_root)
            except OSError as exc:
                self._show_error(str(exc))
        dashboard_uri = self._dashboard_file.as_uri() if self._dashboard_file else None
        self.transport.notify(
            "textDocument/publishDiagnostics",
            {
                "uri": uri,
                "diagnostics": [
                    finding_to_diagnostic(item, dashboard_uri=dashboard_uri) for item in active
                ],
            },
        )
        if refresh_code_lenses:
            self._refresh_code_lenses()

    def _refresh_code_lenses(self) -> None:
        workspace = self._client_capabilities.get("workspace") or {}
        code_lens = workspace.get("codeLens") or {}
        if not code_lens.get("refreshSupport"):
            return
        self._send_request("workspace/codeLens/refresh", {})

    def _open_dashboard(self) -> None:
        try:
            analyzer = ProjectAnalyzer(self.workspace_root)
            findings = analyzer.scan_workspace()
            target = write_dashboard(findings, self.workspace_root)
        except (ConfigError, OSError, ValueError) as exc:
            self._show_error(str(exc))
            return
        self._dashboard_file = target
        self._send_request(
            "window/showDocument",
            {"uri": target.as_uri(), "external": False, "takeFocus": True},
        )
        self.transport.notify(
            "window/showMessage",
            {"type": 3, "message": f"CodeGuard dashboard updated: {target}"},
        )

    def _send_request(self, method: str, params: dict[str, Any]) -> None:
        with self._lock:
            request_id = self._next_request_id
            self._next_request_id += 1
        self.transport.send(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )

    def _show_error(self, message: str) -> None:
        self.transport.notify("window/showMessage", {"type": 1, "message": f"CodeGuard: {message}"})


def run_stdio() -> None:
    CodeGuardLanguageServer().run()
