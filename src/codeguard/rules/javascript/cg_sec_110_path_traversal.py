# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-110 -- file-system path built from request data (path traversal).

``fs.*`` / ``fs.promises.*`` file operations and Express ``res.sendFile`` /
``res.download`` whose path argument reads ``req.query`` / ``req.body`` /
``req.params``.  Not reported when the request value is wrapped in
``path.basename(...)``, or for ``sendFile(p, { root })`` (Express then rejects
``..``).  CWE-22.
"""

from __future__ import annotations

import re

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import TreeSitterRule
from codeguard.lang.base import Language
from codeguard.lang.node import SourceNode
from codeguard.rules._jsnodes import REQUEST_DATA, arguments, callee_text, calls

_JS_TS = frozenset({Language.JAVASCRIPT, Language.TYPESCRIPT})
_FS_CALL = re.compile(
    r"(?:^|\.)(?:fs|fsp|fsPromises|promises)\."
    r"(?:readFile|writeFile|appendFile|createReadStream|createWriteStream|unlink|rm|rmdir|"
    r"readdir|stat|lstat|access|open|existsSync|copyFile|rename)(?:Sync)?$"
)
_SEND = re.compile(r"\.(?:sendFile|download)$")
_FIX = (
    "Reduce the value to a file name with path.basename(), then resolve it and check it "
    "stays inside the base directory: if (!full.startsWith(base + path.sep)) reject."
)


class PathTraversalJsRule(TreeSitterRule):
    id = "CG-SEC-110"
    title = "File path built from request data"
    description = (
        "A file path is built from request data. Sequences like '../' let an attacker "
        "read or overwrite files outside the intended directory (path traversal)."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    languages = _JS_TS
    cwe = "CWE-22"
    owasp = "A01:2021 - Broken Access Control"

    def check_tree(self, root: SourceNode, ctx: RuleContext) -> list[Finding]:
        findings: list[Finding] = []
        for call in calls(root):
            callee = callee_text(call)
            is_send = bool(_SEND.search(callee))
            if not (is_send or _FS_CALL.search(callee)):
                continue
            args = arguments(call)
            if not args:
                continue
            path_text = args[0].text()
            if not REQUEST_DATA.search(path_text) or "basename(" in path_text:
                continue
            if is_send and any(_has_root_option(a) for a in args[1:]):
                continue
            findings.append(
                self._make_finding(node=call, ctx=ctx, fix_suggestion=_FIX, confidence=0.8)
            )
        return findings


def _has_root_option(node: SourceNode) -> bool:
    return node.kind == "object" and re.search(r"\broot\s*:", node.text()) is not None


REGISTRY.register(PathTraversalJsRule())
