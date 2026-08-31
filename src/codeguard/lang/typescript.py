# SPDX-License-Identifier: Apache-2.0
"""TypeScript language support (tree-sitter).

The ``.tsx`` grammar is a superset that also parses ``.ts``; using it for both
keeps things simple and still parses plain TypeScript correctly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Language
from .treesitter import TreeSitterSupport, _load_language

if TYPE_CHECKING:
    import tree_sitter


class TypeScriptSupport(TreeSitterSupport):
    language = Language.TYPESCRIPT
    extensions = (".ts", ".tsx", ".mts", ".cts")

    def _ts_language(self) -> tree_sitter.Language:
        return _load_language("tree_sitter_typescript", "language_tsx")
