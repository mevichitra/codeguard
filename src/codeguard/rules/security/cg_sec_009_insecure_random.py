# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-009 -- the ``random`` module used for a security value.

``random`` is a Mersenne Twister: its output can be predicted after observing
624 values.  Reported when the result is bound to, or computed in a function
named like, a token, password, nonce, OTP, or secret.  CWE-338.

Autofix (safe): ``random.choice`` -> ``secrets.choice``,
``random.getrandbits`` -> ``secrets.randbits``, ``random.randbytes`` ->
``secrets.token_bytes`` (identical signatures), adding ``import secrets`` when
needed.  Other functions get a suggestion only.
"""

from __future__ import annotations

import ast

from codeguard.engine.context import RuleContext
from codeguard.engine.finding import Category, Finding, Fix, Severity, TextEdit
from codeguard.engine.fixes import edit_for_ast_node, line_insert
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule
from codeguard.engine.text import split_lines
from codeguard.rules._pyimports import ImportMap, insertion_line
from codeguard.rules._pyparents import PyParents

_RANDOM_FUNCS = frozenset(
    {
        "random",
        "randint",
        "randrange",
        "choice",
        "choices",
        "getrandbits",
        "randbytes",
        "sample",
        "shuffle",
        "uniform",
    }
)
#: random.X -> secrets.Y with an identical call signature.
_SAFE_REPLACEMENTS = {
    "choice": "choice",
    "getrandbits": "randbits",
    "randbytes": "token_bytes",
}
_FIX = (
    "Use the secrets module: secrets.token_urlsafe(32) for tokens, "
    "secrets.choice(seq) to pick, secrets.randbelow(n) for integers."
)


class InsecureRandomRule(AstRule):
    id = "CG-SEC-009"
    title = "random module used for a security value"
    description = (
        "The random module is not cryptographically secure: an attacker who sees some "
        "outputs can predict the rest. The surrounding names suggest this value is a "
        "token, password, or secret."
    )
    severity = Severity.MEDIUM
    category = Category.SECURITY
    cwe = "CWE-338"
    owasp = "A02:2021 - Cryptographic Failures"
    autofix = True

    def analyze(self, ctx: RuleContext) -> list[Finding]:
        return self._check(ctx.python_ast, ctx.source, ctx.filename)

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        return self._check(tree, source, filename)

    def _check(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        imports = ImportMap.from_tree(tree)
        parents: PyParents | None = None
        findings: list[Finding] = []
        import_edit: TextEdit | None = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            module, name = imports.resolve_call(node.func)
            if module != "random" or name not in _RANDOM_FUNCS:
                continue
            parents = parents or PyParents.from_tree(tree)
            if not parents.in_security_context(node):
                continue
            fix = None
            replacement = _SAFE_REPLACEMENTS.get(name)
            if replacement is not None:
                secrets_name = imports.local_name_for("secrets")
                edits = [edit_for_ast_node(node.func, f"{secrets_name or 'secrets'}.{replacement}")]
                if secrets_name is None:
                    if import_edit is None and isinstance(tree, ast.Module):
                        import_edit = _import_secrets(tree, source)
                    if import_edit is not None:
                        edits.append(import_edit)
                fix = Fix(f"Use secrets.{replacement}()", tuple(edits))
            findings.append(
                self._make_finding(
                    node=node,
                    filename=filename,
                    description=(
                        f"random.{name}() produces what looks like a security value. The "
                        "random module is not cryptographically secure: an attacker who sees "
                        "some outputs can predict the rest."
                    ),
                    fix_suggestion=_FIX,
                    confidence=0.8,
                    fix=fix,
                )
            )
        return findings


def _import_secrets(tree: ast.Module, source: str) -> TextEdit:
    line = insertion_line(tree)
    text = "import secrets\n"
    if line > len(split_lines(source)) and source and not source.endswith("\n"):
        text = "\n" + text
    return line_insert(line, text)


REGISTRY.register(InsecureRandomRule())
