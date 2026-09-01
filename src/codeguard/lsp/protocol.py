# SPDX-License-Identifier: Apache-2.0
"""Small, dependency-free JSON-RPC transport for the CodeGuard LSP server."""

from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from typing import Any, BinaryIO


class JsonRpcTransport:
    def __init__(self, reader: BinaryIO, writer: BinaryIO) -> None:
        self.reader = reader
        self.writer = writer
        self._write_lock = threading.Lock()

    def read(self) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = self.reader.readline()
            if not line:
                return None
            if line in (b"\r\n", b"\n"):
                break
            name, _, value = line.decode("ascii").partition(":")
            headers[name.lower().strip()] = value.strip()

        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        payload = self.reader.read(length)
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON-RPC payload must be an object")
        return value

    def send(self, message: Mapping[str, Any]) -> None:
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii")
        with self._write_lock:
            self.writer.write(header)
            self.writer.write(payload)
            self.writer.flush()

    def respond(self, request_id: object, result: object) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def error(self, request_id: object, code: int, message: str) -> None:
        self.send(
            {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
        )

    def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

