# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-010 -- untrusted input reaches a SQL query (taint).

Follows request data and process input through assignments, string building,
and string methods to ``cursor.execute()`` / ``executemany()`` /
``executescript()``.  Replaces CG-SEC-001 on the same line, adding the
source-to-sink path.  CWE-89.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Severity
from codeguard.engine.registry import REGISTRY
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pysinks import is_sql_execute

from ._taint import TaintRule, call_label


class TaintedSqlRule(TaintRule):
    id = "CG-SEC-010"
    title = "Untrusted input reaches a SQL query"
    description = (
        "Data from outside the program is used to build a SQL statement. An attacker "
        "can change the query's meaning (SQL injection)."
    )
    severity = Severity.HIGH
    cwe = "CWE-89"
    owasp = "A03:2021 - Injection"
    supersedes = frozenset({"CG-SEC-001"})
    fix_text = (
        "Pass values as query parameters instead of building the SQL string: "
        'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
    )

    def sink(self, call: ast.Call, imports: ImportMap) -> tuple[ast.expr, str] | None:
        if is_sql_execute(call) and call.args:
            return call.args[0], call_label(call)
        return None


REGISTRY.register(TaintedSqlRule())
