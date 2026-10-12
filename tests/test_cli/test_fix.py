# SPDX-License-Identifier: Apache-2.0
"""`codeguard scan --fix` / `--fix-dry-run` / `--category`, and fix-aware list-rules/explain."""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner

from codeguard.cli.main import EXIT_FINDINGS, EXIT_OK, EXIT_USAGE, cli
from codeguard.engine.finding import Category, Finding, Fix, Severity
from codeguard.engine.fixes import edit_for_ast_node
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule


class _KeysRule(AstRule):
    """Test rule: flags `X.keys()` and fixes it to `X`."""

    id = "CG-TEST-FIX"
    title = "redundant keys()"
    description = "d"
    severity = Severity.LOW
    category = Category.PERFORMANCE
    autofix = True
    default_options = {"enabled": True}  # noqa: RUF012

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        out = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "keys"
                and isinstance(node.func.value, ast.Name)
            ):
                edit = edit_for_ast_node(node, node.func.value.id)
                out.append(
                    self._make_finding(
                        node=node, filename=filename, fix=Fix("Drop .keys()", (edit,))
                    )
                )
        return out


@pytest.fixture
def fix_rule() -> Iterator[None]:
    REGISTRY.register(_KeysRule())
    try:
        yield
    finally:
        REGISTRY._rules.pop("CG-TEST-FIX", None)


def _proj(tmp_path: Path, body: str) -> Path:
    (tmp_path / ".git").mkdir()
    target = tmp_path / "m.py"
    target.write_bytes(body.encode("utf-8"))
    return target


SRC = "for k in d.keys():\r\n    print(k, 'é')\r\nx = k in e.keys()\r\n"


def test_fix_dry_run_prints_diff_and_changes_nothing(tmp_path: Path, fix_rule: None) -> None:
    target = _proj(tmp_path, SRC)
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--rule", "CG-TEST-FIX", "--fix-dry-run"])
    assert r.exit_code == EXIT_FINDINGS
    assert "-for k in d.keys():" in r.output and "+for k in d:" in r.output
    assert target.read_bytes() == SRC.encode()


def test_fix_writes_file_preserving_bytes_and_exits_clean(tmp_path: Path, fix_rule: None) -> None:
    target = _proj(tmp_path, SRC)
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--rule", "CG-TEST-FIX", "--fix"])
    assert r.exit_code == EXIT_OK, r.output
    assert target.read_bytes() == "for k in d:\r\n    print(k, 'é')\r\nx = k in e\r\n".encode()
    assert "Fixed 2 finding(s) in 1 file" in r.output


def test_fix_json_reports_post_fix_state(tmp_path: Path, fix_rule: None) -> None:
    _proj(tmp_path, SRC)
    r = CliRunner().invoke(
        cli, ["scan", str(tmp_path), "--rule", "CG-TEST-FIX", "--fix", "-q", "--format", "json"]
    )
    assert json.loads(r.stdout)["summary"]["findings"] == 0


def test_json_reports_fix_and_fixable(tmp_path: Path, fix_rule: None) -> None:
    _proj(tmp_path, SRC)
    r = CliRunner().invoke(
        cli, ["scan", str(tmp_path), "--rule", "CG-TEST-FIX", "--format", "json"]
    )
    out = json.loads(r.stdout)
    assert out["summary"]["fixable"] == 2
    fix = out["results"][0]["fix"]
    assert fix["safe"] is True and fix["edits"][0]["replacement"] == "d"


def test_sarif_emits_fixes(tmp_path: Path, fix_rule: None) -> None:
    _proj(tmp_path, SRC)
    r = CliRunner().invoke(
        cli, ["scan", str(tmp_path), "--rule", "CG-TEST-FIX", "--format", "sarif"]
    )
    result = json.loads(r.stdout)["runs"][0]["results"][0]
    replacement = result["fixes"][0]["artifactChanges"][0]["replacements"][0]
    assert replacement["insertedContent"]["text"] == "d"
    assert replacement["deletedRegion"]["startLine"] == 1


def test_fix_rejects_stdin() -> None:
    r = CliRunner().invoke(cli, ["scan", "-", "--fix"], input="x = 1\n")
    assert r.exit_code == EXIT_USAGE


def test_category_filter(tmp_path: Path, fix_rule: None) -> None:
    _proj(tmp_path, 'password = "hunter2hunter2"\nfor k in d.keys(): pass\n')
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--category", "performance"])
    assert "CG-TEST-FIX" in r.output and "CG-SEC-002" not in r.output
    r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--category", "security"])
    assert "CG-SEC-002" in r.output and "CG-TEST-FIX" not in r.output


def test_unknown_rule_option_is_config_error(tmp_path: Path) -> None:
    _proj(tmp_path, "x = 1\n")
    (tmp_path / "codeguard.toml").write_text("[codeguard.rules.CG-SEC-001]\nbogus = 1\n")
    r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
    assert r.exit_code == 3
    r = CliRunner().invoke(cli, ["validate", "--config", str(tmp_path / "codeguard.toml")])
    assert r.exit_code == 3 and "bogus" in r.output


def test_list_rules_fixable_and_explain(fix_rule: None) -> None:
    r = CliRunner().invoke(cli, ["list-rules", "--fixable", "--format", "json"])
    rows = json.loads(r.output)
    assert any(row["id"] == "CG-TEST-FIX" and row["autofix"] for row in rows)
    assert all(row["autofix"] for row in rows)
    r = CliRunner().invoke(cli, ["explain", "CG-TEST-FIX"])
    assert "Autofix:   safe" in r.output
    assert "enabled = True" in r.output


class TestCategoryDefaults:
    """Performance / quality rules never change a CLI exit code unless asked for."""

    SRC = "def f(items=[]):\n    for k in items:\n        pass\n"

    def test_cli_default_is_security_only(self, tmp_path: Path) -> None:
        _proj(tmp_path, self.SRC)
        r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
        assert r.exit_code == EXIT_OK

    def test_config_categories_enable_quality(self, tmp_path: Path) -> None:
        _proj(tmp_path, self.SRC)
        (tmp_path / "codeguard.toml").write_text(
            '[codeguard]\ncategories = ["security", "quality"]\n'
        )
        r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
        assert r.exit_code == EXIT_FINDINGS and "CG-QUAL-001" in r.output

    def test_explicit_rule_selection_runs_any_category(self, tmp_path: Path) -> None:
        _proj(tmp_path, self.SRC)
        r = CliRunner().invoke(cli, ["scan", str(tmp_path), "--rule", "CG-QUAL-001"])
        assert r.exit_code == EXIT_FINDINGS

    def test_unknown_category_in_config(self, tmp_path: Path) -> None:
        _proj(tmp_path, self.SRC)
        (tmp_path / "codeguard.toml").write_text('[codeguard]\ncategories = ["speed"]\n')
        r = CliRunner().invoke(cli, ["scan", str(tmp_path)])
        assert r.exit_code == 3


def test_analyzer_editor_defaults_include_all_categories(tmp_path: Path) -> None:
    from codeguard.analysis import EDITOR_DEFAULT_CATEGORIES, AnalysisOptions, ProjectAnalyzer

    (tmp_path / ".git").mkdir()
    src = "def f(items=[]):\n    pass\n"
    cli_view = ProjectAnalyzer(tmp_path).scan_document(src, tmp_path / "m.py")
    editor = ProjectAnalyzer(
        tmp_path, AnalysisOptions(default_categories=EDITOR_DEFAULT_CATEGORIES)
    ).scan_document(src, tmp_path / "m.py")
    assert cli_view == []
    assert [f.rule_id for f in editor] == ["CG-QUAL-001"]
