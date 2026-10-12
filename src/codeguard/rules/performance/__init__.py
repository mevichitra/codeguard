# SPDX-License-Identifier: Apache-2.0
"""Performance rules (CG-PERF-*) -- imported for side-effect (registers rules)."""

from . import _js as _js_rules  # noqa: F401
from . import cg_perf_001_list_membership as _001  # noqa: F401
from . import cg_perf_002_str_concat_loop as _002  # noqa: F401
from . import cg_perf_003_range_len as _003  # noqa: F401
from . import cg_perf_004_redundant_keys as _004  # noqa: F401
from . import cg_perf_005_regex_in_loop as _005  # noqa: F401
