# SPDX-License-Identifier: Apache-2.0
"""Dependency-free CodeGuard language server.

Capabilities: diagnostics (live, debounced, and for the whole workspace),
severity-aware mapping, quick fixes and suppressions, a fix-all source action,
hovers with data-flow paths, a code lens, and two custom requests that editor
UIs build on:

- ``codeguard/summary`` -- every active finding, grouped by file and rule.
- ``codeguard/fixAll`` -- a ``WorkspaceEdit`` with every safe fix.

After each change the server sends ``codeguard/summaryChanged`` (debounced).
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import unquote, urlparse

from codeguard import __version__
from codeguard.analysis import EDITOR_DEFAULT_CATEGORIES, AnalysisOptions, ProjectAnalyzer
from codeguard.cli.formatters import finding_help_uri
from codeguard.config import ConfigError
from codeguard.dashboard import dashboard_path, write_dashboard
from codeguard.engine.finding import Finding

from . import actions
from .actions import (
    CMD_EXPLAIN,
    CMD_FIX_ALL,
    CMD_OPEN_DASHBOARD,
    CMD_SCAN_WORKSPACE,
    COMMANDS,
    DASHBOARD_KIND,
    FIX_ALL_KIND,
    Settings,
)
from .positions import LineIndex, contains
from .protocol import JsonRpcTransport
from .summary import build_summary, counts

LOG = logging.getLogger(__name__)
DEBOUNCE_SECONDS = 0.4
SUMMARY_DEBOUNCE_SECONDS = 0.15
CACHE_SIZE = 128
#: Below this many files the workspace scan runs in-process (no worker pool).
PARALLEL_THRESHOLD = 40

# Back-compat: the 2.1 server used this ID; keep accepting it.
_LEGACY_OPEN_DASHBOARD = "codeguard.openDashboard"

#: Re-exported for callers and tests that import it from here.
finding_to_diagnostic = actions.finding_to_diagnostic


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


class CodeGuardLanguageServer:
    def __init__(self, reader: BinaryIO | None = None, writer: BinaryIO | None = None) -> None:
        self.transport = JsonRpcTransport(reader or sys.stdin.buffer, writer or sys.stdout.buffer)
        self.workspace_root = Path.cwd().resolve()
        self.documents: dict[str, Document] = {}
        self.settings = Settings()
        self._timers: dict[str, threading.Timer] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="codeguard-lsp")
        self._lock = threading.RLock()
        self._workspace_uris: set[str] = set()
        self._published_findings: dict[str, list[Finding]] = {}
        self._published_text: dict[str, str] = {}
        self._dashboard_file: Path | None = None
        self._client_capabilities: dict[str, Any] = {}
        self._next_request_id = 1
        self._analyzer: ProjectAnalyzer | None = None
        self._config_generation = 0
        self._workspace_generation = 0
        self._cache: OrderedDict[tuple[str, str, int], list[Finding]] = OrderedDict()
        self._summary_timer: threading.Timer | None = None
        self._pending: dict[int, threading.Event] = {}
        self._responses: dict[int, dict[str, Any]] = {}
        self._closed = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

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
            self._closed = True
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
            if self._summary_timer is not None:
                self._summary_timer.cancel()
                self._summary_timer = None
            for event in self._pending.values():
                event.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _dispatch(self, message: dict[str, Any]) -> bool:
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message.get("id")
        if method is None and "id" in message:
            self._on_response(message)
            return False
        try:
            if method == "initialize":
                self._initialize(params)
                self.transport.respond(request_id, self._initialize_result())
            elif method == "initialized":
                self._register_config_watchers()
                self._submit(self._startup_scan)
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
            elif method == "textDocument/hover":
                self.transport.respond(request_id, self._hover(params))
            elif method == "workspace/executeCommand":
                self.transport.respond(request_id, self._execute_command(params))
            elif method == "codeguard/summary":
                self.transport.respond(request_id, self.summary())
            elif method == "codeguard/fixAll":
                self.transport.respond(request_id, self._fix_all(params.get("uri")))
            elif method == "workspace/didChangeConfiguration":
                self._did_change_configuration(params)
            elif method == "workspace/didChangeWatchedFiles":
                self._config_changed()
            elif method == "shutdown":
                self.transport.respond(request_id, None)
            elif method == "exit":
                return True
            elif method == "$/cancelRequest" or (
                isinstance(method, str) and method.startswith("$/")
            ):
                pass
            elif request_id is not None:
                self.transport.error(request_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # pragma: no cover - defensive protocol boundary
            LOG.exception("LSP request failed: %s", method)
            if request_id is not None:
                self.transport.error(request_id, -32603, str(exc))
            else:
                self._show_error(str(exc))
        return False

    def _submit(self, fn: Any, *args: Any) -> None:
        if self._closed:
            return
        try:
            self._executor.submit(fn, *args)
        except RuntimeError:  # executor shut down
            pass

    # ------------------------------------------------------------------
    # Initialization and settings
    # ------------------------------------------------------------------

    def _initialize(self, params: dict[str, Any]) -> None:
        root_uri = params.get("rootUri")
        folders = params.get("workspaceFolders") or []
        if folders and folders[0].get("uri"):
            root_uri = folders[0]["uri"]
        if root_uri:
            self.workspace_root = uri_to_path(root_uri).resolve()
        self._client_capabilities = params.get("capabilities") or {}
        self.settings = Settings.from_dict(params.get("initializationOptions"))
        self._analyzer = None
        self._get_analyzer()  # validate project configuration during startup

    def _initialize_result(self) -> dict[str, Any]:
        return {
            "capabilities": {
                "textDocumentSync": {
                    "openClose": True,
                    "change": 1,
                    "save": {"includeText": True},
                },
                "hoverProvider": True,
                "codeLensProvider": {"resolveProvider": False},
                "codeActionProvider": {
                    "codeActionKinds": ["quickfix", FIX_ALL_KIND, DASHBOARD_KIND],
                    "resolveProvider": False,
                },
                "executeCommandProvider": {"commands": COMMANDS},
                "experimental": {
                    "codeguard": {"protocolVersion": 1, "summary": True, "fixAll": True}
                },
            },
            "serverInfo": {"name": "CodeGuard", "version": __version__},
        }

    def _analysis_options(self) -> AnalysisOptions:
        return AnalysisOptions(
            auto_reload=False,
            default_categories=EDITOR_DEFAULT_CATEGORIES,
            category_overrides=self.settings.category_overrides,
            disabled_rule_ids=self.settings.disabled_rules,
        )

    def _get_analyzer(self) -> ProjectAnalyzer | None:
        with self._lock:
            if self._analyzer is not None:
                return self._analyzer
        try:
            analyzer = ProjectAnalyzer(self.workspace_root, self._analysis_options())
        except (ConfigError, OSError, ValueError) as exc:
            LOG.warning("CodeGuard configuration is invalid: %s", exc)
            self._show_error(str(exc))
            return None
        with self._lock:
            self._analyzer = analyzer
        return analyzer

    def _did_change_configuration(self, params: dict[str, Any]) -> None:
        settings = params.get("settings")
        section = settings.get("codeguard") if isinstance(settings, dict) else None
        if isinstance(section, dict):
            self.settings = Settings.from_dict(section, base=self.settings)
        self._config_changed(rebuild=True)

    def _config_changed(self, *, rebuild: bool = False) -> None:
        with self._lock:
            self._config_generation += 1
            self._cache.clear()
            analyzer = self._analyzer
            if rebuild:
                self._analyzer = None
        if analyzer is not None and not rebuild:
            try:
                analyzer.reload()
            except (ConfigError, OSError, ValueError) as exc:
                self._show_error(str(exc))
                with self._lock:
                    self._analyzer = None
        self._submit(self._refresh_all)

    def _register_config_watchers(self) -> None:
        workspace = self._client_capabilities.get("workspace") or {}
        watched = workspace.get("didChangeWatchedFiles") or {}
        if not watched.get("dynamicRegistration"):
            return
        watchers = [
            {"globPattern": pattern}
            for pattern in (
                "**/codeguard.toml",
                "**/.codeguard.toml",
                "**/pyproject.toml",
                "**/.codeguard-baseline.json",
            )
        ]
        self._send_request(
            "client/registerCapability",
            {
                "registrations": [
                    {
                        "id": "codeguard-config-watchers",
                        "method": "workspace/didChangeWatchedFiles",
                        "registerOptions": {"watchers": watchers},
                    }
                ]
            },
        )

    # ------------------------------------------------------------------
    # Requests to the client
    # ------------------------------------------------------------------

    def _send_request(self, method: str, params: dict[str, Any], *, track: bool = False) -> int:
        with self._lock:
            request_id = self._next_request_id
            self._next_request_id += 1
            if track:
                self._pending[request_id] = threading.Event()
        self.transport.send(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        return request_id

    def _on_response(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        with self._lock:
            event = self._pending.pop(request_id, None) if isinstance(request_id, int) else None
            if event is not None:
                self._responses[request_id] = message  # type: ignore[index]
        if event is not None:
            event.set()

    def _await_response(self, request_id: int, timeout: float = 2.0) -> dict[str, Any] | None:
        with self._lock:
            event = self._pending.get(request_id)
        if event is not None:
            event.wait(timeout)
        with self._lock:
            self._pending.pop(request_id, None)
            return self._responses.pop(request_id, None)

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def _progress_token(self) -> str | None:
        window = self._client_capabilities.get("window") or {}
        if not window.get("workDoneProgress"):
            return None
        token = f"codeguard/scan/{self._workspace_generation}"
        request_id = self._send_request(
            "window/workDoneProgress/create", {"token": token}, track=True
        )
        response = self._await_response(request_id)
        if response is None or "error" in response:
            return None
        return token

    def _progress(self, token: str | None, value: dict[str, Any]) -> None:
        if token is not None:
            self.transport.notify("$/progress", {"token": token, "value": value})

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def _startup_scan(self) -> None:
        if self.settings.scan_on_startup:
            self._refresh_all()
        else:
            for uri in list(self.documents):
                self._scan_open_document(uri)

    def _refresh_all(self) -> None:
        self._scan_workspace()
        with self._lock:
            open_uris = list(self.documents)
        for uri in open_uris:
            self._scan_open_document(uri)

    def _scan_workspace(self) -> None:
        with self._lock:
            self._workspace_generation += 1
            generation = self._workspace_generation
        analyzer = self._get_analyzer()
        if analyzer is None:
            return
        token = self._progress_token()
        self._progress(
            token,
            {
                "kind": "begin",
                "title": "CodeGuard",
                "message": "Scanning workspace…",
                "cancellable": False,
            },
        )
        try:
            files = analyzer.files()
            self._progress(token, {"kind": "report", "message": f"Scanning {len(files)} files…"})
            jobs = 1 if len(files) < PARALLEL_THRESHOLD else min(os.cpu_count() or 1, 4)
            findings = analyzer.scan_workspace(jobs=jobs)
        except (ConfigError, OSError, ValueError) as exc:
            self._progress(token, {"kind": "end", "message": "Failed"})
            self._show_error(str(exc))
            return
        with self._lock:
            if generation != self._workspace_generation:
                return  # a newer scan superseded this one

        grouped: dict[str, list[Finding]] = {path_to_uri(path): [] for path in files}
        for finding in findings:
            grouped.setdefault(path_to_uri(Path(finding.location.file)), []).append(finding)
        stale_uris = self._workspace_uris - set(grouped)
        self._workspace_uris = set(grouped)
        for uri in stale_uris:
            if uri not in self.documents:
                self._publish(uri, [], text="", refresh=False)
        for uri, file_findings in grouped.items():
            if uri in self.documents:
                continue
            text = self._read_text(uri) if file_findings else ""
            self._publish(uri, file_findings, text=text, refresh=False)
        active = sum(1 for f in findings if not f.suppressed and not f.baselined)
        self._progress(token, {"kind": "end", "message": f"{active} finding(s)"})
        self._refresh_code_lenses()
        self._schedule_summary()

    def _scan_open_document(self, uri: str) -> None:
        with self._lock:
            document = self.documents.get(uri)
            if document is None:
                return
            text, path, generation = document.text, document.path, document.generation
            key = (uri, hashlib.sha256(text.encode("utf-8")).hexdigest(), self._config_generation)
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
        if cached is None:
            analyzer = self._get_analyzer()
            if analyzer is None:
                return
            try:
                findings = analyzer.scan_document(text, path)
            except SyntaxError:
                findings = []
            except (ConfigError, OSError, ValueError) as exc:
                self._show_error(str(exc))
                return
            with self._lock:
                self._cache[key] = findings
                while len(self._cache) > CACHE_SIZE:
                    self._cache.popitem(last=False)
        else:
            findings = cached
        with self._lock:
            current = self.documents.get(uri)
            if current is None or current.generation != generation:
                return
        self._publish(uri, findings, text=text)

    def _scan_saved_document(self, uri: str, path: Path) -> None:
        analyzer = self._get_analyzer()
        if analyzer is None:
            return
        try:
            findings = analyzer.scan_saved_file(path)
        except (ConfigError, OSError, ValueError) as exc:
            self._show_error(str(exc))
            return
        self._publish(uri, findings, text=self._read_text(uri) if findings else "")

    def _read_text(self, uri: str) -> str:
        try:
            return uri_to_path(uri).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def _publish(
        self, uri: str, findings: list[Finding], *, text: str | None = None, refresh: bool = True
    ) -> None:
        if text is None:
            document = self.documents.get(uri)
            text = document.text if document is not None else self._read_text(uri)
        index = LineIndex(text)
        with self._lock:
            self._published_findings[uri] = list(findings)
            self._published_text[uri] = text
            # The report path is deterministic, so links work before it is first written.
            dashboard_uri = (self._dashboard_file or dashboard_path(self.workspace_root)).as_uri()
        uri_for = {f.location.file: uri for f in findings}
        diagnostics = [
            actions.finding_to_diagnostic(
                f,
                index=index,
                settings=self.settings,
                dashboard_uri=dashboard_uri,
                uri_for=uri_for,
            )
            for f in findings
            if not f.suppressed and not f.baselined and actions.lsp_severity(f, self.settings) != 0
        ]
        self.transport.notify(
            "textDocument/publishDiagnostics", {"uri": uri, "diagnostics": diagnostics}
        )
        if refresh:
            self._refresh_code_lenses()
            self._schedule_summary()

    def _schedule_summary(self) -> None:
        with self._lock:
            if self._closed:
                return
            if self._summary_timer is not None:
                self._summary_timer.cancel()
            timer = threading.Timer(SUMMARY_DEBOUNCE_SECONDS, self._emit_summary)
            timer.daemon = True
            self._summary_timer = timer
            timer.start()

    def _emit_summary(self) -> None:
        with self._lock:
            snapshot = {uri: list(fs) for uri, fs in self._published_findings.items()}
            if self._closed:
                return
        try:
            all_findings = [f for fs in snapshot.values() for f in fs]
            self._dashboard_file = write_dashboard(all_findings, self.workspace_root)
        except OSError as exc:
            LOG.warning("could not write dashboard: %s", exc)
        self.transport.notify("codeguard/summaryChanged", {"counts": counts(snapshot)})

    def summary(self) -> dict[str, Any]:
        """The ``codeguard/summary`` response."""
        with self._lock:
            snapshot = {uri: list(fs) for uri, fs in self._published_findings.items()}
        return build_summary(snapshot, self.workspace_root)

    def _refresh_code_lenses(self) -> None:
        workspace = self._client_capabilities.get("workspace") or {}
        code_lens = workspace.get("codeLens") or {}
        if code_lens.get("refreshSupport"):
            self._send_request("workspace/codeLens/refresh", {})

    # ------------------------------------------------------------------
    # Document sync
    # ------------------------------------------------------------------

    def _did_open(self, params: dict[str, Any]) -> None:
        item = params["textDocument"]
        uri = item["uri"]
        with self._lock:
            self.documents[uri] = Document(
                path=uri_to_path(uri), text=item["text"], version=item.get("version")
            )
        self._schedule(uri, delay=0.0)

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
        self._submit(self._scan_open_document, uri)

    def _did_close(self, params: dict[str, Any]) -> None:
        uri = params["textDocument"]["uri"]
        with self._lock:
            self._cancel_timer(uri)
            document = self.documents.pop(uri, None)
        path = document.path if document else uri_to_path(uri)
        self._submit(self._scan_saved_document, uri, path)

    def _schedule(self, uri: str, *, delay: float | None = None) -> None:
        with self._lock:
            self._cancel_timer(uri)
            timer = threading.Timer(
                DEBOUNCE_SECONDS if delay is None else delay,
                lambda: self._submit(self._scan_open_document, uri),
            )
            timer.daemon = True
            self._timers[uri] = timer
            timer.start()

    def _cancel_timer(self, uri: str) -> None:
        timer = self._timers.pop(uri, None)
        if timer is not None:
            timer.cancel()

    # ------------------------------------------------------------------
    # Features
    # ------------------------------------------------------------------

    def _document_state(self, uri: str) -> tuple[list[Finding], str]:
        with self._lock:
            findings = list(self._published_findings.get(uri, []))
            document = self.documents.get(uri)
            text = document.text if document is not None else self._published_text.get(uri)
        if text is None:
            text = self._read_text(uri)
        return findings, text

    def _code_lenses(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        uri = params["textDocument"]["uri"]
        with self._lock:
            workspace = [
                f
                for findings in self._published_findings.values()
                for f in findings
                if not f.suppressed and not f.baselined
            ]
            here = sum(
                1
                for f in self._published_findings.get(uri, [])
                if not f.suppressed and not f.baselined
            )
        total = len(workspace)
        noun = "issue" if total == 1 else "issues"
        title = f"🛡 CodeGuard · {total} workspace {noun}"
        if here:
            title += f" · {here} in this file"
        return [
            {
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                "command": {
                    "title": title + " · Open dashboard",
                    "command": CMD_OPEN_DASHBOARD,
                    "arguments": [uri],
                },
            }
        ]

    def _code_actions(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        uri = params["textDocument"]["uri"]
        context = params.get("context") or {}
        diagnostics = context.get("diagnostics") or []
        only = context.get("only")
        if diagnostics and not any(item.get("source") == "CodeGuard" for item in diagnostics):
            if not only:
                return []
        request_range = params.get("range") or {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 0},
        }
        findings, text = self._document_state(uri)
        result = actions.code_actions(
            uri,
            uri_to_path(uri),
            findings,
            LineIndex(text),
            text,
            request_range,
            only,
        )
        if not only or any(DASHBOARD_KIND.startswith(k) for k in only):
            result.append(
                {
                    "title": "🛡 Open CodeGuard Dashboard",
                    "kind": DASHBOARD_KIND,
                    "command": {
                        "title": "🛡 Open CodeGuard Dashboard",
                        "command": CMD_OPEN_DASHBOARD,
                        "arguments": [uri],
                    },
                }
            )
        return result

    def _hover(self, params: dict[str, Any]) -> dict[str, Any] | None:
        uri = params["textDocument"]["uri"]
        position = params.get("position") or {}
        findings, text = self._document_state(uri)
        index = LineIndex(text)
        hits = []
        for finding in findings:
            if finding.suppressed or finding.baselined:
                continue
            rng = index.location_range(finding.location)
            if contains(rng, position):
                hits.append((finding, rng))
        if not hits:
            return None
        body = "\n\n---\n\n".join(actions.hover_markdown(f) for f, _ in hits)
        return {"contents": {"kind": "markdown", "value": body}, "range": hits[0][1]}

    def _fix_all(self, uri: str | None) -> dict[str, Any]:
        with self._lock:
            uris = [uri] if uri else list(self._published_findings)
        changes: dict[str, list[dict[str, Any]]] = {}
        count = 0
        for target in uris:
            findings, text = self._document_state(target)
            edits = actions.fix_all_edits(text, findings, LineIndex(text))
            if edits:
                changes[target] = edits
                count += len(edits)
        return {"edit": {"changes": changes}, "count": count}

    def _execute_command(self, params: dict[str, Any]) -> Any:
        command = params.get("command")
        arguments = params.get("arguments") or []
        if command in (CMD_OPEN_DASHBOARD, _LEGACY_OPEN_DASHBOARD):
            self._submit(self._open_dashboard)
        elif command == CMD_EXPLAIN and arguments:
            self._send_request(
                "window/showDocument",
                {"uri": finding_help_uri(str(arguments[0])), "external": True},
            )
        elif command == CMD_SCAN_WORKSPACE:
            self._submit(self._refresh_all)
        elif command == CMD_FIX_ALL:
            result = self._fix_all(str(arguments[0]) if arguments else None)
            if result["count"]:
                self._send_request(
                    "workspace/applyEdit",
                    {"label": "CodeGuard: fix all safe issues", "edit": result["edit"]},
                )
            return {"applied": result["count"]}
        return None

    def _open_dashboard(self) -> None:
        analyzer = self._get_analyzer()
        if analyzer is None:
            return
        try:
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

    def _show_error(self, message: str) -> None:
        self.transport.notify("window/showMessage", {"type": 1, "message": f"CodeGuard: {message}"})


def run_stdio() -> None:
    CodeGuardLanguageServer().run()
