# CG-SEC-001: SQL Injection via String Formatting

## Description
Detects SQL queries constructed using f-strings, `.format()`, or `%` string formatting with user-controlled input. This allows attackers to manipulate the query logic, bypass authentication, or exfiltrate data.

## Security Risk
- **CWE**: CWE-89 — Improper Neutralization of Special Elements used in an SQL Command
- **OWASP**: A03:2021 — Injection

## Vulnerable Example
```python
def get_user(uid):
    query = f"SELECT * FROM users WHERE id = {uid}"
    cursor.execute(query)
```

## Safe Example
```python
def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))
```

## Remediation
Always use parameterized queries or prepared statements. Never concatenate or interpolate user input directly into SQL strings.
