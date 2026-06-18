# CG-SEC-002: Hardcoded Secrets

## Description
Detects hardcoded passwords, API keys, tokens, and secrets assigned directly to variables. Hardcoded credentials embedded in source code can be exposed via version control history or code leaks.

## Security Risk
- **CWE**: CWE-798 — Use of Hard-coded Credentials
- **OWASP**: A07:2021 — Identification and Authentication Failures

## Vulnerable Example
```python
api_key = "sk-abc123xyz"
password = "supersecret123"
```

## Safe Example
```python
import os
api_key = os.environ.get("API_KEY")
password = os.environ.get("DB_PASSWORD")
```

## Remediation
Load secrets from environment variables, a secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault), or a `.env` file that is excluded from version control.
