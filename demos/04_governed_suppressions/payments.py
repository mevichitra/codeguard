"""
Demo 4: Governed Suppressions & Auditing
Demonstrates enforcement of justification reasons, expiry dates, and debt tracking.
"""

import os
import sqlite3

# CASE 1: Compliant suppression with valid reason
# Suppressed cleanly because reason is provided.
cursor = sqlite3.connect("db").cursor()
cursor.execute(f"SELECT * FROM users WHERE id = {123}")  # codeguard: ignore[CG-SEC-001] reason: constant int literal

# CASE 2: Bare suppression WITHOUT reason
# Suppresses CG-SEC-001, but CodeGuard raises CG-META-001 (Missing reason)
cursor.execute(f"SELECT * FROM accounts WHERE id = {'abc'}")  # codeguard: ignore[CG-SEC-001]

# CASE 3: Temporary waiver with an EXPIRED date (until=2024-01-01)
# Expired: Underlying CG-SEC-005 reactivates AND CG-META-002 is raised!
os.system(f"echo processing {123}")  # codeguard: ignore[CG-SEC-005] reason: refactor to subprocess pending until=2024-01-01

# CASE 4: Unused suppression (rule doesn't fire on this line)
# Detected during audits with 'codeguard suppressions list --unused'
safe_variable = 42  # codeguard: ignore[CG-SEC-002] reason: dead waiver left behind
