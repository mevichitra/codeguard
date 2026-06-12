# Fixture: CG-SEC-002 safe
# This file MUST NOT trigger CG-SEC-002.
# Shows correct patterns for handling secrets.

import os

# SAFE: loaded from environment variable
password = os.environ["DB_PASSWORD"]

# SAFE: loaded from os.getenv with no hardcoded fallback
api_key = os.getenv("API_KEY")

# SAFE: placeholder makes intent clear AND value is not a secret string
# (empty string default — not a real secret value)
auth_token = os.getenv("AUTH_TOKEN", "")

# SAFE: non-secret variable name, happens to hold a string
user_display_name = "Alice"
greeting = "hello world"

# SAFE: config loaded from a file/config system (name has "password" but value is not a literal)
db_password = os.getenv("DATABASE_URL", "").split("@")[0].split(":")[-1]
