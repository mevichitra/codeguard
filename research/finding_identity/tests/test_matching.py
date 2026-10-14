from research.finding_identity.linemap import map_lines
from research.finding_identity.matching import Observation, evaluate, ground_truth
from research.finding_identity.schemes import ALL_SCHEMES, FileContext, keys_for, split_lines


def test_map_lines_insertion_and_edit() -> None:
    old = ["a = 1", "b = eval(x)", "c = 3"]
    new = ["import os", "a = 1", "b = eval(y)", "c = 3"]
    mapping = map_lines(old, new)
    assert mapping[1] == (2, "equal")
    assert mapping[2] == (3, "edited")
    assert mapping[3] == (4, "equal")


def test_map_lines_unrelated_replacement_is_unmapped() -> None:
    mapping = map_lines(["x = eval(data)"], ["print('completely different text here')"])
    assert 1 not in mapping


def _obs(text: str, line: int, rule: str = "R") -> Observation:
    ctx = FileContext.build("f.py", text, is_python=True)
    return Observation(rule, line, 5, keys_for(rule, line, ctx, ALL_SCHEMES))


def test_line_scheme_hides_a_new_finding_and_loses_the_old_one() -> None:
    old_text = "def f(x):\n    eval(x)\n"
    # Two lines inserted above; a *different* new finding lands on the old line 2.
    new_text = "def f(x):\n    eval(y)\n    pass\n    eval(x)\n"
    old = [_obs(old_text, 2)]
    new = [_obs(new_text, 2), _obs(new_text, 4)]
    line_map = map_lines(split_lines(old_text), split_lines(new_text))
    truth = ground_truth(old, new, line_map)
    assert truth == {1: (0, "equal")}  # eval(x) moved from line 2 to line 4

    result = evaluate(old, new, line_map, ["line", "codeguard"])
    assert result.gt["known"] == 1 and result.gt["introduced"] == 1
    assert result.by_scheme["line"]["false_known"] == 1  # eval(y) hidden
    assert result.by_scheme["line"]["false_new"] == 1  # eval(x) reported as new
    assert result.by_scheme["codeguard"]["known_ok"] == 1
    assert result.by_scheme["codeguard"]["new_ok"] == 1
