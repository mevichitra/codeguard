# SPDX-License-Identifier: Apache-2.0
"""Tests for the output formatters."""

from __future__ import annotations

import json

from codeguard.cli.formatters import (
    format_human,
    format_json,
    format_json_legacy,
    format_sarif,
)
from codeguard.engine.finding import Category, Finding, Location, Severity


def _finding(**kw: object) -> Finding:
    defaults = dict(
        rule_id="CG-SEC-001",
        title="SQL query built with string formatting",
        description="dynamic SQL",
        severity=Severity.HIGH,
        category=Category.SECURITY,
        location=Location(file="app.py", line=12, col=5, end_line=12, end_col=40),
        cwe="CWE-89",
        owasp="A03:2021 - Injection",
        fix_suggestion="Use parameterized queries.",
        fingerprint="deadbeefdeadbeef",
    )
    defaults.update(kw)
    return Finding(**defaults)  # type: ignore[arg-type]


class TestJsonEnvelope:
    def test_shape(self) -> None:
        out = json.loads(format_json([_finding()], tool_version="2.0.0"))
        assert out["schema_version"] == "1"
        assert out["tool"] == {"name": "CodeGuard", "version": "2.0.0"}
        assert [r["id"] for r in out["rules"]] == ["CG-SEC-001"]
        assert out["rules"][0]["help_uri"].endswith("/rules/cg-sec-001/")
        assert out["results"][0]["fingerprint"] == "deadbeefdeadbeef"
        assert out["results"][0]["location"]["col"] == 5
        assert out["summary"] == {"findings": 1, "by_severity": {"high": 1}, "suppressed": 0}

    def test_suppressed_excluded_by_default(self) -> None:
        out = json.loads(format_json([_finding(suppressed=True)]))
        assert out["results"] == []
        assert out["summary"]["suppressed"] == 1

    def test_suppressed_included_on_request(self) -> None:
        out = json.loads(format_json([_finding(suppressed=True)], show_suppressed=True))
        assert len(out["results"]) == 1


class TestJsonLegacy:
    def test_is_bare_array(self) -> None:
        out = json.loads(format_json_legacy([_finding()]))
        assert isinstance(out, list)
        assert out[0]["rule_id"] == "CG-SEC-001"


class TestSarif:
    def test_structure(self) -> None:
        out = json.loads(format_sarif([_finding()], tool_version="2.0.0"))
        assert out["version"] == "2.1.0"
        driver = out["runs"][0]["tool"]["driver"]
        assert driver["informationUri"] == "https://github.com/mevichitra/codeguard"
        rule = driver["rules"][0]
        assert rule["helpUri"].endswith("/rules/cg-sec-001/")
        assert rule["properties"]["security-severity"] == "8.0"
        assert "external/cwe/cwe-89" in rule["properties"]["tags"]

        result = out["runs"][0]["results"][0]
        assert result["partialFingerprints"] == {"codeguard/v1": "deadbeefdeadbeef"}
        assert result["locations"][0]["physicalLocation"]["region"] == {
            "startLine": 12,
            "startColumn": 5,
            "endLine": 12,
            "endColumn": 40,
        }

    def test_suppressed_gets_suppressions_entry(self) -> None:
        out = json.loads(format_sarif([_finding(suppressed=True)]))
        assert out["runs"][0]["results"][0]["suppressions"][0]["kind"] == "inSource"


class TestHuman:
    def test_no_findings(self) -> None:
        assert "No findings" in format_human([])

    def test_lists_finding_and_summary(self) -> None:
        text = format_human([_finding()])
        assert "app.py:12:5" in text
        assert "[CG-SEC-001] HIGH" in text
        assert "1 finding(s)" in text
