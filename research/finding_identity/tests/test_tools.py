"""Fidelity of the real-tool schemes: SonarQube, Bandit and Semgrep.

The recorded fixtures come from running the original tools (see ``fidelity/``), so these
tests run without them. Tests marked ``live`` run Bandit or Semgrep when installed
(``pip install -r research/finding_identity/requirements.txt``) and skip otherwise.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

import pytest

from research.finding_identity.analyzers import (
    DEFAULT_SEMGREP_RULES,
    SEMGREP_SCAN_ARGS,
    semgrep_env,
    semgrep_formulas,
)
from research.finding_identity.fidelity import sonar_cases
from research.finding_identity.linemap import map_lines
from research.finding_identity.matching import Observation, evaluate
from research.finding_identity.scan import Scanner
from research.finding_identity.schemes import (
    ALL_SCHEMES,
    FileContext,
    FindingMeta,
    SemgrepMatch,
    keys_for,
    schemes_for,
    semgrep_formula_string,
    semgrep_match_based_ids,
    split_lines,
)
from research.finding_identity.trackers import bandit_baseline, sonar_line_hash

FIXTURES = Path(__file__).parent / "fixtures"


needs_bandit = pytest.mark.skipif(find_spec("bandit") is None, reason="bandit not installed")
needs_semgrep = pytest.mark.skipif(shutil.which("semgrep") is None, reason="semgrep not installed")


# ---------------------------------------------------------------------------- SonarQube


def test_sonar_port_matches_sonarqube_tracker() -> None:
    fixture = json.loads((FIXTURES / "sonar_tracker.json").read_text())
    cases = sonar_cases.make_cases(fixture["seed"], fixture["count"])
    assert sonar_cases.cases_digest(cases) == fixture["cases_sha256"], "generator changed"
    for n, (case, want) in enumerate(zip(cases, fixture["expected"], strict=True)):
        assert sonar_cases.port_matches(case) == want, f"case {n}"
    order_cases = sonar_cases.make_order_cases(fixture["seed"], fixture["order_count"])
    for n, (oc, want) in enumerate(zip(order_cases, fixture["orders"], strict=True)):
        assert sonar_cases.port_order(oc) == want, f"order case {n}"


def test_sonar_line_hash_ignores_spaces_and_tabs() -> None:
    assert sonar_line_hash(" \t ") == ""
    assert sonar_line_hash("a b\tc") == hashlib.md5(b"abc", usedforsecurity=False).hexdigest()


def _sonar_obs(text: str, line: int, message: str, rule: str = "R") -> Observation:
    lines = split_lines(text)
    ctx = FileContext.build("f.py", text, is_python=True)
    keys = keys_for(rule, line, ctx, ["sonar", "line"])
    return Observation(rule, line, 1, keys, message=message, lines=lines)


def test_sonar_tracks_moved_code_and_changed_messages() -> None:
    old_text = "def f(x):\n    eval(x)\n    eval(y)\n"
    new_text = "import os\n\ndef f(x):\n    eval(x)\n    eval(y)\n    eval(z)\n"
    old = [_sonar_obs(old_text, 2, "eval of x"), _sonar_obs(old_text, 3, "eval of y")]
    new = [
        _sonar_obs(new_text, 4, "eval of x"),
        _sonar_obs(new_text, 5, "eval: y"),  # same line hash, new message
        _sonar_obs(new_text, 6, "eval of z"),  # new
    ]
    line_map = map_lines(split_lines(old_text), split_lines(new_text))
    result = evaluate(old, new, line_map, ["sonar", "line"])
    assert result.by_scheme["sonar"]["known_ok"] == 2
    assert result.by_scheme["sonar"]["new_ok"] == 1
    assert result.by_scheme["line"]["known_ok"] == 0


# ---------------------------------------------------------------------------- Semgrep


def test_semgrep_port_matches_emitted_ids() -> None:
    fixture = json.loads((FIXTURES / "semgrep_match_based_id.json").read_text())
    assert fixture["semgrep"] == "1.180.0"
    formulas = semgrep_formulas(fixture["rules"])
    checked = reused = 0
    for source in fixture["sources"]:
        for results in source["files"]:
            matches = [
                SemgrepMatch(r["rule"], r["path"], formulas[r["rule"]], r["metavars"])
                for r in results
            ]
            assert semgrep_match_based_ids(matches) == [r["id"] for r in results]
            checked += len(results)
            reused += sum(not r["id"].endswith("_0") for r in results)
    assert checked > 300 and reused > 100


def test_semgrep_formula_string() -> None:
    assert semgrep_formula_string({"pattern": "eval($X)"}) == "eval($X)"
    either = {"pattern-either": [{"pattern": "os.system(...)"}, {"pattern": "exec(...)"}]}
    assert semgrep_formula_string(either) == "exec(...) os.system(...)"
    nested = {"patterns": [{"pattern": "$F(...)"}, {"metavariable-regex": {"regex": "^e"}}]}
    assert semgrep_formula_string(nested) == "$F(...) ^e"
    # A non-string value anywhere voids the whole formula, as in Semgrep.
    assert semgrep_formula_string({"patterns": [{"focus-metavariable": True}]}) == ""


def test_semgrep_ids_count_matches_of_equal_keys() -> None:
    m = SemgrepMatch("r", "src/a.py", "eval($X)", {"$X": "a"})
    other = SemgrepMatch("r", "src/a.py", "eval($X)", {"$X": "b"})
    ids = semgrep_match_based_ids([m, other, m])
    assert [i[-2:] for i in ids] == ["_0", "_0", "_1"]
    assert ids[0][:-2] == ids[2][:-2] != ids[1][:-2]


SEMGREP_SAMPLE = """import os
import subprocess


