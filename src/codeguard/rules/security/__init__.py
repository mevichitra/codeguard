# SPDX-License-Identifier: Apache-2.0
"""Security rules — imported for side-effect (registers rules into REGISTRY)."""

from . import cg_sec_001_sql_injection as _001  # noqa: F401
from . import cg_sec_002_hardcoded_secrets as _002  # noqa: F401
from . import cg_sec_003_eval_exec as _003  # noqa: F401
from . import cg_sec_004_unsafe_deserialization as _004  # noqa: F401
from . import cg_sec_005_shell_injection as _005  # noqa: F401
