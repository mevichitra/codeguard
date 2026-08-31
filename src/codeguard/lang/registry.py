# SPDX-License-Identifier: Apache-2.0
"""Registry of available :class:`~codeguard.lang.base.LanguageSupport` backends."""

from __future__ import annotations

from pathlib import Path

from .base import Language, LanguageSupport
from .javascript import JavaScriptSupport
from .python_ast import PythonAstSupport
from .typescript import TypeScriptSupport

#: All registered language backends, keyed by :class:`Language`.
LANGUAGES: dict[Language, LanguageSupport] = {
    Language.PYTHON: PythonAstSupport(),
    Language.JAVASCRIPT: JavaScriptSupport(),
    Language.TYPESCRIPT: TypeScriptSupport(),
}

_EXTENSION_INDEX: dict[str, Language] = {
    ext: lang for lang, support in LANGUAGES.items() for ext in support.extensions
}


def language_for_path(path: str | Path) -> Language | None:
    """Return the language for *path* based on its extension, or ``None``."""
    return _EXTENSION_INDEX.get(Path(path).suffix.lower())


def support_for(language: Language) -> LanguageSupport:
    """Return the backend for *language*.

    Raises
    ------
    KeyError
        If no backend is registered for *language*.
    """
    return LANGUAGES[language]
