# SPDX-License-Identifier: Apache-2.0
"""Settings, diagnostics, code actions, and hovers built by codeguard.lsp.actions."""

from __future__ import annotations

from pathlib import Path

from codeguard.engine.finding import (
    Category,
    Finding,
    Fix,
    Location,
    RelatedLocation,
    Severity,
    TextEdit,
)
from codeguard.lsp import actions
from codeguard.lsp.actions import Settings
from codeguard.lsp.positions import LineIndex

WHOLE = {"start": {"line": 0, "character": 0}, "end": {"line": 99, "character": 0}}


def _finding(**kw: object) -> Finding:
    base: dict[str, object] = {
        "rule_id": "CG-PERF-004",
        "title": "Redundant .keys()",
        "description": "desc",
        "severity": Severity.INFO,
        "category": Category.PERFORMANCE,
        "location": Location("m.py", 2, 10, 2, 18),
        "fingerprint": "abc123",
    }
    base.update(kw)
    return Finding(**base)  # type: ignore[arg-type]


SOURCE = "import os\nfor k in d.keys():\n    pass\n"
KEYS_FIX = Fix("Remove .keys()", (TextEdit(2, 10, 2, 18, "d"),))


class TestSettings:
    def test_defaults(self) -> None:
        s = Settings()
        assert s.severity_map["high"] == 1 and s.severity_map["info"] == 4
        assert s.code_description == "help" and s.scan_on_startup

    def test_parse_all_keys(self) -> None:
        s = Settings.from_dict(
            {
                "severityMap": {"medium": "error", "low": 4, "info": "off", "bogus": "error"},
                "categories": {"quality": False, "performance": True, "nope": True},
                "rules": {"disable": ["CG-QUAL-104", 7]},
                "scanWorkspaceOnStartup": False,
                "codeDescription": "dashboard",
                "client": "zed",
            }
        )
        assert s.severity_map["medium"] == 1 and s.severity_map["low"] == 4
        assert s.severity_map["info"] == 0
        assert dict(s.category_overrides) == {"quality": False, "performance": True}
        assert s.disabled_rules == ("CG-QUAL-104",)
        assert not s.scan_on_startup and s.code_description == "dashboard" and s.client == "zed"

    def test_category_list_form_and_base_merge(self) -> None:
        base = Settings.from_dict({"severityMap": {"low": "error"}})
        s = Settings.from_dict({"categories": ["security"]}, base=base)
        assert dict(s.category_overrides) == {
            "performance": False,
            "quality": False,
            "security": True,
        }
        assert s.severity_map["low"] == 1  # kept from base

    def test_garbage_is_ignored(self) -> None:
        s = Settings.from_dict({"severityMap": {"high": True}, "codeDescription": "x"})
        assert s.severity_map["high"] == 1 and s.code_description == "help"
        assert Settings.from_dict(None) == Settings()


class TestDiagnostic:
    def test_data_carries_fix_as_lsp_edits(self) -> None:
        d = actions.finding_to_diagnostic(_finding(fix=KEYS_FIX), index=LineIndex(SOURCE))
        assert d["severity"] == 4
        assert d["data"]["hasFix"] is True
        assert d["data"]["fix"]["edits"][0] == {
            "range": {"start": {"line": 1, "character": 9}, "end": {"line": 1, "character": 17}},
            "newText": "d",
        }
        assert d["codeDescription"]["href"].endswith("/rules/CG-PERF-004/")

    def test_related_information(self) -> None:
        f = _finding(related=(RelatedLocation(Location("m.py", 1, 1), "Untrusted input: x"),))
        d = actions.finding_to_diagnostic(f, uri_for={"m.py": "file:///m.py"})
        assert d["relatedInformation"][0]["location"]["uri"] == "file:///m.py"
        assert d["relatedInformation"][0]["message"] == "Untrusted input: x"

    def test_severity_map_and_dashboard_mode(self) -> None:
        settings = Settings.from_dict(
            {"severityMap": {"info": "warning"}, "codeDescription": "dashboard"}
        )
        d = actions.finding_to_diagnostic(
            _finding(), settings=settings, dashboard_uri="file:///r.md"
        )
        assert d["severity"] == 2 and d["codeDescription"]["href"] == "file:///r.md"


