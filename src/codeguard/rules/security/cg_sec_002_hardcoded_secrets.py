# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-002 — Hardcoded secret in variable assignment.

Detects string literals assigned to variables whose names suggest they hold
a secret: password, api_key, token, secret, etc.

Why this matters
----------------
Hardcoded credentials are one of the most common security mistakes in
AI-generated code (CWE-798, OWASP A07:2021).  LLMs routinely generate
example code with placeholder strings like "admin123" or "my_secret_key"
that end up committed to version control.

This rule has intentionally conservative matching: it only fires when the
*variable name* matches known secret-naming patterns AND the value is a
non-empty string literal (not an env-var lookup or config read).

Confidence is set to 0.9 because the rule can fire on intentional test
fixtures using placeholder values.  Use ``# codeguard: ignore[CG-SEC-002]``
in tests if needed, or use a non-secret-looking variable name.
"""

from __future__ import annotations

import ast
import re

from codeguard.engine.finding import Category, Finding, Severity
from codeguard.engine.registry import REGISTRY
from codeguard.engine.rule import AstRule

# Variable names that suggest secret storage.
# Deliberately conservative — only clear semantic markers.
_SECRET_NAME_RE = re.compile(
    r"(?i)(\b|_)("
    r"password|passwd|pwd|passphrase"
    r"|secret|api_?key|private_?key|access_?key|secret_?key"
    r"|auth_?token|bearer_?token|refresh_?token|session_?token|csrf_?token"
    r"|client_?secret|app_?secret"
    r"|db_?pass(?:word)?|database_?password"
    r"|smtp_?pass(?:word)?"
    r"|aws_?secret|stripe_?(?:secret_?)?key|twilio_?token|github_?token"
    r")(\b|_)"
)

_FIX = (
    "Load secrets from environment variables or a secrets manager: "
    "os.environ['MY_SECRET'] or a library like python-decouple / hvac."
)

# Minimum length to avoid flagging empty-string defaults
_MIN_SECRET_LEN = 1


class HardcodedSecretsRule(AstRule):
    """Detect string literals assigned to secret-named variables."""

    id = "CG-SEC-002"
    title = "Hardcoded secret"
    description = (
        "A string literal is assigned to a variable whose name indicates it holds "
        "a secret (password, API key, token, etc.). Hardcoded credentials get "
        "committed to version control and are trivially discoverable."
    )
    severity = Severity.HIGH
    category = Category.SECURITY
    cwe = "CWE-798"
    owasp = "A07:2021 - Identification and Authentication Failures"

    def check_ast(self, tree: ast.AST, source: str, filename: str) -> list[Finding]:
        """Scan assignments for secret-named variables with string literals."""
        findings: list[Finding] = []

        for node in ast.walk(tree):
            # Simple assignment:  password = "hunter2"
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    # Handle tuple/list unpacking: user, password = "admin", "hunter2"
                    if isinstance(target, (ast.Tuple, ast.List)):
                        findings.extend(self._check_unpacked(target, node.value, node, filename))
                    else:
                        name = self._target_name(target)
                        if name and _SECRET_NAME_RE.search(name):
                            if self._is_secret_literal(node.value):
                                findings.append(
                                    self._make_finding(
                                        node=node,
                                        filename=filename,
                                        description=(f"{self.description} (variable: {name!r})"),
                                        fix_suggestion=_FIX,
                                        confidence=0.9,
                                    )
                                )

            # Annotated assignment:  password: str = "hunter2"
            elif isinstance(node, ast.AnnAssign):
                name = self._target_name(node.target)
                if name and _SECRET_NAME_RE.search(name) and node.value is not None:
                    if self._is_secret_literal(node.value):
                        findings.append(
                            self._make_finding(
                                node=node,
                                filename=filename,
                                description=(f"{self.description} (variable: {name!r})"),
                                fix_suggestion=_FIX,
                                confidence=0.9,
                            )
                        )

        return findings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_unpacked(
        self,
        target: ast.Tuple | ast.List,
        value: ast.AST,
        node: ast.AST,
        filename: str,
    ) -> list[Finding]:
        """Check each element of a tuple/list unpacking assignment.

        Handles patterns like:
            user, password = "admin", "hunter2"
            [username, api_key] = get_credentials()
        """
        findings: list[Finding] = []

        # Only inspect element-by-element when the RHS is also a tuple/list
        # literal so we can match targets to values positionally.
        if isinstance(value, (ast.Tuple, ast.List)):
            for tgt, val in zip(target.elts, value.elts, strict=False):
                name = self._target_name(tgt)
                if name and _SECRET_NAME_RE.search(name):
                    if self._is_secret_literal(val):
                        findings.append(
                            self._make_finding(
                                node=node,
                                filename=filename,
                                description=(f"{self.description} (variable: {name!r})"),
                                fix_suggestion=_FIX,
                                confidence=0.9,
                            )
                        )
        else:
            # RHS is not a literal tuple — we can't match positionally,
            # so flag any secret-named target in the unpacking.
            for tgt in target.elts:
                name = self._target_name(tgt)
                if name and _SECRET_NAME_RE.search(name):
                    findings.append(
                        self._make_finding(
                            node=node,
                            filename=filename,
                            description=(f"{self.description} (variable: {name!r})"),
                            fix_suggestion=_FIX,
                            confidence=0.7,
                        )
                    )

        return findings

    @staticmethod
    def _target_name(target: ast.AST) -> str | None:
        """Extract the simple name from a Name or Attribute target, or None."""
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return target.attr
        return None

    @staticmethod
    def _is_secret_literal(node: ast.AST) -> bool:
        """Return True if *node* is a non-empty string constant."""
        return (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and len(node.value) >= _MIN_SECRET_LEN
        )


REGISTRY.register(HardcodedSecretsRule())
