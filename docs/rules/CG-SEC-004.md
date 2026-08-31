# CG-SEC-004: Unsafe Deserialization (pickle / yaml.load)

## Description
Detects use of `pickle.loads()` on untrusted data or `yaml.load()` without `SafeLoader`. Deserializing untrusted data with these functions can lead to arbitrary code execution.

## Security Risk
- **CWE**: CWE-502 — Deserialization of Untrusted Data
- **OWASP**: A08:2021 — Software and Data Integrity Failures

## Vulnerable Example
```python
import pickle
obj = pickle.loads(data_from_network)

import yaml
config = yaml.load(file_content)
```

## Safe Example
```python
import yaml
config = yaml.safe_load(file_content)

import json
data = json.loads(file_content)  # prefer JSON over pickle
```

## Remediation
Never unpickle data from untrusted sources. Use `yaml.safe_load()` instead of `yaml.load()`. Prefer JSON or other safe formats for data exchange.
