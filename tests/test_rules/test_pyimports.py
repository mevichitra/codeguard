# SPDX-License-Identifier: Apache-2.0
"""Tests for the import-alias resolver shared by the security rules."""

from __future__ import annotations

import ast

from codeguard.rules._pyimports import ImportMap


def _resolve(src: str) -> tuple[str | None, str | None]:
    tree = ast.parse(src)
    imports = ImportMap.from_tree(tree)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    return imports.resolve_call(call.func)


def test_plain_module_attr() -> None:
    assert _resolve("import os\nos.system(x)\n") == ("os", "system")


def test_module_alias() -> None:
    assert _resolve("import subprocess as sp\nsp.run(x)\n") == ("subprocess", "run")


def test_from_import() -> None:
    assert _resolve("from pickle import loads\nloads(b)\n") == ("pickle", "loads")


def test_from_import_alias() -> None:
    assert _resolve("from os import system as sh\nsh(x)\n") == ("os", "system")


def test_from_import_submodule() -> None:
    assert _resolve("from os.path import join\njoin(a, b)\n") == ("os.path", "join")


def test_unknown_bare_name() -> None:
    assert _resolve("def run(x): ...\nrun(x)\n") == (None, "run")


def test_non_name_receiver() -> None:
    assert _resolve("get_conn().execute(q)\n") == (None, None)


def test_relative_import_not_tracked() -> None:
    # `from . import x` has no canonical module: the name is not registered,
    # so `helpers.run(...)` just resolves receiver-as-module. Must not crash,
    # and must not resolve to a stdlib target.
    assert _resolve("from . import helpers\nhelpers.run(x)\n") == ("helpers", "run")
