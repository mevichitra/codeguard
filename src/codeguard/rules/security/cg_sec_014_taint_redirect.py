# SPDX-License-Identifier: Apache-2.0
"""CG-SEC-014 -- request data used as a redirect target (open redirect, taint).

``flask.redirect()``, Django ``redirect()`` / ``HttpResponseRedirect()``,
Starlette / FastAPI ``RedirectResponse()`` with a URL built from request data.
CWE-601.
"""

from __future__ import annotations

import ast

from codeguard.engine.finding import Severity
from codeguard.engine.registry import REGISTRY
from codeguard.rules._pyimports import ImportMap
from codeguard.rules._pysinks import redirect_call_arg

from ._taint import TaintRule, call_label


class TaintedRedirectRule(TaintRule):
    id = "CG-SEC-014"
    title = "Request data used as a redirect target"
    description = (
        "The user is redirected to a URL taken from the request. Attackers use this "
        "to send victims from a trusted domain to a phishing site (open redirect)."
    )
    severity = Severity.MEDIUM
    cwe = "CWE-601"
    owasp = "A01:2021 - Broken Access Control"
    source_kinds = frozenset({"web"})
    fix_text = (
        "Redirect only to relative paths or an allow-list of hosts; Django offers "
        "url_has_allowed_host_and_scheme() for this check."
    )

    def sink(self, call: ast.Call, imports: ImportMap) -> tuple[ast.expr, str] | None:
        arg = redirect_call_arg(call, imports)
        return (arg, call_label(call)) if arg is not None else None


REGISTRY.register(TaintedRedirectRule())
