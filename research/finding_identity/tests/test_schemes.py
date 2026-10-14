from codeguard.engine.runner import AnalysisRunner
from codeguard.lang.base import Language
from research.finding_identity.schemes import (
    ALL_SCHEMES,
    FileContext,
    github_line_hashes,
    keys_for,
)

# Expected values were produced by running GitHub's own fingerprints.ts (codeql-action,
# with the `long` package) on the same inputs.
GITHUB_A = "import os\n\ndef f(x):\n\treturn eval(x)   # bad\n\nx = 1\nx = 1\nx = 1\n"
GITHUB_A_EXPECTED = {
    1: "420aefba3f9eb175:1",
    2: "e65a2d6470d3f9a6:1",
    3: "52e8697e4f828294:1",
    4: "2abbbe6646aa285e:1",
    5: "b792415f5b7fbcd:1",
    6: "b06211268476d237:1",
    7: "87c133c3324ef59b:1",
    8: "8e00d41f0ebba6bf:1",
    9: "c129715d7a2bc9a3:1",
}
GITHUB_B = "line one\r\nline two\r\n\r\n  indented\rcr-only\n"
GITHUB_B_EXPECTED = {
    1: "4ec050cce04de77c:1",
    2: "b58a469adea14580:1",
    3: "70d68996d679060:1",
    4: "ccff826d0d74b76:1",
    5: "e0be3c354f7b73a5:1",
    6: "c129715d7a2bc9a3:1",
}


def test_github_hash_matches_reference() -> None:
    assert github_line_hashes(GITHUB_A) == GITHUB_A_EXPECTED
    assert github_line_hashes(GITHUB_B) == GITHUB_B_EXPECTED


def test_github_hash_counts_duplicates() -> None:
    # Short identical lines at the end of a file hash identically and get :1, :2, ...
    hashes = github_line_hashes("a\n" * 120)
    assert hashes[1].endswith(":1")
    assert len({h.split(":")[0] for h in list(hashes.values())[:20]}) == 1
    assert hashes[2].endswith(":2")


SOURCE = "def handler(expr):\n    result = eval(expr)\n    return result\n"


def test_codeguard_key_equals_runner_fingerprint() -> None:
    import codeguard.rules  # noqa: F401

    findings = AnalysisRunner(rule_ids=["CG-SEC-003"]).run(
        SOURCE, filename="app/views.py", language=Language.PYTHON
    )
    assert len(findings) == 1
    f = findings[0]
    ctx = FileContext.build("app/views.py", SOURCE, is_python=True)
    keys = keys_for(f.rule_id, f.location.line, ctx, ALL_SCHEMES)
    assert keys["codeguard"] == f.fingerprint
    # With no literals on the line, masking changes nothing: the two keys coincide.
    assert keys["cg_no_mask"] == keys["codeguard"]
    others = [keys[s] for s in ALL_SCHEMES if s != "cg_no_mask"]
    assert len(set(others)) == len(others)


def test_codeguard_key_ignores_literals_and_spacing() -> None:
    a = FileContext.build("m.py", "def f():\n    q = run('a', 1)\n", is_python=True)
    b = FileContext.build("m.py", 'def f():\n    q =  run("b", 2)  # x\n', is_python=True)
    ka = keys_for("R", 2, a, ALL_SCHEMES)
    kb = keys_for("R", 2, b, ALL_SCHEMES)
    assert ka["codeguard"] == kb["codeguard"]
    assert ka["cg_no_scope"] == kb["cg_no_scope"]
    assert ka["cg_no_mask"] != kb["cg_no_mask"]
    assert ka["line_text"] != kb["line_text"]
    assert ka["line"] == kb["line"]
