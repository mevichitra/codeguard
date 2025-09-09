#!/usr/bin/env python3
"""
CodeGuard AI - Code Quality Assessment Module

Assesses code quality using multiple dimensions including maintainability,
readability, testability, and adherence to best practices.
"""

import ast
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple

import numpy as np

from .ast_parser import ParseResult, ASTNode, LanguageType, CodeMetrics
from .performance_analyzer import ComplexityMetrics

# Configure logging
logger = logging.getLogger(__name__)

class QualityDimension(Enum):
    """Quality assessment dimensions"""
    MAINTAINABILITY = "maintainability"
    READABILITY = "readability"
    TESTABILITY = "testability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    STYLE_CONSISTENCY = "style_consistency"

class QualityLevel(Enum):
    """Quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

class QualityIssueType(Enum):
    """Types of quality issues"""
    NAMING_CONVENTION = "naming_convention"
    MISSING_DOCUMENTATION = "missing_documentation"
    LONG_FUNCTION = "long_function"
    DEEP_NESTING = "deep_nesting"
    MAGIC_NUMBERS = "magic_numbers"
    DUPLICATE_CODE = "duplicate_code"
    UNUSED_VARIABLES = "unused_variables"
    INCONSISTENT_STYLE = "inconsistent_style"
    MISSING_ERROR_HANDLING = "missing_error_handling"
    HARD_CODED_VALUES = "hard_coded_values"
    POOR_SEPARATION = "poor_separation"
    MISSING_TESTS = "missing_tests"

@dataclass
class QualityIssue:
    """Quality issue information"""
    issue_type: QualityIssueType
    dimension: QualityDimension
    severity: QualityLevel
    title: str
    description: str
    line_start: int
    line_end: int
    impact_score: float  # 0-100
    recommendation: str
    evidence: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'issue_type': self.issue_type.value,
            'dimension': self.dimension.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'impact_score': self.impact_score,
            'recommendation': self.recommendation,
            'evidence': self.evidence
        }

@dataclass
class QualityMetrics:
    """Quality assessment metrics"""
    overall_score: float  # 0-100
    maintainability_score: float
    readability_score: float
    testability_score: float
    reliability_score: float
    documentation_score: float
    style_consistency_score: float
    technical_debt_ratio: float  # 0-1
    code_coverage_estimate: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class QualityAssessmentResult:
    """Result of quality assessment"""
    metrics: QualityMetrics
    issues: List[QualityIssue]
    recommendations: List[str]
    quality_level: QualityLevel
    improvement_suggestions: Dict[str, List[str]]
    analysis_summary: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'metrics': self.metrics.to_dict(),
            'issues': [issue.to_dict() for issue in self.issues],
            'recommendations': self.recommendations,
            'quality_level': self.quality_level.value,
            'improvement_suggestions': self.improvement_suggestions,
            'analysis_summary': self.analysis_summary,
            'timestamp': self.timestamp.isoformat()
        }

class MaintainabilityAnalyzer:
    """Analyzer for code maintainability"""
    
    def analyze_maintainability(self, code: str, ast_result: ParseResult, 
                              complexity_metrics: ComplexityMetrics) -> Tuple[float, List[QualityIssue]]:
        """Analyze code maintainability"""
        issues = []
        score = 100.0
        
        # Function length analysis
        function_issues, length_penalty = self._analyze_function_length(code, ast_result)
        issues.extend(function_issues)
        score -= length_penalty
        
        # Complexity analysis
        complexity_issues, complexity_penalty = self._analyze_complexity_impact(complexity_metrics)
        issues.extend(complexity_issues)
        score -= complexity_penalty
        
        # Coupling analysis
        coupling_issues, coupling_penalty = self._analyze_coupling(code, ast_result)
        issues.extend(coupling_issues)
        score -= coupling_penalty
        
        # Cohesion analysis
        cohesion_issues, cohesion_penalty = self._analyze_cohesion(code, ast_result)
        issues.extend(cohesion_issues)
        score -= cohesion_penalty
        
        return max(0, score), issues
    
    def _analyze_function_length(self, code: str, ast_result: ParseResult) -> Tuple[List[QualityIssue], float]:
        """Analyze function length for maintainability"""
        issues = []
        penalty = 0
        
        if not ast_result.success or not ast_result.ast_tree:
            return issues, penalty
        
        functions = self._find_functions(ast_result.ast_tree)
        
        for func in functions:
            length = func.line_end - func.line_start + 1
            
            if length > 50:
                severity = QualityLevel.POOR if length > 100 else QualityLevel.FAIR
                impact = min(100, length * 0.8)
                
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.LONG_FUNCTION,
                    dimension=QualityDimension.MAINTAINABILITY,
                    severity=severity,
                    title=f"Long Function: {func.name or 'unnamed'}",
                    description=f"Function is {length} lines long, which may be difficult to maintain.",
                    line_start=func.line_start,
                    line_end=func.line_end,
                    impact_score=impact,
                    recommendation="Break down long functions into smaller, focused functions.",
                    evidence={'function_length': length, 'function_name': func.name}
                ))
                
                penalty += min(20, length * 0.2)
        
        return issues, penalty
    
    def _analyze_complexity_impact(self, complexity_metrics: ComplexityMetrics) -> Tuple[List[QualityIssue], float]:
        """Analyze complexity impact on maintainability"""
        issues = []
        penalty = 0
        
        # High cyclomatic complexity
        if complexity_metrics.cyclomatic_complexity > 10:
            severity = QualityLevel.POOR if complexity_metrics.cyclomatic_complexity > 20 else QualityLevel.FAIR
            impact = min(100, complexity_metrics.cyclomatic_complexity * 4)
            
            issues.append(QualityIssue(
                issue_type=QualityIssueType.DEEP_NESTING,
                dimension=QualityDimension.MAINTAINABILITY,
                severity=severity,
                title="High Cyclomatic Complexity",
                description=f"Cyclomatic complexity of {complexity_metrics.cyclomatic_complexity} makes code hard to maintain.",
                line_start=1,
                line_end=1,
                impact_score=impact,
                recommendation="Reduce complexity by extracting methods and simplifying control flow.",
                evidence={'cyclomatic_complexity': complexity_metrics.cyclomatic_complexity}
            ))
            
            penalty += min(30, complexity_metrics.cyclomatic_complexity * 1.5)
        
        # Low maintainability index
        if complexity_metrics.maintainability_index < 50:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.POOR_SEPARATION,
                dimension=QualityDimension.MAINTAINABILITY,
                severity=QualityLevel.FAIR,
                title="Low Maintainability Index",
                description=f"Maintainability index of {complexity_metrics.maintainability_index:.1f} indicates potential maintenance issues.",
                line_start=1,
                line_end=1,
                impact_score=100 - complexity_metrics.maintainability_index,
                recommendation="Improve code structure, reduce complexity, and enhance documentation.",
                evidence={'maintainability_index': complexity_metrics.maintainability_index}
            ))
            
            penalty += (50 - complexity_metrics.maintainability_index) * 0.5
        
        return issues, penalty
    
    def _analyze_coupling(self, code: str, ast_result: ParseResult) -> Tuple[List[QualityIssue], float]:
        """Analyze coupling between components"""
        issues = []
        penalty = 0
        
        # Count imports and dependencies
        import_count = len(re.findall(r'^\s*(import|from)\s+', code, re.MULTILINE))
        
        if import_count > 20:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.POOR_SEPARATION,
                dimension=QualityDimension.MAINTAINABILITY,
                severity=QualityLevel.FAIR,
                title="High Coupling",
                description=f"File has {import_count} imports, indicating high coupling.",
                line_start=1,
                line_end=1,
                impact_score=min(100, import_count * 3),
                recommendation="Consider reducing dependencies and improving module separation.",
                evidence={'import_count': import_count}
            ))
            
            penalty += min(15, (import_count - 20) * 0.5)
        
        return issues, penalty
    
    def _analyze_cohesion(self, code: str, ast_result: ParseResult) -> Tuple[List[QualityIssue], float]:
        """Analyze cohesion within modules"""
        issues = []
        penalty = 0
        
        # Simple cohesion analysis based on function relationships
        if ast_result.success and ast_result.ast_tree:
            functions = self._find_functions(ast_result.ast_tree)
            
            if len(functions) > 10:
                # Check if functions seem related (simplified analysis)
                function_names = [f.name for f in functions if f.name]
                
                # Look for common prefixes or patterns
                common_patterns = self._find_common_patterns(function_names)
                
                if len(common_patterns) < len(function_names) * 0.3:
                    issues.append(QualityIssue(
                        issue_type=QualityIssueType.POOR_SEPARATION,
                        dimension=QualityDimension.MAINTAINABILITY,
                        severity=QualityLevel.FAIR,
                        title="Low Cohesion",
                        description="Functions in this module may not be closely related.",
                        line_start=1,
                        line_end=1,
                        impact_score=40,
                        recommendation="Consider splitting this module into more focused, cohesive modules.",
                        evidence={'function_count': len(functions), 'common_patterns': len(common_patterns)}
                    ))
                    
                    penalty += 10
        
        return issues, penalty
    
    def _find_functions(self, ast_tree: ASTNode) -> List[ASTNode]:
        """Find all functions in AST"""
        functions = []
        
        def traverse(node: ASTNode):
            if node.node_type in ['function', 'method', 'function_definition']:
                functions.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(ast_tree)
        return functions
    
    def _find_common_patterns(self, names: List[str]) -> Set[str]:
        """Find common patterns in function names"""
        patterns = set()
        
        for name in names:
            if '_' in name:
                prefix = name.split('_')[0]
                if len(prefix) > 2:
                    patterns.add(prefix)
            
            # CamelCase patterns
            camel_parts = re.findall(r'[A-Z][a-z]*', name)
            if camel_parts:
                patterns.add(camel_parts[0].lower())
        
        return patterns

class ReadabilityAnalyzer:
    """Analyzer for code readability"""
    
    def analyze_readability(self, code: str, ast_result: ParseResult) -> Tuple[float, List[QualityIssue]]:
        """Analyze code readability"""
        issues = []
        score = 100.0
        
        # Naming convention analysis
        naming_issues, naming_penalty = self._analyze_naming_conventions(code, ast_result)
        issues.extend(naming_issues)
        score -= naming_penalty
        
        # Documentation analysis
        doc_issues, doc_penalty = self._analyze_documentation(code, ast_result)
        issues.extend(doc_issues)
        score -= doc_penalty
        
        # Magic numbers analysis
        magic_issues, magic_penalty = self._analyze_magic_numbers(code)
        issues.extend(magic_issues)
        score -= magic_penalty
        
        # Comment quality analysis
        comment_issues, comment_penalty = self._analyze_comments(code)
        issues.extend(comment_issues)
        score -= comment_penalty
        
        return max(0, score), issues
    
    def _analyze_naming_conventions(self, code: str, ast_result: ParseResult) -> Tuple[List[QualityIssue], float]:
        """Analyze naming conventions"""
        issues = []
        penalty = 0
        
        # Check variable names
        var_names = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', code)
        
        for var_name in var_names:
            if len(var_name) < 3 and var_name not in ['i', 'j', 'k', 'x', 'y', 'z']:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.NAMING_CONVENTION,
                    dimension=QualityDimension.READABILITY,
                    severity=QualityLevel.FAIR,
                    title=f"Short Variable Name: {var_name}",
                    description=f"Variable '{var_name}' has a very short name that may not be descriptive.",
                    line_start=1,
                    line_end=1,
                    impact_score=20,
                    recommendation="Use more descriptive variable names.",
                    evidence={'variable_name': var_name}
                ))
                penalty += 2
        
        # Check function names
        if ast_result.success and ast_result.ast_tree:
            functions = self._find_functions(ast_result.ast_tree)
            
            for func in functions:
                if func.name and not re.match(r'^[a-z_][a-z0-9_]*$', func.name):
                    issues.append(QualityIssue(
                        issue_type=QualityIssueType.NAMING_CONVENTION,
                        dimension=QualityDimension.READABILITY,
                        severity=QualityLevel.FAIR,
                        title=f"Non-standard Function Name: {func.name}",
                        description=f"Function '{func.name}' doesn't follow snake_case convention.",
                        line_start=func.line_start,
                        line_end=func.line_end,
                        impact_score=15,
                        recommendation="Use snake_case for function names.",
                        evidence={'function_name': func.name}
                    ))
                    penalty += 3
        
        return issues, penalty
    
    def _analyze_documentation(self, code: str, ast_result: ParseResult) -> Tuple[List[QualityIssue], float]:
        """Analyze documentation quality"""
        issues = []
        penalty = 0
        
        # Count docstrings
        docstring_count = len(re.findall(r'"""[^"]*"""', code, re.DOTALL))
        docstring_count += len(re.findall(r"'''[^']*'''", code, re.DOTALL))
        
        # Count functions
        function_count = len(re.findall(r'def\s+\w+\s*\(', code))
        
        if function_count > 0:
            doc_ratio = docstring_count / function_count
            
            if doc_ratio < 0.5:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.MISSING_DOCUMENTATION,
                    dimension=QualityDimension.READABILITY,
                    severity=QualityLevel.FAIR,
                    title="Insufficient Documentation",
                    description=f"Only {doc_ratio:.1%} of functions have docstrings.",
                    line_start=1,
                    line_end=1,
                    impact_score=50 * (1 - doc_ratio),
                    recommendation="Add docstrings to functions to improve code documentation.",
                    evidence={'doc_ratio': doc_ratio, 'function_count': function_count}
                ))
                penalty += 20 * (1 - doc_ratio)
        
        return issues, penalty
    
    def _analyze_magic_numbers(self, code: str) -> Tuple[List[QualityIssue], float]:
        """Analyze magic numbers in code"""
        issues = []
        penalty = 0
        
        # Find numeric literals (excluding common ones like 0, 1, -1)
        magic_numbers = re.findall(r'\b(?<!\.)(?:[2-9]|[1-9]\d+)(?!\.\d)\b', code)
        
        if len(magic_numbers) > 5:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.MAGIC_NUMBERS,
                dimension=QualityDimension.READABILITY,
                severity=QualityLevel.FAIR,
                title="Magic Numbers Detected",
                description=f"Found {len(magic_numbers)} magic numbers that should be named constants.",
                line_start=1,
                line_end=1,
                impact_score=min(50, len(magic_numbers) * 3),
                recommendation="Replace magic numbers with named constants.",
                evidence={'magic_number_count': len(magic_numbers)}
            ))
            penalty += min(15, len(magic_numbers) * 1.5)
        
        return issues, penalty
    
    def _analyze_comments(self, code: str) -> Tuple[List[QualityIssue], float]:
        """Analyze comment quality"""
        issues = []
        penalty = 0
        
        # Count comments
        comment_lines = len(re.findall(r'^\s*#', code, re.MULTILINE))
        total_lines = len([line for line in code.split('\n') if line.strip()])
        
        if total_lines > 0:
            comment_ratio = comment_lines / total_lines
            
            # Too few comments
            if comment_ratio < 0.1 and total_lines > 50:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.MISSING_DOCUMENTATION,
                    dimension=QualityDimension.READABILITY,
                    severity=QualityLevel.FAIR,
                    title="Insufficient Comments",
                    description=f"Only {comment_ratio:.1%} of lines are comments.",
                    line_start=1,
                    line_end=1,
                    impact_score=30,
                    recommendation="Add more explanatory comments to improve code readability.",
                    evidence={'comment_ratio': comment_ratio}
                ))
                penalty += 10
            
            # Too many comments (might indicate unclear code)
            elif comment_ratio > 0.3:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.INCONSISTENT_STYLE,
                    dimension=QualityDimension.READABILITY,
                    severity=QualityLevel.FAIR,
                    title="Excessive Comments",
                    description=f"{comment_ratio:.1%} of lines are comments, which might indicate unclear code.",
                    line_start=1,
                    line_end=1,
                    impact_score=20,
                    recommendation="Consider simplifying code to reduce the need for extensive comments.",
                    evidence={'comment_ratio': comment_ratio}
                ))
                penalty += 5
        
        return issues, penalty
    
    def _find_functions(self, ast_tree: ASTNode) -> List[ASTNode]:
        """Find all functions in AST"""
        functions = []
        
        def traverse(node: ASTNode):
            if node.node_type in ['function', 'method', 'function_definition']:
                functions.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(ast_tree)
        return functions