def handler(cmd, user, cur):
    eval(cmd)
    eval(cmd)
    os.system(cmd)
    os.popen(user)
    subprocess.call(cmd, shell=True)
    cur.execute("SELECT * FROM t WHERE u = '%s'" % user)
    cur.execute(f"SELECT {user}")
"""


@needs_semgrep
def test_semgrep_live_json_and_sarif_ids(tmp_path: Path) -> None:
    scanner = Scanner([], schemes_for("semgrep"), analyzer="semgrep")
    result = scanner.scan("blob", "pkg/app.py", SEMGREP_SAMPLE.encode())
    assert result is not None and len(result.observations) == 8
    described = scanner.describe()
    assert described["port_checked"] == 8 and described["port_mismatches"] == 0
    json_ids = [o.keys["semgrep"] for o in result.observations]
    assert len(set(json_ids)) == len(json_ids)

    # SARIF carries the same value as fingerprints["matchBasedId/v1"].
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "app.py").write_text(SEMGREP_SAMPLE)
    shutil.copy(DEFAULT_SEMGREP_RULES, tmp_path / "rules.yml")
    (tmp_path / ".semgrepignore").write_text("")
    home = tmp_path / "home"
    home.mkdir()
    out = subprocess.run(
        [
            "semgrep",
            *SEMGREP_SCAN_ARGS[:-2],
            "--quiet",
            "--config",
            "rules.yml",
            "--sarif",
            "pkg/app.py",
        ],
        cwd=tmp_path,
        env=semgrep_env(home),
        capture_output=True,
        text=True,
        check=True,
    )
    sarif = json.loads(out.stdout)["runs"][0]["results"]
    sarif_ids = sorted(r["fingerprints"]["matchBasedId/v1"] for r in sarif)
    assert sarif_ids == sorted(json_ids)


# ---------------------------------------------------------------------------- Bandit


def _bandit_obs(rule: str, line: int, message: str) -> Observation:
    ctx = FileContext.build("a.py", "", is_python=True)
    meta = FindingMeta(message=message, severity="HIGH", confidence="HIGH", cwe="78", test="t")
    return Observation(rule, line, 1, keys_for(rule, line, ctx, ["bandit"], meta=meta))


def test_bandit_baseline_is_membership_not_pairing() -> None:
    old = [_bandit_obs("B602", 3, "shell")]
    new = [_bandit_obs("B602", 9, "shell"), _bandit_obs("B602", 12, "shell")]
    # Both new issues equal the baseline issue, so Bandit reports neither as new.
    assert bandit_baseline(old, new) == {0: 0, 1: 0}
    assert bandit_baseline(old, [_bandit_obs("B602", 3, "other")]) == {}


BANDIT_OLD = """import subprocess
import pickle


def run(cmd, data):
    subprocess.call(cmd, shell=True)
    return pickle.loads(data)
"""
# Lines shift; a second identical shell call is added (hidden by the baseline); a new
# kind of issue appears; the shell=True call with a literal changes severity.
BANDIT_NEW = """import subprocess
import pickle
import hashlib

TOKEN = "x"


def run(cmd, data):
    subprocess.call(cmd, shell=True)
    subprocess.call(cmd, shell=True)
    subprocess.call("ls", shell=True)
    hashlib.md5(data)
    return pickle.loads(data)
"""


def _bandit_cli(cwd: Path, *args: str) -> list[dict[str, object]]:
    """Run the Bandit command line on pkg/app.py; the JSON report's results."""
    proc = subprocess.run(
        [sys.executable, "-m", "bandit", "-q", "-f", "json", "-o", "out.json", *args, "pkg/app.py"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1), proc.stderr
    results: list[dict[str, object]] = json.loads((cwd / "out.json").read_text())["results"]
    return results


@needs_bandit
def test_bandit_live_baseline_matches_port(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    target = tmp_path / "pkg" / "app.py"
    target.write_text(BANDIT_OLD)
    _bandit_cli(tmp_path)
    (tmp_path / "out.json").rename(tmp_path / "baseline.json")
    target.write_text(BANDIT_NEW)
    new_cli = _bandit_cli(tmp_path)
    reported_new = _bandit_cli(tmp_path, "-b", "baseline.json")

    scanner = Scanner([], ALL_SCHEMES, analyzer="bandit")
    old_res = scanner.scan("old", "pkg/app.py", BANDIT_OLD.encode())
    new_res = scanner.scan("new", "pkg/app.py", BANDIT_NEW.encode())
    assert old_res is not None and new_res is not None

    # The in-process analyzer reports what the command line reports.
    assert [(o.rule, o.line, o.col - 1, o.message) for o in new_res.observations] == [
        (r["test_id"], r["line_number"], r["col_offset"], r["issue_text"]) for r in new_cli
    ]
    # The port flags as new exactly the issues `bandit -b` reports.
    pairs = bandit_baseline(old_res.observations, new_res.observations)
    port_new = sorted(
        (o.rule, o.line) for j, o in enumerate(new_res.observations) if j not in pairs
    )
    assert port_new == sorted((r["test_id"], r["line_number"]) for r in reported_new)
    assert ("B602", 9) not in port_new  # a duplicate of a baselined issue stays hidden
    assert len(port_new) >= 2


@needs_bandit
def test_scanner_skips_files_bandit_does_not_analyse() -> None:
    scanner = Scanner([], ALL_SCHEMES, analyzer="bandit")
    result = scanner.scan("js", "web/app.js", b"eval(x);\n")
    assert result is not None and result.observations == []
    assert scanner.versions_scanned == 0 and scanner.parse_failures == 0
