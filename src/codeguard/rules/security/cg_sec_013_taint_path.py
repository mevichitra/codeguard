# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-013 -- request data used as a file path (path traversal, taint).

``open()``, ``os.remove()``, ``shutil.*``, ``pathlib.Path()``,
``flask.send_file()`` with a path built from
request data.  Only web sources count: a CLI opening the file its user named
is expected behaviour.  CWE-22.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Severity
from codeguard.engine.registry import REGISTRY
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pysinks import path_call_arg

from ._taint import TaintRule, call_label


class TaintedPathRule(TaintRule):
    id = "CG-SEC-013"
    title = "Request data used as a file path"
    description = (
        "A file path is built from request data. Sequences like '../' let an attacker "
        "read or overwrite files outside the intended directory (path traversal)."
    )
    severity = Severity.HIGH
    cwe = "CWE-22"
    owasp = "A01:2021 - Broken Access Control"
    source_kinds = frozenset({"web"})
    fix_text = (
        "Reduce the input to a bare file name with werkzeug.utils.secure_filename() or "
        "os.path.basename(), or resolve the path and check it stays inside the base "
        "directory: Path(base, name).resolve().is_relative_to(base)."
    )

    def sink(self, call: ast.Call, imports: ImportMap) -> tuple[ast.expr, str] | None:
        arg = path_call_arg(call, imports)
        return (arg, call_label(call)) if arg is not None else None


REGISTRY.register(TaintedPathRule())
