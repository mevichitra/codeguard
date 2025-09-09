# CodeGuard Test Samples

This directory contains sample code files with various types of vulnerabilities, performance issues, and code quality problems to demonstrate CodeGuard's analysis capabilities.

## Sample Directories

### 1. SQL Injection (`sql_injection/`)
**File:** `vulnerable_login.py`
- SQL injection vulnerabilities
- Weak cryptographic functions (MD5)
- Hardcoded credentials
- Sensitive data logging

### 2. Performance Issues (`performance_issues/`)
**File:** `inefficient_code.js`
- O(n³) algorithmic complexity
- Memory leaks (global cache, event listeners)
- Inefficient DOM manipulation
- Blocking synchronous operations
- Inefficient string concatenation

### 3. Code Quality (`code_quality/`)
**File:** `poor_quality.java`
- Deep nesting (8+ levels)
- Code duplication
- Long methods and parameter lists
- Magic numbers
- Inconsistent naming conventions
- God class anti-pattern

### 4. AI-Generated Code (`ai_generated/`)
**File:** `chatgpt_style.py`
- Excessive comments
- Generic variable names (result, data, item)
- Redundant documentation
- Overly verbose code structure
- Typical AI-generated patterns

### 5. Mixed Vulnerabilities (`mixed_vulnerabilities/`)
**File:** `web_security.php`
- XSS (Cross-Site Scripting)
- SQL injection
- Command injection
- Insecure file upload
- Weak session management
- Information disclosure
- CSRF vulnerabilities
- Insecure cryptography

## How to Scan These Samples

### Using the Web Interface
1. Open http://localhost:3000 in your browser
2. Upload any of the sample files
3. Select the appropriate language
4. Click "Analyze" to see the results

### Using the API

#### Scan a single file:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "file=@test_samples/sql_injection/vulnerable_login.py" \
  -F "language=python"
```

#### Scan JavaScript file:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "file=@test_samples/performance_issues/inefficient_code.js" \
  -F "language=javascript"
```

#### Scan Java file:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "file=@test_samples/code_quality/poor_quality.java" \
  -F "language=java"
```

#### Scan PHP file:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -F "file=@test_samples/mixed_vulnerabilities/web_security.php" \
  -F "language=php"
```

### Using Python Script
```python
import requests

# Analyze a file
with open('test_samples/sql_injection/vulnerable_login.py', 'rb') as f:
    files = {'file': f}
    data = {'language': 'python'}
    response = requests.post('http://localhost:8000/api/v1/analyze', files=files, data=data)
    print(response.json())
```

## Expected Analysis Results

### Security Vulnerabilities
- **High Severity**: SQL injection, command injection, XSS
- **Medium Severity**: Weak cryptography, hardcoded secrets
- **Low Severity**: Information disclosure, insecure configurations

### Performance Issues
- **Algorithmic Complexity**: O(n³) algorithms detected
- **Memory Leaks**: Global variables, uncleaned event listeners
- **Inefficient Operations**: DOM manipulation, string concatenation

### Code Quality Issues
- **Maintainability**: Deep nesting, long methods
- **Readability**: Magic numbers, unclear variable names
- **Design**: Code duplication, god classes

### AI Detection
- **Confidence Scores**: 0.6-0.8 for AI-generated samples
- **Pattern Detection**: Generic naming, excessive comments
- **Structural Analysis**: Typical AI code organization

## Directory Scanning

To scan an entire directory, you can use a script like this:

```bash
#!/bin/bash
for file in test_samples/*/*.py; do
    echo "Analyzing: $file"
    curl -X POST "http://localhost:8000/api/v1/analyze" \
      -F "file=@$file" \
      -F "language=python" \
      -s | jq '.summary'
done
```

This demonstrates CodeGuard's ability to scan any local directory containing code files and identify various types of security, performance, and quality issues.