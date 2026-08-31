# SPDX-License-Identifier: Apache-2.0
"""Tests for CG-SEC-004: Unsafe deserialization."""

from __future__ import annotations

from codeguard.engine.runner import AnalysisRunner
from tests.conftest import load_fixture

RULE_ID = "CG-SEC-004"
RUNNER = AnalysisRunner(rule_ids=[RULE_ID])


def active_findings(source: str) -> list:
    return [f for f in RUNNER.run(source, filename="test.py") if not f.suppressed]


class TestCGSEC004Vulnerable:
    def test_pickle_loads(self) -> None:
        src = "import pickle\nresult = pickle.loads(data)\n"
        assert len(active_findings(src)) >= 1

    def test_pickle_load(self) -> None:
        src = "import pickle\nresult = pickle.load(f)\n"
        assert len(active_findings(src)) >= 1

    def test_marshal_loads(self) -> None:
        src = "import marshal\nresult = marshal.loads(data)\n"
        assert len(active_findings(src)) >= 1

    def test_yaml_load_no_loader(self) -> None:
        src = "import yaml\nresult = yaml.load(data)\n"
        assert len(active_findings(src)) >= 1

    def test_yaml_load_full_loader(self) -> None:
        # FullLoader is not safe for untrusted input
        src = "import yaml\nresult = yaml.load(data, Loader=yaml.FullLoader)\n"
        assert len(active_findings(src)) >= 1

    def test_from_import_loads(self) -> None:
        # Direct function import bypassed detection before (issue #4)
        src = "from pickle import loads\nresult = loads(data)\n"
        assert len(active_findings(src)) >= 1

    def test_from_import_marshal_load(self) -> None:
        src = "from marshal import load\nresult = load(fp)\n"
        assert len(active_findings(src)) >= 1

    def test_module_alias(self) -> None:
        src = "import pickle as p\nresult = p.loads(data)\n"
        assert len(active_findings(src)) >= 1

    def test_from_import_yaml_load(self) -> None:
        src = "from yaml import load\nresult = load(data)\n"
        assert len(active_findings(src)) >= 1

    def test_vulnerable_fixture(self) -> None:
        src = load_fixture("security", "cg_sec_004", "vulnerable")
        findings = active_findings(src)
        assert len(findings) >= 1, "Vulnerable fixture produced no findings"
        assert all(f.rule_id == RULE_ID for f in findings)


class TestCGSEC004Safe:
    def test_yaml_load_safe_loader_keyword(self) -> None:
        src = "import yaml\nresult = yaml.load(data, Loader=yaml.SafeLoader)\n"
        assert active_findings(src) == []

    def test_yaml_load_safe_loader_positional(self) -> None:
        src = "import yaml\nresult = yaml.load(data, yaml.SafeLoader)\n"
        assert active_findings(src) == []

    def test_yaml_safe_load(self) -> None:
        # yaml.safe_load is a different function — not detected as yaml.load
        src = "import yaml\nresult = yaml.safe_load(data)\n"
        assert active_findings(src) == []

    def test_json_loads(self) -> None:
        src = "import json\nresult = json.loads(data)\n"
        assert active_findings(src) == []

    def test_from_import_json_loads(self) -> None:
        src = "from json import loads\nresult = loads(data)\n"
        assert active_findings(src) == []

    def test_safe_fixture(self) -> None:
        src = load_fixture("security", "cg_sec_004", "safe")
        findings = active_findings(src)
        assert findings == [], f"Safe fixture produced unexpected findings: {findings}"