class TestabilityAnalyzer:
    """Analyzer for code testability"""
    
    def analyze_testability(self, code: str, ast_result: ParseResult) -> Tuple[float, List[QualityIssue]]:
        """Analyze code testability"""
        issues = []
        score = 100.0
        
        # Function complexity for testing
        complexity_issues, complexity_penalty = self._analyze_test_complexity(code, ast_result)
        issues.extend(complexity_issues)
        score -= complexity_penalty
        
        # Dependency analysis
        dependency_issues, dependency_penalty = self._analyze_dependencies(code)
        issues.extend(dependency_issues)
        score -= dependency_penalty
        
        # Error handling analysis
        error_issues, error_penalty = self._analyze_error_handling(code)
        issues.extend(error_issues)
        score -= error_penalty
        
        return max(0, score), issues
    
    def _analyze_test_complexity(self, code: str, ast_result: ParseResult) -> Tuple[List[QualityIssue], float]:
        """Analyze complexity impact on testability"""
        issues = []
        penalty = 0
        
        if ast_result.success and ast_result.ast_tree:
            functions = self._find_functions(ast_result.ast_tree)
            
            for func in functions:
                # Count parameters
                param_count = len(func.attributes.get('args', []))
                
                if param_count > 5:
                    issues.append(QualityIssue(
                        issue_type=QualityIssueType.POOR_SEPARATION,
                        dimension=QualityDimension.TESTABILITY,
                        severity=QualityLevel.FAIR,
                        title=f"Too Many Parameters: {func.name or 'unnamed'}",
                        description=f"Function has {param_count} parameters, making it hard to test.",
                        line_start=func.line_start,
                        line_end=func.line_end,
                        impact_score=min(80, param_count * 10),
                        recommendation="Reduce parameter count by using objects or breaking down the function.",
                        evidence={'parameter_count': param_count, 'function_name': func.name}
                    ))
                    penalty += min(15, (param_count - 5) * 2)
        
        return issues, penalty
    
    def _analyze_dependencies(self, code: str) -> Tuple[List[QualityIssue], float]:
        """Analyze external dependencies impact on testability"""
        issues = []
        penalty = 0
        
        # Look for hard-to-test patterns
        hard_patterns = {
            'file_operations': r'open\s*\(',
            'network_calls': r'requests\.|urllib\.|http\.',
            'database_calls': r'\.(execute|query|commit)\(',
            'system_calls': r'os\.|subprocess\.',
            'datetime_now': r'datetime\.now\(\)|time\.time\(\)'
        }
        
        for pattern_name, pattern in hard_patterns.items():
            matches = re.findall(pattern, code)
            
            if len(matches) > 3:
                issues.append(QualityIssue(
                    issue_type=QualityIssueType.POOR_SEPARATION,
                    dimension=QualityDimension.TESTABILITY,
                    severity=QualityLevel.FAIR,
                    title=f"Hard-to-Test Dependencies: {pattern_name}",
                    description=f"Found {len(matches)} instances of {pattern_name} that may be hard to test.",
                    line_start=1,
                    line_end=1,
                    impact_score=min(60, len(matches) * 8),
                    recommendation="Consider dependency injection or mocking for better testability.",
                    evidence={'pattern': pattern_name, 'count': len(matches)}
                ))
                penalty += min(10, len(matches) * 2)
        
        return issues, penalty
    
    def _analyze_error_handling(self, code: str) -> Tuple[List[QualityIssue], float]:
        """Analyze error handling for testability"""
        issues = []
        penalty = 0
        
        # Count try-except blocks
        try_blocks = len(re.findall(r'try\s*:', code))
        
        # Count functions that might need error handling
        risky_operations = len(re.findall(r'(open\(|requests\.|\[.*\]|\w+\.\w+\()', code))
        
        if risky_operations > 5 and try_blocks == 0:
            issues.append(QualityIssue(
                issue_type=QualityIssueType.MISSING_ERROR_HANDLING,
                dimension=QualityDimension.TESTABILITY,
                severity=QualityLevel.FAIR,
                title="Missing Error Handling",
                description="Code has risky operations but no error handling, making it hard to test edge cases.",
                line_start=1,
                line_end=1,
                impact_score=40,
                recommendation="Add appropriate error handling to improve testability and reliability.",
                evidence={'risky_operations': risky_operations, 'try_blocks': try_blocks}
            ))
            penalty += 15
        
        return issues, penalty
    
    def _find_functions(self, ast_tree: ASTNode) -> List[ASTNode]:
        """Find all functions in AST"""
        functions = []
        
        def traverse(node: ASTNode):
            if node.node_type in ['function', 'method', 'function_definition']:
                functions.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(ast_tree)
        return functions

