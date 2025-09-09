#!/usr/bin/env python3
"""
CodeGuard AI - Security Vulnerability Scanner

Comprehensive security scanner that detects OWASP Top 10 vulnerabilities
plus AI-specific security issues in code.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple

from .ast_parser import ParseResult, ASTNode, LanguageType

# Configure logging
logger = logging.getLogger(__name__)

class VulnerabilityType(Enum):
    """Types of security vulnerabilities"""
    # OWASP Top 10 2021
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    CRYPTOGRAPHIC_FAILURES = "cryptographic_failures"
    INJECTION = "injection"
    INSECURE_DESIGN = "insecure_design"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"
    VULNERABLE_COMPONENTS = "vulnerable_components"
    IDENTIFICATION_FAILURES = "identification_failures"
    SOFTWARE_INTEGRITY_FAILURES = "software_integrity_failures"
    LOGGING_MONITORING_FAILURES = "logging_monitoring_failures"
    SSRF = "server_side_request_forgery"
    
    # AI-Specific Vulnerabilities
    AI_MODEL_POISONING = "ai_model_poisoning"
    AI_PROMPT_INJECTION = "ai_prompt_injection"
    AI_DATA_LEAKAGE = "ai_data_leakage"
    AI_ADVERSARIAL_ATTACKS = "ai_adversarial_attacks"
    AI_BIAS_DISCRIMINATION = "ai_bias_discrimination"
    AI_PRIVACY_VIOLATION = "ai_privacy_violation"
    
    # General Security Issues
    HARDCODED_SECRETS = "hardcoded_secrets"
    WEAK_RANDOMNESS = "weak_randomness"
    INSECURE_COMMUNICATION = "insecure_communication"
    BUFFER_OVERFLOW = "buffer_overflow"
    RACE_CONDITION = "race_condition"

class SeverityLevel(Enum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class SecurityVulnerability:
    """Security vulnerability information"""
    vuln_type: VulnerabilityType
    severity: SeverityLevel
    title: str
    description: str
    line_start: int
    line_end: int
    column_start: int = 0
    column_end: int = 0
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    remediation: Optional[str] = None
    evidence: Dict[str, Any] = None
    confidence: float = 1.0
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vuln_type': self.vuln_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'column_start': self.column_start,
            'column_end': self.column_end,
            'cwe_id': self.cwe_id,
            'owasp_category': self.owasp_category,
            'remediation': self.remediation,
            'evidence': self.evidence,
            'confidence': self.confidence
        }

@dataclass
class SecurityScanResult:
    """Result of security vulnerability scan"""
    vulnerabilities: List[SecurityVulnerability]
    total_count: int
    severity_counts: Dict[str, int]
    scan_summary: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        
        # Calculate counts
        self.total_count = len(self.vulnerabilities)
        self.severity_counts = {
            'critical': sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.CRITICAL),
            'high': sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.HIGH),
            'medium': sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.MEDIUM),
            'low': sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.LOW),
            'info': sum(1 for v in self.vulnerabilities if v.severity == SeverityLevel.INFO)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vulnerabilities': [v.to_dict() for v in self.vulnerabilities],
            'total_count': self.total_count,
            'severity_counts': self.severity_counts,
            'scan_summary': self.scan_summary,
            'timestamp': self.timestamp.isoformat()
        }

class InjectionScanner:
    """Scanner for injection vulnerabilities"""
    
    def __init__(self):
        self.sql_patterns = [
            r'SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*["\']\s*\+',
            r'INSERT\s+INTO\s+.*VALUES\s*\([^)]*["\']\s*\+',
            r'UPDATE\s+.*SET\s+.*["\']\s*\+',
            r'DELETE\s+FROM\s+.*WHERE\s+.*["\']\s*\+',
            r'execute\s*\(\s*["\'][^"\']*(\%s|\?).*["\']\s*\%',
            r'cursor\.execute\s*\([^)]*["\'].*["\']\s*\%'
        ]
        
        self.xss_patterns = [
            r'innerHTML\s*=\s*[^;]*\+',
            r'document\.write\s*\([^)]*\+',
            r'eval\s*\([^)]*\+',
            r'setTimeout\s*\([^)]*\+',
            r'setInterval\s*\([^)]*\+'
        ]
        
        self.command_injection_patterns = [
            r'os\.system\s*\([^)]*\+',
            r'subprocess\.(call|run|Popen)\s*\([^)]*\+',
            r'exec\s*\([^)]*\+',
            r'eval\s*\([^)]*\+'
        ]
    
    def scan(self, code: str, language: LanguageType) -> List[SecurityVulnerability]:
        """Scan for injection vulnerabilities"""
        vulnerabilities = []
        
        # SQL Injection
        vulnerabilities.extend(self._scan_sql_injection(code))
        
        # XSS (for web languages)
        if language in [LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]:
            vulnerabilities.extend(self._scan_xss(code))
        
        # Command Injection
        vulnerabilities.extend(self._scan_command_injection(code))
        
        return vulnerabilities
    
    def _scan_sql_injection(self, code: str) -> List[SecurityVulnerability]:
        """Scan for SQL injection vulnerabilities"""
        vulnerabilities = []
        
        for pattern in self.sql_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.INJECTION,
                    severity=SeverityLevel.HIGH,
                    title="SQL Injection Vulnerability",
                    description="Potential SQL injection vulnerability detected. User input appears to be directly concatenated into SQL query.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 – Injection",
                    remediation="Use parameterized queries or prepared statements instead of string concatenation.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities
    
    def _scan_xss(self, code: str) -> List[SecurityVulnerability]:
        """Scan for XSS vulnerabilities"""
        vulnerabilities = []
        
        for pattern in self.xss_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.INJECTION,
                    severity=SeverityLevel.HIGH,
                    title="Cross-Site Scripting (XSS) Vulnerability",
                    description="Potential XSS vulnerability detected. User input may be directly inserted into DOM without sanitization.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-79",
                    owasp_category="A03:2021 – Injection",
                    remediation="Sanitize and validate all user input before inserting into DOM. Use textContent instead of innerHTML when possible.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities
    
    def _scan_command_injection(self, code: str) -> List[SecurityVulnerability]:
        """Scan for command injection vulnerabilities"""
        vulnerabilities = []
        
        for pattern in self.command_injection_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.INJECTION,
                    severity=SeverityLevel.CRITICAL,
                    title="Command Injection Vulnerability",
                    description="Potential command injection vulnerability detected. User input may be directly executed as system commands.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-78",
                    owasp_category="A03:2021 – Injection",
                    remediation="Avoid executing user input as system commands. Use safe alternatives or strict input validation.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities

class CryptographicScanner:
    """Scanner for cryptographic failures"""
    
    def __init__(self):
        self.weak_crypto_patterns = [
            r'md5\s*\(',
            r'sha1\s*\(',
            r'DES\s*\(',
            r'RC4\s*\(',
            r'random\.random\s*\(',
            r'Math\.random\s*\('
        ]
        
        self.hardcoded_key_patterns = [
            r'["\'][A-Za-z0-9+/]{32,}[=]{0,2}["\']',  # Base64 keys
            r'["\'][A-Fa-f0-9]{32,}["\']',  # Hex keys
            r'password\s*=\s*["\'][^"\']',
            r'secret\s*=\s*["\'][^"\']',
            r'api_key\s*=\s*["\'][^"\']'
        ]
    
    def scan(self, code: str) -> List[SecurityVulnerability]:
        """Scan for cryptographic vulnerabilities"""
        vulnerabilities = []
        
        # Weak cryptographic algorithms
        vulnerabilities.extend(self._scan_weak_crypto(code))
        
        # Hardcoded secrets
        vulnerabilities.extend(self._scan_hardcoded_secrets(code))
        
        return vulnerabilities
    
    def _scan_weak_crypto(self, code: str) -> List[SecurityVulnerability]:
        """Scan for weak cryptographic algorithms"""
        vulnerabilities = []
        
        for pattern in self.weak_crypto_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.CRYPTOGRAPHIC_FAILURES,
                    severity=SeverityLevel.MEDIUM,
                    title="Weak Cryptographic Algorithm",
                    description="Usage of weak or deprecated cryptographic algorithm detected.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-327",
                    owasp_category="A02:2021 – Cryptographic Failures",
                    remediation="Use strong cryptographic algorithms like SHA-256, AES, or modern alternatives.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities
    
    def _scan_hardcoded_secrets(self, code: str) -> List[SecurityVulnerability]:
        """Scan for hardcoded secrets and keys"""
        vulnerabilities = []
        
        for pattern in self.hardcoded_key_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.HARDCODED_SECRETS,
                    severity=SeverityLevel.HIGH,
                    title="Hardcoded Secret Detected",
                    description="Potential hardcoded secret, password, or API key detected in source code.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-798",
                    owasp_category="A02:2021 – Cryptographic Failures",
                    remediation="Store secrets in environment variables or secure configuration files, not in source code.",
                    evidence={'pattern': pattern, 'match': match.group()[:20] + '...'}
                ))
        
        return vulnerabilities

class AISecurityScanner:
    """Scanner for AI-specific security vulnerabilities"""
    
    def __init__(self):
        self.prompt_injection_patterns = [
            r'user_input.*\+.*prompt',
            r'prompt.*\+.*user',
            r'f["\'].*{.*user.*}.*["\']',
            r'format\s*\(.*user.*\)'
        ]
        
        self.model_poisoning_patterns = [
            r'model\.load\s*\([^)]*user',
            r'pickle\.load\s*\(',
            r'joblib\.load\s*\([^)]*user',
            r'torch\.load\s*\([^)]*user'
        ]
        
        self.data_leakage_patterns = [
            r'print\s*\(.*password',
            r'print\s*\(.*secret',
            r'log.*\(.*password',
            r'log.*\(.*secret',
            r'model\.predict\s*\(.*personal'
        ]
    
    def scan(self, code: str) -> List[SecurityVulnerability]:
        """Scan for AI-specific security vulnerabilities"""
        vulnerabilities = []
        
        # AI Prompt Injection
        vulnerabilities.extend(self._scan_prompt_injection(code))
        
        # AI Model Poisoning
        vulnerabilities.extend(self._scan_model_poisoning(code))
        
        # AI Data Leakage
        vulnerabilities.extend(self._scan_data_leakage(code))
        
        return vulnerabilities
    
    def _scan_prompt_injection(self, code: str) -> List[SecurityVulnerability]:
        """Scan for AI prompt injection vulnerabilities"""
        vulnerabilities = []
        
        for pattern in self.prompt_injection_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.AI_PROMPT_INJECTION,
                    severity=SeverityLevel.HIGH,
                    title="AI Prompt Injection Vulnerability",
                    description="Potential prompt injection vulnerability detected. User input may be directly concatenated into AI prompts.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-94",
                    owasp_category="AI-Specific Vulnerability",
                    remediation="Sanitize and validate user input before including in AI prompts. Use prompt templates with proper escaping.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities
    
    def _scan_model_poisoning(self, code: str) -> List[SecurityVulnerability]:
        """Scan for AI model poisoning vulnerabilities"""
        vulnerabilities = []
        
        for pattern in self.model_poisoning_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.AI_MODEL_POISONING,
                    severity=SeverityLevel.CRITICAL,
                    title="AI Model Poisoning Risk",
                    description="Potential model poisoning vulnerability detected. Untrusted model files may be loaded.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-502",
                    owasp_category="AI-Specific Vulnerability",
                    remediation="Only load models from trusted sources. Validate model integrity before loading.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities
    
    def _scan_data_leakage(self, code: str) -> List[SecurityVulnerability]:
        """Scan for AI data leakage vulnerabilities"""
        vulnerabilities = []
        
        for pattern in self.data_leakage_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerabilities.append(SecurityVulnerability(
                    vuln_type=VulnerabilityType.AI_DATA_LEAKAGE,
                    severity=SeverityLevel.MEDIUM,
                    title="AI Data Leakage Risk",
                    description="Potential data leakage detected. Sensitive information may be exposed through logging or output.",
                    line_start=line_num,
                    line_end=line_num,
                    cwe_id="CWE-200",
                    owasp_category="AI-Specific Vulnerability",
                    remediation="Avoid logging or printing sensitive data. Implement proper data sanitization.",
                    evidence={'pattern': pattern, 'match': match.group()}
                ))
        
        return vulnerabilities

class SecurityScannerEngine:
    """Main security scanner engine that coordinates all security scanners"""
    
    def __init__(self):
        self.injection_scanner = InjectionScanner()
        self.crypto_scanner = CryptographicScanner()
        self.ai_scanner = AISecurityScanner()
    
    def scan_code(self, code: str, filename: str = "", ast_result: Optional[ParseResult] = None) -> SecurityScanResult:
        """Perform comprehensive security scan on code"""
        try:
            # Determine language
            if ast_result and ast_result.success:
                language = ast_result.language
            else:
                from .ast_parser import detect_language
                language = detect_language(filename, code)
            
            all_vulnerabilities = []
            
            # Injection vulnerabilities
            injection_vulns = self.injection_scanner.scan(code, language)
            all_vulnerabilities.extend(injection_vulns)
            
            # Cryptographic vulnerabilities
            crypto_vulns = self.crypto_scanner.scan(code)
            all_vulnerabilities.extend(crypto_vulns)
            
            # AI-specific vulnerabilities
            ai_vulns = self.ai_scanner.scan(code)
            all_vulnerabilities.extend(ai_vulns)
            
            # Create scan summary
            scan_summary = self._create_scan_summary(all_vulnerabilities, language, filename)
            
            return SecurityScanResult(
                vulnerabilities=all_vulnerabilities,
                total_count=len(all_vulnerabilities),
                severity_counts={},  # Will be calculated in __post_init__
                scan_summary=scan_summary
            )
            
        except Exception as e:
            logger.error(f"Error in security scan: {str(e)}")
            return SecurityScanResult(
                vulnerabilities=[],
                total_count=0,
                severity_counts={},
                scan_summary={'error': str(e)}
            )
    
    def scan_file(self, file_path: str) -> SecurityScanResult:
        """Scan a file for security vulnerabilities"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            return self.scan_code(code, file_path)
            
        except FileNotFoundError:
            return SecurityScanResult(
                vulnerabilities=[],
                total_count=0,
                severity_counts={},
                scan_summary={'error': f'File not found: {file_path}'}
            )
        except Exception as e:
            return SecurityScanResult(
                vulnerabilities=[],
                total_count=0,
                severity_counts={},
                scan_summary={'error': str(e)}
            )
    
    def _create_scan_summary(self, vulnerabilities: List[SecurityVulnerability], 
                           language: LanguageType, filename: str) -> Dict[str, Any]:
        """Create summary of security scan results"""
        vuln_types = [v.vuln_type.value for v in vulnerabilities]
        owasp_categories = [v.owasp_category for v in vulnerabilities if v.owasp_category]
        
        return {
            'filename': filename,
            'language': language.value,
            'total_vulnerabilities': len(vulnerabilities),
            'unique_vulnerability_types': len(set(vuln_types)),
            'vulnerability_types': list(set(vuln_types)),
            'owasp_categories': list(set(owasp_categories)),
            'highest_severity': self._get_highest_severity(vulnerabilities),
            'scan_timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_highest_severity(self, vulnerabilities: List[SecurityVulnerability]) -> str:
        """Get the highest severity level from vulnerabilities"""
        if not vulnerabilities:
            return SeverityLevel.INFO.value
        
        severity_order = {
            SeverityLevel.CRITICAL: 5,
            SeverityLevel.HIGH: 4,
            SeverityLevel.MEDIUM: 3,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFO: 1
        }
        
        highest = max(vulnerabilities, key=lambda v: severity_order[v.severity])
        return highest.severity.value

# Global scanner instance
security_scanner = SecurityScannerEngine()

# Convenience functions
def scan_code_security(code: str, filename: str = "") -> SecurityScanResult:
    """Scan code for security vulnerabilities"""
    return security_scanner.scan_code(code, filename)

def scan_file_security(file_path: str) -> SecurityScanResult:
    """Scan file for security vulnerabilities"""
    return security_scanner.scan_file(file_path)

def has_critical_vulnerabilities(code: str, filename: str = "") -> bool:
    """Check if code has critical security vulnerabilities"""
    result = security_scanner.scan_code(code, filename)
    return any(v.severity == SeverityLevel.CRITICAL for v in result.vulnerabilities)

def get_security_score(code: str, filename: str = "") -> float:
    """Get security score for code (0-100, higher is better)"""
    result = security_scanner.scan_code(code, filename)
    if not result.vulnerabilities:
        return 100.0
    
    # Calculate score based on severity and count
    severity_weights = {
        SeverityLevel.CRITICAL: 25,
        SeverityLevel.HIGH: 15,
        SeverityLevel.MEDIUM: 8,
        SeverityLevel.LOW: 3,
        SeverityLevel.INFO: 1
    }
    
    total_penalty = sum(severity_weights.get(v.severity, 1) for v in result.vulnerabilities)
    score = max(0, 100 - total_penalty)
    return float(score)