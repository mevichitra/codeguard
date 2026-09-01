# SPDX-License-Identifier: Apache-2.0
"""Tests for project-level analysis shared with editor integrations."""

from __future__ import annotations

from pathlib import Path

from codeguard.analysis import ProjectAnalyzer

VULNERABLE = 'password = "secret-value"\n'


def test_workspace_and_document_share_exclusion_policy(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    included = tmp_path / "src" / "bad.py"
    excluded = tmp_path / "generated" / "bad.py"
    included.parent.mkdir()
    excluded.parent.mkdir()
    included.write_text(VULNERABLE, encoding="utf-8")
    excluded.write_text(VULNERABLE, encoding="utf-8")
    (tmp_path / "codeguard.toml").write_text(
        '[codeguard]\nexclude = ["generated/**"]\n', encoding="utf-8"
    )

    analyzer = ProjectAnalyzer(tmp_path)
    workspace_files = {Path(item.location.file) for item in analyzer.scan_workspace(jobs=1)}

    assert included in workspace_files
    assert excluded not in workspace_files
    assert analyzer.scan_document(VULNERABLE, included)
    assert analyzer.scan_document(VULNERABLE, excluded) == []


def test_document_fingerprint_is_relative_to_workspace(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    source = tmp_path / "src" / "bad.py"
    source.parent.mkdir()
    source.write_text(VULNERABLE, encoding="utf-8")

    analyzer = ProjectAnalyzer(tmp_path)
    workspace = analyzer.scan_workspace(jobs=1)
    document = analyzer.scan_document(VULNERABLE, source)

    assert {item.fingerprint for item in workspace} == {item.fingerprint for item in document}

