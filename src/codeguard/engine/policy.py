# SPDX-License-Identifier: Apache-2.0
"""Apply configuration to a raw finding list.

Keeps the CLI thin: given the findings from a scan plus a
:class:`~codeguard.config.schema.Config`, produce the findings to report
(severity remapped, per-path rules applied, confidence floors enforced) and
decide whether any of them should fail the run.
"""

from __future__ import annotations

from dataclasses import replace

import pathspec

from codeguard.config.schema import Config
from codeguard.engine.finding import Finding, Severity
from codeguard.engine.fingerprint import relative_path

_SEV = {s.value: s for s in Severity}


def _matches(path_glob: str, rel_file: str) -> bool:
    spec = pathspec.PathSpec.from_lines("gitignore", [path_glob])
    return spec.match_file(rel_file)


def apply_config(
    findings: list[Finding], config: Config, *, root: str | None = None
) -> list[Finding]:
    """Return the findings to report after severity remap + per-path overrides.

    Findings suppressed by a path override are returned with ``suppressed=True``
    (like inline suppressions) so ``--show-suppressed`` and SARIF still see them.
    """
    remap = dict(config.severity_remap)
    per_rule = config.rules

    out: list[Finding] = []
    for f in findings:
        rel_file = relative_path(f.location.file, root=root)
        new_sev = f.severity
        if f.rule_id in remap:
            new_sev = _SEV[remap[f.rule_id]]
        rs = per_rule.get(f.rule_id)
        if rs and rs.severity:
            new_sev = _SEV[rs.severity]

        suppressed = f.suppressed
        for ov in config.overrides:
            if _matches(ov.path, rel_file):
                if ov.disable and (f.rule_id in ov.disable or "ALL" in ov.disable):
                    suppressed = True
                if ov.enable and f.rule_id not in ov.enable:
                    suppressed = True

        if new_sev != f.severity or suppressed != f.suppressed:
            f = replace(f, severity=new_sev, suppressed=suppressed)

        if rs and rs.confidence_min is not None and f.confidence < rs.confidence_min:
            continue

        out.append(f)
    return out


def gating_findings(findings: list[Finding], fail_on: str) -> list[Finding]:
    """The findings that should fail the run: active, not baselined, and at or
    above the ``fail_on`` threshold.  ``fail_on == "never"`` -> always empty.
    """
    if fail_on == "never":
        return []
    threshold = _SEV[fail_on]
    return [f for f in findings if not f.suppressed and not f.baselined and f.severity >= threshold]
