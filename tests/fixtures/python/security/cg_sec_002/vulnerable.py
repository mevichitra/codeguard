# Fixture: CG-SEC-002 vulnerable
# This file MUST trigger CG-SEC-002 (hardcoded secrets).

# VULNERABLE: hardcoded password
password = "hunter2"

# VULNERABLE: hardcoded API key
api_key = "sk-abc123secretkey"

# VULNERABLE: hardcoded token in annotation
auth_token: str = "Bearer eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWRtaW4ifQ.fakesig"


class Config:
    # VULNERABLE: hardcoded secret in class attribute
    client_secret = "my-super-secret-oauth-secret"
    db_password = "postgres_admin_pass"