class QualityAssessorEngine:
    """Main quality assessor engine"""
    
    def __init__(self):
        self.maintainability_analyzer = MaintainabilityAnalyzer()
        self.readability_analyzer = ReadabilityAnalyzer()
        self.testability_analyzer = TestabilityAnalyzer()
    
    def assess_quality(self, code: str, filename: str = "", 
                      ast_result: Optional[ParseResult] = None,
                      complexity_metrics: Optional[ComplexityMetrics] = None) -> QualityAssessmentResult:
        """Perform comprehensive quality assessment"""
        try:
            # Parse AST if not provided
            if ast_result is None:
                from .ast_parser import parse_code
                ast_result = parse_code(code, filename)
            
            # Get complexity metrics if not provided
            if complexity_metrics is None:
                from .performance_analyzer import ComplexityAnalyzer
                complexity_analyzer = ComplexityAnalyzer()
                complexity_metrics = complexity_analyzer.analyze_complexity(code, ast_result)
            
            # Analyze different quality dimensions
            maintainability_score, maintainability_issues = self.maintainability_analyzer.analyze_maintainability(
                code, ast_result, complexity_metrics
            )
            
            readability_score, readability_issues = self.readability_analyzer.analyze_readability(
                code, ast_result
            )
            
            testability_score, testability_issues = self.testability_analyzer.analyze_testability(
                code, ast_result
            )
            
            # Combine all issues
            all_issues = maintainability_issues + readability_issues + testability_issues
            
            # Calculate overall metrics
            quality_metrics = self._calculate_quality_metrics(
                maintainability_score, readability_score, testability_score,
                complexity_metrics, all_issues
            )
            
            # Determine overall quality level
            quality_level = self._determine_quality_level(quality_metrics.overall_score)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(all_issues, quality_metrics)
            
            # Create improvement suggestions
            improvement_suggestions = self._create_improvement_suggestions(all_issues)
            
            # Create analysis summary
            analysis_summary = self._create_analysis_summary(code, ast_result, all_issues)
            
            return QualityAssessmentResult(
                metrics=quality_metrics,
                issues=all_issues,
                recommendations=recommendations,
                quality_level=quality_level,
                improvement_suggestions=improvement_suggestions,
                analysis_summary=analysis_summary
            )
            
        except Exception as e:
            logger.error(f"Error in quality assessment: {str(e)}")
            return QualityAssessmentResult(
                metrics=QualityMetrics(
                    overall_score=0,
                    maintainability_score=0,
                    readability_score=0,
                    testability_score=0,
                    reliability_score=0,
                    documentation_score=0,
                    style_consistency_score=0,
                    technical_debt_ratio=1.0,
                    code_coverage_estimate=0
                ),
                issues=[],
                recommendations=[],
                quality_level=QualityLevel.CRITICAL,
                improvement_suggestions={},
                analysis_summary={'error': str(e)}
            )
    
    def _calculate_quality_metrics(self, maintainability_score: float, readability_score: float,
                                 testability_score: float, complexity_metrics: ComplexityMetrics,
                                 issues: List[QualityIssue]) -> QualityMetrics:
        """Calculate overall quality metrics"""
        # Calculate dimension scores
        reliability_score = max(0, 100 - len([i for i in issues if i.dimension == QualityDimension.RELIABILITY]) * 15)
        
        # Documentation score based on readability issues
        doc_issues = [i for i in issues if i.issue_type == QualityIssueType.MISSING_DOCUMENTATION]
        documentation_score = max(0, 100 - len(doc_issues) * 20)
        
        # Style consistency score
        style_issues = [i for i in issues if i.issue_type in [QualityIssueType.NAMING_CONVENTION, QualityIssueType.INCONSISTENT_STYLE]]
        style_consistency_score = max(0, 100 - len(style_issues) * 10)
        
        # Overall score (weighted average)
        overall_score = (
            maintainability_score * 0.3 +
            readability_score * 0.25 +
            testability_score * 0.2 +
            reliability_score * 0.15 +
            documentation_score * 0.1
        )
        
        # Technical debt ratio
        high_impact_issues = [i for i in issues if i.impact_score > 50]
        technical_debt_ratio = min(1.0, len(high_impact_issues) * 0.1)
        
        # Code coverage estimate (simplified)
        test_issues = [i for i in issues if i.dimension == QualityDimension.TESTABILITY]
        code_coverage_estimate = max(0, 80 - len(test_issues) * 10)
        
        return QualityMetrics(
            overall_score=overall_score,
            maintainability_score=maintainability_score,
            readability_score=readability_score,
            testability_score=testability_score,
            reliability_score=reliability_score,
            documentation_score=documentation_score,
            style_consistency_score=style_consistency_score,
            technical_debt_ratio=technical_debt_ratio,
            code_coverage_estimate=code_coverage_estimate
        )
    
    def _determine_quality_level(self, overall_score: float) -> QualityLevel:
        """Determine overall quality level"""
        if overall_score >= 80:
            return QualityLevel.EXCELLENT
        elif overall_score >= 60:
            return QualityLevel.GOOD
        elif overall_score >= 40:
            return QualityLevel.FAIR
        elif overall_score >= 20:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def _generate_recommendations(self, issues: List[QualityIssue], 
                                metrics: QualityMetrics) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        # Add top issue recommendations
        sorted_issues = sorted(issues, key=lambda x: x.impact_score, reverse=True)
        for issue in sorted_issues[:5]:
            recommendations.append(issue.recommendation)
        
        # Add metric-based recommendations
        if metrics.maintainability_score < 60:
            recommendations.append("Focus on improving code maintainability by reducing complexity and improving structure.")
        
        if metrics.readability_score < 60:
            recommendations.append("Improve code readability with better naming, documentation, and formatting.")
        
        if metrics.testability_score < 60:
            recommendations.append("Enhance testability by reducing dependencies and improving error handling.")
        
        if metrics.technical_debt_ratio > 0.3:
            recommendations.append("Address technical debt by refactoring problematic code areas.")
        
        # Remove duplicates
        return list(dict.fromkeys(recommendations))
    
    def _create_improvement_suggestions(self, issues: List[QualityIssue]) -> Dict[str, List[str]]:
        """Create categorized improvement suggestions"""
        suggestions = {
            'immediate': [],
            'short_term': [],
            'long_term': []
        }
        
        for issue in issues:
            if issue.severity in [QualityLevel.CRITICAL, QualityLevel.POOR]:
                suggestions['immediate'].append(issue.recommendation)
            elif issue.severity == QualityLevel.FAIR:
                suggestions['short_term'].append(issue.recommendation)
            else:
                suggestions['long_term'].append(issue.recommendation)
        
        # Remove duplicates
        for category in suggestions:
            suggestions[category] = list(dict.fromkeys(suggestions[category]))
        
        return suggestions
    
    def _create_analysis_summary(self, code: str, ast_result: ParseResult, 
                               issues: List[QualityIssue]) -> Dict[str, Any]:
        """Create summary of quality analysis"""
        lines_of_code = len([line for line in code.split('\n') if line.strip()])
        
        issue_by_dimension = {}
        for dimension in QualityDimension:
            issue_by_dimension[dimension.value] = len([i for i in issues if i.dimension == dimension])
        
        return {
            'lines_of_code': lines_of_code,
            'language': ast_result.language.value if ast_result.success else 'unknown',
            'total_issues': len(issues),
            'issues_by_dimension': issue_by_dimension,
            'critical_issues': len([i for i in issues if i.severity == QualityLevel.CRITICAL]),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

# Global assessor instance
quality_assessor = QualityAssessorEngine()

# Convenience functions
def assess_code_quality(code: str, filename: str = "") -> QualityAssessmentResult:
    """Assess code quality"""
    return quality_assessor.assess_quality(code, filename)

def get_quality_score(code: str, filename: str = "") -> float:
    """Get overall quality score (0-100)"""
    result = assess_code_quality(code, filename)
    return result.metrics.overall_score