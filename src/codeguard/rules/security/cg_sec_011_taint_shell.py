# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-011 -- untrusted input reaches a shell command (taint).

``os.system`` / ``os.popen`` / ``subprocess.*(shell=True)`` / ``getoutput``
whose command carries untrusted data.  Replaces CG-SEC-005 on the same line.
CWE-78.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Severity
from codeguard.engine.registry import REGISTRY
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pysinks import command_arg, shell_target

from ._taint import TaintRule


class TaintedShellRule(TaintRule):
    id = "CG-SEC-011"
    title = "Untrusted input reaches a shell command"
    description = (
        "Data from outside the program is part of a command run by the system shell. "
        "An attacker can append their own commands (command injection)."
    )
    severity = Severity.CRITICAL
    cwe = "CWE-78"
    owasp = "A03:2021 - Injection"
    supersedes = frozenset({"CG-SEC-005"})
    fix_text = (
        "Run the program with an argument list and shell=False: "
        "subprocess.run(['git', 'checkout', branch]). If a shell is unavoidable, "
        "quote every value with shlex.quote()."
    )

    def sink(self, call: ast.Call, imports: ImportMap) -> tuple[ast.expr, str] | None:
        target = shell_target(call, imports)
        arg = command_arg(call)
        if target is None or arg is None:
            return None
        return arg, f"{target[0]}.{target[1]}()"


REGISTRY.register(TaintedShellRule())
