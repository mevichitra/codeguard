# SPDX-License-Identifier: Apache-2.0
"""JavaScript / TypeScript security rules (imported for side-effect)."""

from . import cg_sec_101_dynamic_code as _101  # noqa: F401
from . import cg_sec_102_child_process as _102  # noqa: F401
from . import cg_sec_103_dom_xss as _103  # noqa: F401
from . import cg_sec_104_react_dangerous_html as _104  # noqa: F401
from . import cg_sec_105_hardcoded_secret as _105  # noqa: F401
from . import cg_sec_106_weak_random as _106  # noqa: F401
from . import cg_sec_107_weak_hash as _107  # noqa: F401
from . import cg_sec_108_tls_verify_disabled as _108  # noqa: F401
from . import cg_sec_109_open_redirect as _109  # noqa: F401
from . import cg_sec_110_path_traversal as _110  # noqa: F401
from . import cg_sec_111_prototype_pollution as _111  # noqa: F401
