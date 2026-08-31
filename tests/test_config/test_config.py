# SPDX-License-Identifier: Apache-2.0
"""Tests for config loading, validation, and discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from codeguard.config import ConfigError, find_config, load_config
from codeguard.config.schema import Config


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


class TestLoad:
    def test_none_is_empty_default(self) -> None:
        cfg = load_config(None)
        assert cfg == Config()
        assert cfg.fail_on == "info"
        assert cfg.gitignore is True

    def test_standalone_codeguard_toml(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path / "codeguard.toml",
            '[codeguard]\nfail_on = "high"\nexclude = ["build/**"]\n'
            '[codeguard.rules]\ndisable = ["CG-SEC-002"]\n'
            '[codeguard.rules.CG-SEC-001]\nseverity = "medium"\n'
            '[codeguard.severity_remap]\nCG-SEC-005 = "critical"\n'
            '[[codeguard.overrides]]\npath = "migrations/**"\ndisable = ["CG-SEC-001"]\n',
        )
        cfg = load_config(f)
        assert cfg.fail_on == "high"
        assert cfg.exclude == ["build/**"]
        assert cfg.disable == ["CG-SEC-002"]
        assert cfg.rules["CG-SEC-001"].severity == "medium"
        assert cfg.severity_remap["CG-SEC-005"] == "critical"
        assert cfg.overrides[0].path == "migrations/**"
        assert cfg.overrides[0].disable == ["CG-SEC-001"]

    def test_pyproject_tool_table(self, tmp_path: Path) -> None:
        f = _write(
            tmp_path / "pyproject.toml",
            '[project]\nname = "x"\n\n[tool.codeguard]\nfail_on = "critical"\n',
        )
        assert load_config(f).fail_on == "critical"

    def test_pyproject_without_tool_table_is_empty(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
        assert load_config(f) == Config(source_dir=str(tmp_path))


class TestValidationErrors:
    @pytest.mark.parametrize(
        "doc",
        [
            "[codeguard]\nnonsense = 1\n",
            '[codeguard]\nfail_on = "sometimes"\n',
            '[codeguard]\nexclude = "not-a-list"\n',
            "[codeguard]\ngitignore = 3\n",
            '[codeguard.rules.CG-SEC-001]\nseverity = "extreme"\n',
            "[[codeguard.overrides]]\ndisable = []\n",  # missing path
            '[codeguard]\nlanguages = ["cobol"]\n',
        ],
    )
    def test_rejected(self, tmp_path: Path, doc: str) -> None:
        f = _write(tmp_path / "codeguard.toml", doc)
        with pytest.raises(ConfigError):
            load_config(f)

    def test_bad_toml_syntax(self, tmp_path: Path) -> None:
        f = _write(tmp_path / "codeguard.toml", "[codeguard\nbroken")
        with pytest.raises(ConfigError, match="invalid TOML"):
            load_config(f)


class TestFindConfig:
    def test_walks_up_to_git_root(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        _write(tmp_path / "codeguard.toml", "[codeguard]\n")
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert find_config(deep) == tmp_path / "codeguard.toml"

    def test_returns_none_when_absent(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        assert find_config(tmp_path) is None
