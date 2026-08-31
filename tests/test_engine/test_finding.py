# SPDX-License-Identifier: Apache-2.0
"""Tests for the Finding model and core engine primitives."""

from __future__ import annotations

import pytest

from codeguard.engine.finding import Category, Finding, Location, Severity


class TestSeverityOrdering:
    def test_critical_gt_high(self) -> None:
        assert Severity.CRITICAL > Severity.HIGH

    def test_high_gt_medium(self) -> None:
        assert Severity.HIGH > Severity.MEDIUM

    def test_medium_gt_low(self) -> None:
        assert Severity.MEDIUM > Severity.LOW

    def test_low_gt_info(self) -> None:
        assert Severity.LOW > Severity.INFO

    def test_equal(self) -> None:
        assert Severity.HIGH == Severity.HIGH

    def test_sorted(self) -> None:
        severities = [Severity.INFO, Severity.CRITICAL, Severity.LOW, Severity.HIGH]
        expected = [Severity.CRITICAL, Severity.HIGH, Severity.LOW, Severity.INFO]
        assert sorted(severities, reverse=True) == expected


class TestLocation:
    def test_valid(self) -> None:
        loc = Location(file="foo.py", line=1, col=1)
        assert loc.file == "foo.py"
        assert loc.line == 1

    def test_line_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="line must be"):
            Location(file="x.py", line=0, col=1)

    def test_col_must_be_positive(self) -> None:
        # Columns are 1-indexed; 0 is invalid.
        with pytest.raises(ValueError, match="col must be"):
            Location(file="x.py", line=1, col=0)

    def test_optional_end_position(self) -> None:
        loc = Location(file="x.py", line=1, col=1, end_line=3, end_col=10)
        assert loc.end_line == 3
        assert loc.end_col == 10


class TestFinding:
    def _make(self, **kwargs: object) -> Finding:
        defaults = dict(
            rule_id="CG-SEC-001",
            title="Test",
            description="Test finding",
            severity=Severity.HIGH,
            category=Category.SECURITY,
            location=Location(file="test.py", line=1, col=1),
        )
        defaults.update(kwargs)
        return Finding(**defaults)  # type: ignore[arg-type]

    def test_basic(self) -> None:
        f = self._make()
        assert f.rule_id == "CG-SEC-001"
        assert f.severity == Severity.HIGH
        assert not f.suppressed

    def test_empty_rule_id_raises(self) -> None:
        with pytest.raises(ValueError, match="rule_id"):
            self._make(rule_id="")

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            self._make(confidence=1.1)
        with pytest.raises(ValueError, match="confidence"):
            self._make(confidence=-0.1)

    def test_as_suppressed(self) -> None:
        f = self._make()
        suppressed = f.as_suppressed()
        assert suppressed.suppressed is True
        assert f.suppressed is False  # original unchanged (frozen)

    def test_to_dict(self) -> None:
        f = self._make(cwe="CWE-89", owasp="A03:2021")
        d = f.to_dict()
        assert d["rule_id"] == "CG-SEC-001"
        assert d["severity"] == "high"
        assert d["category"] == "security"
        assert d["location"]["file"] == "test.py"
        assert d["cwe"] == "CWE-89"
        assert d["suppressed"] is False
        assert d["fingerprint"] == ""  # unset until the runner assigns it

    def test_with_fingerprint(self) -> None:
        f = self._make()
        fp = f.with_fingerprint("abc123")
        assert fp.fingerprint == "abc123"
        assert f.fingerprint == ""  # original unchanged (frozen)
