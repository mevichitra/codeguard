from research.finding_identity import linemap
from research.finding_identity.linemap import line_map, map_lines
from research.finding_identity.matching import Observation, score

FUNC_A = [
    "def load_user(request, user_id):",
    "    query = 'SELECT * FROM users WHERE id = ' + user_id",
    "    return db.execute(query)",
    "",
]
FUNC_B = [
    "def save_profile(request, profile):",
    "    profile.bio = request.POST['bio']",
    "    profile.save()",
    "",
]
FUNC_C = [
    "def delete_account(request):",
    "    request.user.delete()",
    "    return redirect('/')",
    "",
]


def _index(lines: list[str], text: str) -> int:
    return lines.index(text) + 1


def test_moved_function_is_relocated() -> None:
    old = ["import db", "", *FUNC_A, *FUNC_B, *FUNC_C]
    new = ["import db", "", *FUNC_B, *FUNC_C, *FUNC_A]
    mapping = map_lines(old, new)
    for text in FUNC_A[:3] + FUNC_B[:3] + FUNC_C[:3]:
        assert mapping[_index(old, text)][0] == _index(new, text)
    kinds = {mapping[_index(old, text)][1] for text in FUNC_A[:3]}
    assert kinds == {"relocated"}  # the diff keeps B and C, so A is the moved block
    # Without move detection the moved function's lines are lost.
    assert _index(old, FUNC_A[1]) not in map_lines(old, new, moves=False)


def test_swapped_functions_map_both_ways() -> None:
    old = [*FUNC_A, *FUNC_B]
    new = [*FUNC_B, *FUNC_A]
    mapping = map_lines(old, new)
    for text in FUNC_A[:3] + FUNC_B[:3]:
        assert mapping[_index(old, text)][0] == _index(new, text)


def test_moved_block_keeps_an_edited_line_inside_it() -> None:
    body = [
        "def report(request):",
        "    rows = fetch_rows(request.GET['from'], request.GET['to'])",
        "    total = sum(r.amount for r in rows)",
        "    log.info('report built with %d rows', len(rows))",
        "    return render(request, 'report.html', {'rows': rows, 'total': total})",
    ]
    edited = list(body)
    edited[2] = "    total = sum(r.amount for r in rows if r.valid)"
    old = [*body, "", *FUNC_B]
    new = [*FUNC_B, "", *edited]
    mapping = map_lines(old, new)
    assert mapping[3] == (_index(new, edited[2]), "edited")
    for k in (1, 2, 4, 5):
        assert mapping[k] == (_index(new, body[k - 1]), "relocated")


def test_reindented_block_counts_as_moved() -> None:
    old = [*FUNC_A[:3], "", "class Views:", "    pass"]
    new = ["class Views:", *("    " + ln for ln in FUNC_A[:3])]
    mapping = map_lines(old, new)
    assert mapping[2] == (3, "relocated")


def test_block_that_is_not_unique_is_not_mapped() -> None:
    old = [*FUNC_A, *FUNC_B, *FUNC_C]
    new = [*FUNC_B, *FUNC_C, *FUNC_A, "z = 3", *FUNC_A]
    mapping = map_lines(old, new)
    # The diff keeps B and C; the deleted function A reappears twice, so it is ambiguous.
    assert all(kind != "relocated" for _, kind in mapping.values())
    assert 2 not in mapping


def test_block_repeated_elsewhere_in_the_file_is_not_mapped() -> None:
    # Three copies of the same block; the diff keeps two, and the third moves. Among the
    # unmapped lines it looks unique, but in the file it could be any copy.
    block = ["    # placeholder credentials for the mock", "    password = 'MOCK_PASSWORD'"]
    old = ["def a():", *block, "def b():", *block, "def c():", *block, *FUNC_B]
    new = ["def a():", *block, "def b():", *block, *FUNC_B, "def c2():", *block]
    mapping = map_lines(old, new)
    assert all(kind != "relocated" for _, kind in mapping.values())


def test_short_moved_line_is_not_mapped() -> None:
    old = ["a = 1", "b = 2", "c = 3", "x = f()"]
    new = ["x = f()", "a = 1", "b = 2", "c = 3"]
    mapping = map_lines(old, new)
    # "x = f()" has 3 alphanumeric characters, below Git's 20; but the diff keeps a/b/c.
    assert mapping[1] == (2, "equal")
    assert 4 not in mapping


def test_large_rewritten_block_is_aligned_in_a_band() -> None:
    n = 250  # 250 x 250 lines is above FULL_ALIGN_CELLS
    old = [f"value_{k} = compute(alpha_{k}, beta_{k})" for k in range(n)]
    new = [f"value_{k} = compute(alpha_{k}, gamma_{k})" for k in range(n)]
    assert n * n > linemap.FULL_ALIGN_CELLS
    lm = line_map(old, new)
    assert lm.banded_old == frozenset(range(1, n + 1))
    assert lm.banded_new == frozenset(range(1, n + 1))
    assert all(lm.pairs[k] == (k, "edited") for k in range(1, n + 1))


def test_banded_alignment_agrees_with_the_full_one_near_the_diagonal() -> None:
    old = [f"item_{k} = load(source_{k})" for k in range(40)]
    new = [f"item_{k} = load(source_{k}, cache=True)" for k in range(40)]
    new.insert(10, "unrelated = 0")
    full = linemap._align_full(old, new)
    banded = linemap._align_banded(old, new)
    assert banded == full


def test_relocated_findings_are_counted_by_kind() -> None:
    old_lines = [*FUNC_A, *FUNC_B, *FUNC_C]
    new_lines = [*FUNC_B, *FUNC_C, *FUNC_A]
    old = [Observation("R", 2, 4, {"line": "2"})]
    new = [Observation("R", _index(new_lines, FUNC_A[1]), 4, {"line": "x"})]
    from research.finding_identity.matching import ground_truth

    truth = ground_truth(old, new, map_lines(old_lines, new_lines))
    assert truth == {0: (0, "relocated")}
    result = score(old, new, truth, ["line"])
    assert result.gt["known_relocated"] == 1
    assert result.by_scheme["line"]["false_new_relocated"] == 1
