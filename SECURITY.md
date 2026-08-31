# Security Policy

## Supported versions

Only the latest `2.x` release receives security fixes.

| Version | Supported |
|---|---|
| 2.x (latest) | ✅ Yes |
| older | ❌ No |

## Reporting a vulnerability

**Please do not file public GitHub issues for security vulnerabilities.**

Use one of the following private channels:

1. **GitHub private vulnerability reporting** (preferred): go to the repository's **Security** tab → **Report a vulnerability**. This creates a private, encrypted thread visible only to maintainers.

2. **Email**: security@codeguard.dev (PGP key available on request). Use the subject line `[SECURITY] <brief description>`.

### What to include

- A clear description of the vulnerability
- Steps to reproduce (code snippet, command, or config that triggers it)
- The version of CodeGuard affected
- The potential impact in your assessment

### What to expect

- **Acknowledgement within 72 hours** of your report
- A preliminary assessment (valid / needs-more-info / not-a-vulnerability) within **7 days**
- A fix or mitigation timeline communicated before any public disclosure
- Credit in the release notes if you want it (opt-in)

We follow coordinated disclosure: we ask that you give us reasonable time to fix before publishing details. We will not take legal action against researchers acting in good faith.

## Scope

CodeGuard reads and analyses source code files. Vulnerabilities of particular interest:

- **Prompt injection via scanned files**: a maliciously crafted source file or README could attempt to hijack the analysis agent (a documented risk of agentic IDEs). This is a class of vulnerability CodeGuard itself aims to eventually detect.
- **Path traversal** in file scanning
- **Denial of service** via crafted ASTs (e.g., exponential-complexity patterns)
- **False negatives** in security rules that result in dangerous code going undetected
- **Dependency vulnerabilities** in CodeGuard's own dependencies

Out of scope (for the security channel):

- False positives in rules (file a regular GitHub issue)
- Missing rule coverage for new vulnerability classes (file a regular GitHub issue)
- UI/UX issues

## Dependency vulnerabilities

If you discover a vulnerability in one of CodeGuard's dependencies, please report it to that project's maintainers first, then notify us so we can update.
