#!/usr/bin/env python3
"""
CodeGuard AI - Services Package

This package contains the core business logic and analysis engines for CodeGuard AI.
"""

# Import AST Parser components
from .ast_parser import (
    ASTParserEngine,
    ParseResult,
    ASTNode,
    LanguageType,
    CodeMetrics,
    parse_code,
    get_code_metrics,
    detect_language
)

# Import AI Detection components
from .ai_detector import (
    AIDetectionEngine,
    AIDetectionResult,
    StatisticalAnalyzer,
    PatternMatcher,
    StyleAnalyzer,
    detect_ai_code,
    get_ai_confidence
)

# Import Security Scanner components
from .security_scanner import (
    SecurityScannerEngine,
    SecurityScanResult,
    VulnerabilityType,
    SeverityLevel,
    SecurityVulnerability,
    scan_code_security,
    get_security_score
)

# Import Performance Analyzer components
from .performance_analyzer import (
    PerformanceAnalyzerEngine,
    PerformanceAnalysisResult,
    PerformanceMetrics,
    ComplexityMetrics,
    PerformanceIssue,
    PerformanceLevel,
    analyze_code_performance,
    get_performance_score
)

# Import Quality Assessor components
from .quality_assessor import (
    QualityAssessorEngine,
    QualityAssessmentResult,
    QualityMetrics,
    QualityIssue,
    QualityLevel,
    QualityDimension,
    assess_code_quality,
    get_quality_score
)

# Export all components
__all__ = [
    # AST Parser
    'ASTParserEngine',
    'ParseResult',
    'ASTNode',
    'LanguageType',
    'CodeMetrics',
    'parse_code',
    'get_code_metrics',
    'detect_language',
    
    # AI Detection
    'AIDetectionEngine',
    'AIDetectionResult',
    'StatisticalAnalyzer',
    'PatternMatcher',
    'StyleAnalyzer',
    'detect_ai_code',
    'get_ai_confidence',
    
    # Security Scanner
    'SecurityScannerEngine',
    'SecurityScanResult',
    'VulnerabilityType',
    'SeverityLevel',
    'SecurityVulnerability',
    'scan_code_security',
    'get_security_score',
    
    # Performance Analyzer
    'PerformanceAnalyzerEngine',
    'PerformanceAnalysisResult',
    'PerformanceMetrics',
    'ComplexityMetrics',
    'PerformanceIssue',
    'PerformanceLevel',
    'analyze_code_performance',
    'get_performance_score',
    
    # Quality Assessor
    'QualityAssessorEngine',
    'QualityAssessmentResult',
    'QualityMetrics',
    'QualityIssue',
    'QualityLevel',
    'QualityDimension',
    'assess_code_quality',
    'get_quality_score'
]