class TestCodeActions:
    def _actions(
        self, findings: list[Finding], source: str = SOURCE, only: list[str] | None = None
    ):  # type: ignore[no-untyped-def]
        return actions.code_actions(
            "file:///m.py", Path("m.py"), findings, LineIndex(source), source, WHOLE, only
        )

    def test_quick_fix_suppressions_and_explain(self) -> None:
        result = self._actions([_finding(fix=KEYS_FIX)])
        titles = [a["title"] for a in result]
        assert titles[0] == "Fix: Remove .keys() (CG-PERF-004)"
        assert result[0]["isPreferred"] is True
        assert "Suppress CG-PERF-004 on this line" in titles
        assert "Suppress CG-PERF-004 in this file" in titles
        explain = next(a for a in result if a["title"].startswith("Explain"))
        assert explain["command"]["command"] == "codeguard.lsp.explain"
        fix_all = next(a for a in result if a["kind"] == "source.fixAll.codeguard")
        assert fix_all["edit"]["changes"]["file:///m.py"][0]["newText"] == "d"

    def test_suppress_line_appends_comment_at_line_end(self) -> None:
        line = next(a for a in self._actions([_finding()]) if "on this line" in a["title"])
        (edit,) = line["edit"]["changes"]["file:///m.py"]
        assert edit["range"]["start"] == {"line": 1, "character": len("for k in d.keys():")}
        assert edit["newText"].startswith("  # codeguard: ignore[CG-PERF-004] reason:")

    def test_suppress_line_extends_existing_comment(self) -> None:
        src = "x = 1\ny = d.keys()  # codeguard: ignore[CG-SEC-001] reason: r\n"
        line = next(a for a in self._actions([_finding()], src) if "on this line" in a["title"])
        (edit,) = line["edit"]["changes"]["file:///m.py"]
        assert edit["newText"] == ", CG-PERF-004"
        assert edit["range"]["start"]["character"] == src.splitlines()[1].index("]")

    def test_suppress_file_after_shebang_and_coding(self) -> None:
        src = "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\nfor k in d.keys(): pass\n"
        f = _finding(location=Location("m.py", 3, 10, 3, 18))
        action = next(a for a in self._actions([f], src) if "in this file" in a["title"])
        (edit,) = action["edit"]["changes"]["file:///m.py"]
        assert edit["range"]["start"] == {"line": 2, "character": 0}
        assert edit["newText"].startswith("# codeguard: ignore-file[CG-PERF-004]")

    def test_js_uses_slash_comment(self) -> None:
        result = actions.code_actions(
            "file:///a.js", Path("a.js"), [_finding()], LineIndex(SOURCE), SOURCE, WHOLE, None
        )
        line = next(a for a in result if "on this line" in a["title"])
        assert "// codeguard: ignore" in line["edit"]["changes"]["file:///a.js"][0]["newText"]

    def test_only_fix_all(self) -> None:
        result = self._actions([_finding(fix=KEYS_FIX)], only=["source.fixAll"])
        assert [a["kind"] for a in result] == ["source.fixAll.codeguard"]

    def test_suppressed_findings_and_out_of_range_ignored(self) -> None:
        assert self._actions([_finding().as_suppressed()]) == []
        far = {"start": {"line": 50, "character": 0}, "end": {"line": 50, "character": 1}}
        result = actions.code_actions(
            "file:///m.py", Path("m.py"), [_finding()], LineIndex(SOURCE), SOURCE, far, ["quickfix"]
        )
        assert result == []


def test_hover_markdown_includes_flow_fix_and_links() -> None:
    f = _finding(
        rule_id="CG-SEC-011",
        severity=Severity.CRITICAL,
        category=Category.SECURITY,
        cwe="CWE-78",
        owasp="A03:2021 - Injection",
        confidence=0.85,
        fix_suggestion="Use a list.",
        related=(RelatedLocation(Location("m.py", 1, 1), "Untrusted input: flask request.args"),),
        fix=KEYS_FIX,
    )
    md = actions.hover_markdown(f)
    assert "**CG-SEC-011" in md and "`CRITICAL`" in md and "confidence 85%" in md
    assert "[CWE-78](https://cwe.mitre.org/data/definitions/78.html)" in md
    assert "- line 1: `Untrusted input: flask request.args`" in md
    assert "Quick fix available" in md and "How to fix:** Use a list." in md
