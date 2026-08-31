# SPDX-License-Identifier: Apache-2.0
"""Tests for `codeguard suppressions list`."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from codeguard.cli.main import cli

SRC = (
    'cur.execute(f"SELECT {a}")  # codeguard: ignore[CG-SEC-001] reason: a is safe\n'
    'cur.execute(f"SELECT {b}")  # codeguard: ignore[CG-SEC-001]\n'
    'cur.execute(f"SELECT {c}")  # codeguard: ignore[CG-SEC-001] reason: old  until=2020-01-01\n'
    "noop()  # codeguard: ignore[CG-SEC-001] reason: nothing here\n"
)


def _proj(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text(SRC, encoding="utf-8")
    return tmp_path


def test_list_table(tmp_path: Path) -> None:
    r = CliRunner().invoke(cli, ["suppressions", "list", str(_proj(tmp_path))])
    assert r.exit_code == 0
    assert "active" in r.output and "expired" in r.output and "unused" in r.output


def test_list_json_statuses(tmp_path: Path) -> None:
    r = CliRunner().invoke(cli, ["suppressions", "list", str(_proj(tmp_path)), "--format", "json"])
    by_line = {row["line"]: row["status"] for row in json.loads(r.output)}
    assert by_line == {1: "active", 2: "active", 3: "expired", 4: "unused"}


def test_expired_filter_exits_one(tmp_path: Path) -> None:
    r = CliRunner().invoke(cli, ["suppressions", "list", str(_proj(tmp_path)), "--expired"])
    assert r.exit_code == 1
    assert "a.py:3" in r.output and "a.py:1" not in r.output


def test_now_override(tmp_path: Path) -> None:
    # far in the past -> even the 2020 one is "not expired yet"? no: now < until means active.
    r = CliRunner().invoke(
        cli,
        ["suppressions", "list", str(_proj(tmp_path)), "--format", "json", "--now", "2019-01-01"],
    )
    by_line = {row["line"]: row["status"] for row in json.loads(r.output)}
    assert by_line[3] == "active"  # until=2020-01-01 is still in the future
