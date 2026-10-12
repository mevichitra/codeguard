# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-012 -- untrusted input reaches eval / exec / compile (taint).

Replaces CG-SEC-003 on the same line.  CWE-95.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Severity
from codeguard.engine.registry import REGISTRY
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pysinks import eval_like_name

from ._taint import TaintRule


class TaintedEvalRule(TaintRule):
    id = "CG-SEC-012"
    title = "Untrusted input reaches eval() / exec()"
    description = (
        "Data from outside the program is executed as Python code. An attacker can "
        "run arbitrary code with the application's privileges."
    )
    severity = Severity.CRITICAL
    cwe = "CWE-95"
    owasp = "A03:2021 - Injection"
    supersedes = frozenset({"CG-SEC-003"})
    fix_text = (
        "Never execute input as code. Parse data with json.loads() or "
        "ast.literal_eval(), and dispatch with a dict of allowed functions."
    )

    def sink(self, call: ast.Call, imports: ImportMap) -> tuple[ast.expr, str] | None:
        name = eval_like_name(call)
        if name is None or not call.args:
            return None
        return call.args[0], f"{name}()"


REGISTRY.register(TaintedEvalRule())
