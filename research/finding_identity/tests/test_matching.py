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


# ---------------------------------------------------------------------------
# SonarQube file move detection (branch analyses)
# ---------------------------------------------------------------------------


def _levenshtein(a: list[str], b: list[str]) -> int:
    # The textbook algorithm, without the common prefix/suffix shortcut.
    cost = list(range(len(a) + 1))
    for j in range(1, len(b) + 1):
        new = [j] + [0] * len(a)
        for i in range(1, len(a) + 1):
            new[i] = min(cost[i] + 1, new[i - 1] + 1, cost[i - 1] + (a[i - 1] != b[j - 1]))
        cost = new
    return cost[len(a)]


def test_sonar_similarity_matches_the_textbook_edit_distance() -> None:
    import random

    from research.finding_identity.trackers import sonar_similarity

    assert sonar_similarity([], []) == 0
    assert sonar_similarity(["a"], []) == 0
    assert sonar_similarity(["a", "b"], ["a", "b"]) == 100
    assert sonar_similarity(["a", "b", "c", "d"], ["a", "x", "c", "d"]) == 75  # 1 - 1/4
    assert sonar_similarity(["a", "b", "c"], ["a", "c"]) == 66  # 1 - 1/3, truncated
    rng = random.Random(7)  # noqa: S311  (test data, not security)
    for _ in range(300):
        a = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
        b = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
        if a or b:
            expected = int(100 * (1.0 - _levenshtein(a, b) / max(len(a), len(b))))
            assert sonar_similarity(a, b) == expected, (a, b)


def test_sonar_file_moved_score_and_line_count_bounds() -> None:
    from research.finding_identity.trackers import sonar_file_moved

    old = [f"line_{i} = {i}" for i in range(100)]
    assert sonar_file_moved(old, old)
    assert sonar_file_moved(old, [*old, "", "x = 1"])
    # Score 1 - 15/100 = 85 is enough, but 84 lines is at the lower bound floor(100 * 0.84).
    assert sonar_file_moved(old, old[:85])
    assert not sonar_file_moved(old, old[:84])
    # 15 added lines: 1 - 15/115 = 86. 18 added lines: within the upper bound
    # ceil(100 * 1.18) = 119 (the product is 118.00000000000001) but 1 - 18/118 = 84.
    assert sonar_file_moved(old, old + [f"y{i}" for i in range(15)])
    assert not sonar_file_moved(old, old + [f"y{i}" for i in range(18)])
    # Spaces and tabs do not count: line hashes drop them.
    assert sonar_file_moved(old, [line.replace(" ", "\t") for line in old])
    # Half the lines rewritten.
    assert not sonar_file_moved(old, old[:50] + [f"z{i}" for i in range(50)])


def test_sonar_branch_pairs_nothing_across_a_rename_it_does_not_detect() -> None:
    from research.finding_identity.matching import scheme_pairs

    old_text = "def f(x):\n    eval(x)\n" + "".join(f"a{i} = {i}\n" for i in range(20))
    new_text = "def f(x):\n    eval(x)\n" + "".join(f"b{i} = {i}\n" for i in range(20))

    def obs(text: str) -> Observation:
        ctx = FileContext.build("f.py", text, is_python=True)
        keys = keys_for("R", 2, ctx, ALL_SCHEMES)
        return Observation("R", 2, 5, keys, lines=split_lines(text))

    old, new = [obs(old_text)], [obs(new_text)]
    # The flagged line is unchanged, so both modes keep the finding at the same path...
    assert scheme_pairs(old, new, "sonar") == {0: 0}
    assert scheme_pairs(old, new, "sonar_branch") == {0: 0}
    # ...but across a rename, a branch analysis sees a new file (2 of 23 lines equal).
    assert scheme_pairs(old, new, "sonar", renamed=True) == {0: 0}
    assert scheme_pairs(old, new, "sonar_branch", renamed=True) == {}
    # A rename with the same content is a detected move.
    assert scheme_pairs(old, [obs(old_text)], "sonar_branch", renamed=True) == {0: 0}
