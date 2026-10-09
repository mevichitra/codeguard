# SPDX-License-Identifier: Apache-2.0
"""Security rules — imported for side-effect (registers rules into REGISTRY)."""

from . import cg_sec_001_sql_injection as _001  # noqa: F401
from . import cg_sec_002_hardcoded_secrets as _002  # noqa: F401
from . import cg_sec_003_eval_exec as _003  # noqa: F401
from . import cg_sec_004_unsafe_deserialization as _004  # noqa: F401
from . import cg_sec_005_shell_injection as _005  # noqa: F401
from . import cg_sec_006_weak_hash as _006  # noqa: F401
from . import cg_sec_007_tls_verify_disabled as _007  # noqa: F401
from . import cg_sec_008_insecure_tempfile as _008  # noqa: F401
from . import cg_sec_009_insecure_random as _009  # noqa: F401
from . import cg_sec_010_taint_sql as _010  # noqa: F401
from . import cg_sec_011_taint_shell as _011  # noqa: F401
from . import cg_sec_012_taint_eval as _012  # noqa: F401
from . import cg_sec_013_taint_path as _013  # noqa: F401
from . import cg_sec_014_taint_redirect as _014  # noqa: F401
