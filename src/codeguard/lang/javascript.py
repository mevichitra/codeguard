# SPDX-License-Identifier: Apache-2.0
"""JavaScript language support (tree-sitter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import Language
from .treesitter import TreeSitterSupport, _load_language

if TYPE_CHECKING:
    import tree_sitter


class JavaScriptSupport(TreeSitterSupport):
    language = Language.JAVASCRIPT
    extensions = (".js", ".jsx", ".mjs", ".cjs")

    def _ts_language(self) -> tree_sitter.Language:
        return _load_language("tree_sitter_javascript", "language")
