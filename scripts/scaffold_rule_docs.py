# SPDX-License-Identifier: Apache-2.0
"""Write a starter docs/rules/<ID>.md for every registered rule that has none.

The page is built from the rule's metadata (title, severity, CWE, description,
options, autofix) and its fixtures (vulnerable / safe / fixed), so it starts
out accurate.  Edit the result by hand afterwards; existing pages are never
overwritten.  Then add the page to the Rules section of mkdocs.yml and to
docs/rules/index.md (tests/test_docs.py checks both).

    python scripts/scaffold_rule_docs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import codeguard.rules  # noqa: E402,F401 -- registers the built-in rules
from codeguard.engine.registry import REGISTRY  # noqa: E402
from codeguard.engine.rule import Rule  # noqa: E402
from codeguard.engine.runner import AnalysisRunner  # noqa: E402

LANG_NAME = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript"}
FENCE = {".py": "python", ".js": "js", ".jsx": "jsx", ".ts": "ts", ".tsx": "tsx"}
CATEGORIES = ("security", "performance", "quality")


def fixture(rule_id: str, name: str) -> Path | None:
    slug = rule_id.lower().replace("-", "_")
    for lang in LANG_NAME:
        for cat in CATEGORIES:
            directory = ROOT / "tests" / "fixtures" / lang / cat / slug
            hits = sorted(directory.glob(f"{name}.*")) if directory.is_dir() else []
            if hits:
                return hits[0]
    return None


def code_block(path: Path) -> list[str]:
    body = path.read_text(encoding="utf-8").rstrip()
    return [f"```{FENCE.get(path.suffix, '')}", body, "```", ""]


def page(rule: Rule) -> str:
    ordered = sorted(rule.languages, key=lambda x: x.value)
    langs = ", ".join(LANG_NAME[lang.value] for lang in ordered)
    meta = [
        f"**Severity:** {rule.severity.value.upper()}",
        f"**Category:** {rule.category.value}",
        f"**Languages:** {langs}",
    ]
    if rule.autofix:
        meta.append("**Autofix:** safe ([how it works](../autofix.md))")
    lines = [f"# {rule.id}: {rule.title}", "", " · ".join(meta)]
    refs = []
    if rule.cwe:
        number = rule.cwe.split("-")[1]
        refs.append(f"**CWE:** [{rule.cwe}](https://cwe.mitre.org/data/definitions/{number}.html)")
    if rule.owasp:
        refs.append(f"**OWASP:** {rule.owasp.replace(' - ', ' — ')}")
    if refs:
        lines[-1] += "  "
        lines.append(" · ".join(refs))
    lines += ["", "## What it catches", "", rule.description, ""]

    vulnerable, safe, fixed = (fixture(rule.id, n) for n in ("vulnerable", "safe", "fixed"))
    fix_text = getattr(sys.modules[type(rule).__module__], "_FIX", None) or getattr(
        rule, "fix_text", None
    )
    if vulnerable is not None:
        source = vulnerable.read_text(encoding="utf-8")
        if not fix_text:
            findings = AnalysisRunner(rule_ids=[rule.id]).run(source, filename=str(vulnerable))
            fix_text = next((f.fix_suggestion for f in findings if f.fix_suggestion), None)
        lines += ["Reported:", "", *code_block(vulnerable)]
    if safe is not None:
        lines += ["Not reported:", "", *code_block(safe)]
    lines += ["## How to fix", "", fix_text or "TODO: describe the fix.", ""]
    if rule.autofix and fixed is not None:
        lines += ["`codeguard scan --fix` (or the editor quick fix) rewrites the example to:", ""]
        lines += code_block(fixed)
        doc = sys.modules[type(rule).__module__].__doc__ or ""
        match = re.search(r"Autofix \(safe\):(.*?)(?:\n\n|\Z)", doc, re.S)
        if match:
            text = " ".join(match.group(1).split()).replace("``", "`")
            lines += ["The autofix is applied only when it is provably equivalent: " + text, ""]
    if rule.default_options:
        lines += ["## Options", "", "Set in `codeguard.toml`:", "", "```toml"]
        lines.append(f"[codeguard.rules.{rule.id}]")
        for key, value in rule.default_options.items():
            rendered = str(value).lower() if isinstance(value, bool) else repr(value)
            lines.append(f"{key} = {rendered}")
        lines += ["```", ""]
    comment = "#" if any(lang.value == "python" for lang in rule.languages) else "//"
    lines += [
        "## Suppress",
        "",
        "```text",
        f"{comment} codeguard: ignore[{rule.id}] reason: <why this is fine>",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    docs = ROOT / "docs" / "rules"
    written = 0
    for rule in REGISTRY.all():
        target = docs / f"{rule.id}.md"
        if not target.exists():
            target.write_text(page(rule), encoding="utf-8")
            print(f"wrote {target.relative_to(ROOT)}")
            written += 1
    if not written:
        print("every rule already has a page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
