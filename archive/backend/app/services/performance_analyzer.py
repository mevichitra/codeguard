#!/usr/bin/env python3
"""
CodeGuard AI - Performance Analysis Module

Analyzes code performance characteristics including complexity metrics,
efficiency patterns, and potential performance bottlenecks.
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

# Configure logging
logger = logging.getLogger(__name__)

class PerformanceIssueType(Enum):
    """Types of performance issues"""
    HIGH_COMPLEXITY = "high_complexity"
    INEFFICIENT_LOOP = "inefficient_loop"
    MEMORY_LEAK = "memory_leak"
    BLOCKING_OPERATION = "blocking_operation"
    REDUNDANT_COMPUTATION = "redundant_computation"
    INEFFICIENT_DATA_STRUCTURE = "inefficient_data_structure"
    EXCESSIVE_RECURSION = "excessive_recursion"
    UNOPTIMIZED_QUERY = "unoptimized_query"
    LARGE_OBJECT_CREATION = "large_object_creation"
    SYNCHRONOUS_IO = "synchronous_io"

class PerformanceLevel(Enum):
    """Performance impact levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

@dataclass
class PerformanceIssue:
    """Performance issue information"""
    issue_type: PerformanceIssueType
    severity: PerformanceLevel
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
        return asdict(self)

@dataclass
class ComplexityMetrics:
    """Advanced complexity metrics"""
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    halstead_difficulty: float = 0.0
    halstead_effort: float = 0.0
    maintainability_index: float = 0.0
    nesting_depth: int = 0
    function_length: int = 0
    parameter_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PerformanceMetrics:
    """Performance analysis metrics"""
    overall_score: float  # 0-100
    complexity_metrics: ComplexityMetrics
    performance_level: PerformanceLevel
    bottleneck_count: int
    optimization_potential: float  # 0-100
    estimated_execution_time: str
    memory_usage_estimate: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_score': self.overall_score,
            'complexity_metrics': self.complexity_metrics.to_dict(),
            'performance_level': self.performance_level.value,
            'bottleneck_count': self.bottleneck_count,
            'optimization_potential': self.optimization_potential,
            'estimated_execution_time': self.estimated_execution_time,
            'memory_usage_estimate': self.memory_usage_estimate
        }

@dataclass
class PerformanceAnalysisResult:
    """Result of performance analysis"""
    metrics: PerformanceMetrics
    issues: List[PerformanceIssue]
    recommendations: List[str]
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
            'analysis_summary': self.analysis_summary,
            'timestamp': self.timestamp.isoformat()
        }

class ComplexityAnalyzer:
    """Analyzer for code complexity metrics"""
    
    def analyze_complexity(self, code: str, ast_result: ParseResult) -> ComplexityMetrics:
        """Analyze code complexity using multiple metrics"""
        if not ast_result.success or not ast_result.ast_tree:
            return ComplexityMetrics()
        
        metrics = ComplexityMetrics()
        
        # Basic metrics from AST parser
        if ast_result.metrics:
            metrics.cyclomatic_complexity = ast_result.metrics.cyclomatic_complexity
            metrics.nesting_depth = ast_result.metrics.nesting_depth
        
        # Calculate advanced metrics
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(ast_result.ast_tree)
        halstead_metrics = self._calculate_halstead_metrics(code)
        metrics.halstead_difficulty = halstead_metrics.get('difficulty', 0)
        metrics.halstead_effort = halstead_metrics.get('effort', 0)
        metrics.maintainability_index = self._calculate_maintainability_index(code, metrics)
        
        # Function-specific metrics
        function_metrics = self._analyze_function_complexity(ast_result.ast_tree)
        metrics.function_length = function_metrics.get('avg_length', 0)
        metrics.parameter_count = function_metrics.get('avg_parameters', 0)
        
        return metrics
    
    def _calculate_cognitive_complexity(self, ast_tree: ASTNode) -> int:
        """Calculate cognitive complexity (more human-oriented than cyclomatic)"""
        complexity = 0
        
        def traverse(node: ASTNode, nesting_level: int = 0):
            nonlocal complexity
            
            # Base complexity for control structures
            if node.node_type in ['if', 'elif', 'while', 'for', 'try', 'except']:
                complexity += 1 + nesting_level
                nesting_level += 1
            elif node.node_type in ['and', 'or']:
                complexity += 1
            elif node.node_type in ['break', 'continue']:
                complexity += 1
            elif node.node_type == 'lambda':
                complexity += 1
            
            # Recursively analyze children
            for child in node.children:
                traverse(child, nesting_level)
        
        traverse(ast_tree)
        return complexity
    
    def _calculate_halstead_metrics(self, code: str) -> Dict[str, float]:
        """Calculate Halstead complexity metrics"""
        # Simplified Halstead metrics calculation
        operators = re.findall(r'[+\-*/=<>!&|^%]+|\b(and|or|not|in|is)\b', code)
        operands = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b|\b\d+\b', code)
        
        n1 = len(set(operators))  # Unique operators
        n2 = len(set(operands))   # Unique operands
        N1 = len(operators)       # Total operators
        N2 = len(operands)        # Total operands
        
        if n1 == 0 or n2 == 0:
            return {'difficulty': 0, 'effort': 0}
        
        vocabulary = n1 + n2
        length = N1 + N2
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0
        effort = difficulty * length
        
        return {
            'difficulty': difficulty,
            'effort': effort,
            'vocabulary': vocabulary,
            'length': length
        }
    
    def _calculate_maintainability_index(self, code: str, metrics: ComplexityMetrics) -> float:
        """Calculate maintainability index (0-100)"""
        lines_of_code = len([line for line in code.split('\n') if line.strip()])
        
        if lines_of_code == 0:
            return 100
        
        # Simplified maintainability index calculation
        # MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)
        # Where HV = Halstead Volume, CC = Cyclomatic Complexity, LOC = Lines of Code
        
        halstead_volume = max(metrics.halstead_effort, 1)
        cyclomatic = max(metrics.cyclomatic_complexity, 1)
        loc = max(lines_of_code, 1)
        
        mi = 171 - 5.2 * np.log(halstead_volume) - 0.23 * cyclomatic - 16.2 * np.log(loc)
        
        # Normalize to 0-100 scale
        return max(0, min(100, mi))
    
    def _analyze_function_complexity(self, ast_tree: ASTNode) -> Dict[str, float]:
        """Analyze function-specific complexity metrics"""
        functions = []
        
        def find_functions(node: ASTNode):
            if node.node_type in ['function', 'method', 'function_definition']:
                functions.append(node)
            
            for child in node.children:
                find_functions(child)
        
        find_functions(ast_tree)
        
        if not functions:
            return {'avg_length': 0, 'avg_parameters': 0}
        
        total_length = sum(func.line_end - func.line_start + 1 for func in functions)
        total_params = sum(len(func.attributes.get('args', [])) for func in functions)
        
        return {
            'avg_length': total_length / len(functions),
            'avg_parameters': total_params / len(functions),
            'function_count': len(functions)
        }

class PerformanceIssueDetector:
    """Detector for performance issues and bottlenecks"""
    
    def __init__(self):
        self.inefficient_patterns = {
            'nested_loops': r'for\s+.*:\s*\n\s*for\s+.*:',
            'string_concatenation': r'\+\s*["\'].*["\']\s*\+',
            'list_append_loop': r'for\s+.*:\s*\n\s*.*\.append\(',
            'dict_get_loop': r'for\s+.*:\s*\n\s*.*\[.*\]',
            'regex_in_loop': r'for\s+.*:\s*\n\s*.*re\.',
            'file_io_loop': r'for\s+.*:\s*\n\s*.*open\(',
            'database_query_loop': r'for\s+.*:\s*\n\s*.*execute\(',
            'synchronous_requests': r'requests\.(get|post|put|delete)\(',
            'blocking_sleep': r'time\.sleep\(',
            'inefficient_sort': r'\.sort\(.*key=lambda.*\)'
        }
        
        self.memory_patterns = {
            'large_list_creation': r'\[.*\]\s*\*\s*\d{4,}',
            'global_variables': r'^\s*[A-Z_][A-Z0-9_]*\s*=',
            'circular_references': r'self\.[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*self',
            'unclosed_files': r'open\([^)]*\)(?!.*\.close\(\))',
            'memory_intensive_ops': r'\.(join|split|replace)\([^)]*\)'
        }
    
    def detect_issues(self, code: str, ast_result: ParseResult, 
                     complexity_metrics: ComplexityMetrics) -> List[PerformanceIssue]:
        """Detect performance issues in code"""
        issues = []
        
        # Complexity-based issues
        issues.extend(self._detect_complexity_issues(complexity_metrics))
        
        # Pattern-based issues
        issues.extend(self._detect_inefficient_patterns(code))
        issues.extend(self._detect_memory_issues(code))
        
        # AST-based issues
        if ast_result.success and ast_result.ast_tree:
            issues.extend(self._detect_structural_issues(ast_result.ast_tree))
        
        return issues
    
    def _detect_complexity_issues(self, metrics: ComplexityMetrics) -> List[PerformanceIssue]:
        """Detect issues based on complexity metrics"""
        issues = []
        
        # High cyclomatic complexity
        if metrics.cyclomatic_complexity > 15:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.HIGH_COMPLEXITY,
                severity=PerformanceLevel.POOR,
                title="High Cyclomatic Complexity",
                description=f"Cyclomatic complexity is {metrics.cyclomatic_complexity}, which is very high.",
                line_start=1,
                line_end=1,
                impact_score=min(100, metrics.cyclomatic_complexity * 5),
                recommendation="Break down complex functions into smaller, more manageable pieces.",
                evidence={'cyclomatic_complexity': metrics.cyclomatic_complexity}
            ))
        
        # High cognitive complexity
        if metrics.cognitive_complexity > 20:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.HIGH_COMPLEXITY,
                severity=PerformanceLevel.POOR,
                title="High Cognitive Complexity",
                description=f"Cognitive complexity is {metrics.cognitive_complexity}, making code hard to understand.",
                line_start=1,
                line_end=1,
                impact_score=min(100, metrics.cognitive_complexity * 4),
                recommendation="Simplify control flow and reduce nesting levels.",
                evidence={'cognitive_complexity': metrics.cognitive_complexity}
            ))
        
        # Deep nesting
        if metrics.nesting_depth > 5:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.HIGH_COMPLEXITY,
                severity=PerformanceLevel.FAIR,
                title="Deep Nesting",
                description=f"Maximum nesting depth is {metrics.nesting_depth}, which is too deep.",
                line_start=1,
                line_end=1,
                impact_score=metrics.nesting_depth * 15,
                recommendation="Reduce nesting by using early returns or extracting functions.",
                evidence={'nesting_depth': metrics.nesting_depth}
            ))
        
        # Long functions
        if metrics.function_length > 50:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.HIGH_COMPLEXITY,
                severity=PerformanceLevel.FAIR,
                title="Long Function",
                description=f"Average function length is {metrics.function_length:.1f} lines, which is too long.",
                line_start=1,
                line_end=1,
                impact_score=min(100, metrics.function_length * 2),
                recommendation="Break long functions into smaller, focused functions.",
                evidence={'function_length': metrics.function_length}
            ))
        
        return issues
    
    def _detect_inefficient_patterns(self, code: str) -> List[PerformanceIssue]:
        """Detect inefficient coding patterns"""
        issues = []
        
        for pattern_name, pattern in self.inefficient_patterns.items():
            matches = list(re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE))
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                issue_info = self._get_pattern_issue_info(pattern_name, match.group())
                
                issues.append(PerformanceIssue(
                    issue_type=issue_info['type'],
                    severity=issue_info['severity'],
                    title=issue_info['title'],
                    description=issue_info['description'],
                    line_start=line_num,
                    line_end=line_num,
                    impact_score=issue_info['impact_score'],
                    recommendation=issue_info['recommendation'],
                    evidence={'pattern': pattern_name, 'match': match.group()}
                ))
        
        return issues
    
    def _detect_memory_issues(self, code: str) -> List[PerformanceIssue]:
        """Detect memory-related performance issues"""
        issues = []
        
        for pattern_name, pattern in self.memory_patterns.items():
            matches = list(re.finditer(pattern, code, re.MULTILINE | re.IGNORECASE))
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                issue_info = self._get_memory_issue_info(pattern_name, match.group())
                
                issues.append(PerformanceIssue(
                    issue_type=PerformanceIssueType.MEMORY_LEAK,
                    severity=issue_info['severity'],
                    title=issue_info['title'],
                    description=issue_info['description'],
                    line_start=line_num,
                    line_end=line_num,
                    impact_score=issue_info['impact_score'],
                    recommendation=issue_info['recommendation'],
                    evidence={'pattern': pattern_name, 'match': match.group()}
                ))
        
        return issues
    
    def _detect_structural_issues(self, ast_tree: ASTNode) -> List[PerformanceIssue]:
        """Detect structural performance issues from AST"""
        issues = []
        
        # Detect excessive recursion
        recursive_functions = self._find_recursive_functions(ast_tree)
        for func in recursive_functions:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.EXCESSIVE_RECURSION,
                severity=PerformanceLevel.FAIR,
                title="Potential Excessive Recursion",
                description=f"Function '{func.name}' appears to be recursive without obvious base case.",
                line_start=func.line_start,
                line_end=func.line_end,
                impact_score=60,
                recommendation="Ensure proper base cases and consider iterative alternatives for deep recursion.",
                evidence={'function_name': func.name}
            ))
        
        return issues
    
    def _get_pattern_issue_info(self, pattern_name: str, match: str) -> Dict[str, Any]:
        """Get issue information for inefficient patterns"""
        pattern_info = {
            'nested_loops': {
                'type': PerformanceIssueType.INEFFICIENT_LOOP,
                'severity': PerformanceLevel.POOR,
                'title': 'Nested Loops Detected',
                'description': 'Nested loops can lead to O(n²) or worse time complexity.',
                'impact_score': 80,
                'recommendation': 'Consider using more efficient algorithms or data structures.'
            },
            'string_concatenation': {
                'type': PerformanceIssueType.INEFFICIENT_DATA_STRUCTURE,
                'severity': PerformanceLevel.FAIR,
                'title': 'Inefficient String Concatenation',
                'description': 'String concatenation in loops is inefficient.',
                'impact_score': 50,
                'recommendation': 'Use join() method or f-strings for better performance.'
            },
            'synchronous_requests': {
                'type': PerformanceIssueType.BLOCKING_OPERATION,
                'severity': PerformanceLevel.POOR,
                'title': 'Synchronous HTTP Requests',
                'description': 'Synchronous requests block execution and reduce performance.',
                'impact_score': 70,
                'recommendation': 'Use async/await or concurrent.futures for non-blocking requests.'
            }
        }
        
        return pattern_info.get(pattern_name, {
            'type': PerformanceIssueType.INEFFICIENT_LOOP,
            'severity': PerformanceLevel.FAIR,
            'title': 'Performance Issue Detected',
            'description': f'Potential performance issue: {pattern_name}',
            'impact_score': 40,
            'recommendation': 'Review and optimize this code pattern.'
        })
    
    def _get_memory_issue_info(self, pattern_name: str, match: str) -> Dict[str, Any]:
        """Get issue information for memory patterns"""
        memory_info = {
            'large_list_creation': {
                'severity': PerformanceLevel.POOR,
                'title': 'Large List Creation',
                'description': 'Creating very large lists can consume excessive memory.',
                'impact_score': 75,
                'recommendation': 'Consider using generators or iterators for large datasets.'
            },
            'unclosed_files': {
                'severity': PerformanceLevel.FAIR,
                'title': 'Potential Resource Leak',
                'description': 'Files may not be properly closed, leading to resource leaks.',
                'impact_score': 60,
                'recommendation': 'Use context managers (with statement) for file operations.'
            }
        }
        
        return memory_info.get(pattern_name, {
            'severity': PerformanceLevel.FAIR,
            'title': 'Memory Issue Detected',
            'description': f'Potential memory issue: {pattern_name}',
            'impact_score': 50,
            'recommendation': 'Review memory usage patterns.'
        })
    
    def _find_recursive_functions(self, ast_tree: ASTNode) -> List[ASTNode]:
        """Find potentially recursive functions"""
        recursive_functions = []
        
        def find_functions(node: ASTNode):
            if node.node_type in ['function', 'method', 'function_definition'] and node.name:
                # Check if function calls itself
                if self._calls_itself(node, node.name):
                    recursive_functions.append(node)
            
            for child in node.children:
                find_functions(child)
        
        find_functions(ast_tree)
        return recursive_functions
    
    def _calls_itself(self, node: ASTNode, function_name: str) -> bool:
        """Check if a function calls itself (simple recursive detection)"""
        for child in node.children:
            if (child.node_type == 'call' and 
                child.name == function_name):
                return True
            if self._calls_itself(child, function_name):
                return True
        return False

class PerformanceAnalyzerEngine:
    """Main performance analyzer engine"""
    
    def __init__(self):
        self.complexity_analyzer = ComplexityAnalyzer()
        self.issue_detector = PerformanceIssueDetector()
    
    def analyze_performance(self, code: str, filename: str = "", 
                          ast_result: Optional[ParseResult] = None) -> PerformanceAnalysisResult:
        """Perform comprehensive performance analysis"""
        try:
            # Parse AST if not provided
            if ast_result is None:
                from .ast_parser import parse_code
                ast_result = parse_code(code, filename)
            
            # Analyze complexity
            complexity_metrics = self.complexity_analyzer.analyze_complexity(code, ast_result)
            
            # Detect performance issues
            issues = self.issue_detector.detect_issues(code, ast_result, complexity_metrics)
            
            # Calculate overall performance metrics
            performance_metrics = self._calculate_performance_metrics(complexity_metrics, issues)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(issues, complexity_metrics)
            
            # Create analysis summary
            analysis_summary = self._create_analysis_summary(code, ast_result, issues)
            
            return PerformanceAnalysisResult(
                metrics=performance_metrics,
                issues=issues,
                recommendations=recommendations,
                analysis_summary=analysis_summary
            )
            
        except Exception as e:
            logger.error(f"Error in performance analysis: {str(e)}")
            return PerformanceAnalysisResult(
                metrics=PerformanceMetrics(
                    overall_score=0,
                    complexity_metrics=ComplexityMetrics(),
                    performance_level=PerformanceLevel.CRITICAL,
                    bottleneck_count=0,
                    optimization_potential=0,
                    estimated_execution_time="Unknown",
                    memory_usage_estimate="Unknown"
                ),
                issues=[],
                recommendations=[],
                analysis_summary={'error': str(e)}
            )
    
    def _calculate_performance_metrics(self, complexity_metrics: ComplexityMetrics, 
                                     issues: List[PerformanceIssue]) -> PerformanceMetrics:
        """Calculate overall performance metrics"""
        # Calculate overall score (0-100)
        base_score = 100
        
        # Deduct points for complexity
        complexity_penalty = min(50, complexity_metrics.cyclomatic_complexity * 2)
        cognitive_penalty = min(30, complexity_metrics.cognitive_complexity)
        
        # Deduct points for issues
        issue_penalty = sum(min(20, issue.impact_score / 5) for issue in issues)
        
        overall_score = max(0, base_score - complexity_penalty - cognitive_penalty - issue_penalty)
        
        # Determine performance level
        if overall_score >= 80:
            performance_level = PerformanceLevel.EXCELLENT
        elif overall_score >= 60:
            performance_level = PerformanceLevel.GOOD
        elif overall_score >= 40:
            performance_level = PerformanceLevel.FAIR
        elif overall_score >= 20:
            performance_level = PerformanceLevel.POOR
        else:
            performance_level = PerformanceLevel.CRITICAL
        
        # Calculate optimization potential
        optimization_potential = min(100, len(issues) * 15 + complexity_penalty)
        
        # Estimate execution characteristics
        execution_time = self._estimate_execution_time(complexity_metrics, issues)
        memory_usage = self._estimate_memory_usage(complexity_metrics, issues)
        
        return PerformanceMetrics(
            overall_score=overall_score,
            complexity_metrics=complexity_metrics,
            performance_level=performance_level,
            bottleneck_count=len([i for i in issues if i.severity in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]]),
            optimization_potential=optimization_potential,
            estimated_execution_time=execution_time,
            memory_usage_estimate=memory_usage
        )
    
    def _estimate_execution_time(self, complexity_metrics: ComplexityMetrics, 
                               issues: List[PerformanceIssue]) -> str:
        """Estimate relative execution time"""
        if complexity_metrics.cyclomatic_complexity > 20:
            return "High - Complex control flow"
        elif any(issue.issue_type == PerformanceIssueType.INEFFICIENT_LOOP for issue in issues):
            return "High - Inefficient loops detected"
        elif complexity_metrics.cyclomatic_complexity > 10:
            return "Medium - Moderate complexity"
        else:
            return "Low - Simple and efficient"
    
    def _estimate_memory_usage(self, complexity_metrics: ComplexityMetrics, 
                             issues: List[PerformanceIssue]) -> str:
        """Estimate relative memory usage"""
        memory_issues = [i for i in issues if i.issue_type == PerformanceIssueType.MEMORY_LEAK]
        
        if len(memory_issues) > 3:
            return "High - Multiple memory issues"
        elif len(memory_issues) > 1:
            return "Medium - Some memory concerns"
        elif complexity_metrics.function_length > 100:
            return "Medium - Large functions"
        else:
            return "Low - Efficient memory usage"
    
    def _generate_recommendations(self, issues: List[PerformanceIssue], 
                                complexity_metrics: ComplexityMetrics) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Add issue-specific recommendations
        for issue in issues[:5]:  # Top 5 issues
            recommendations.append(issue.recommendation)
        
        # Add general recommendations based on complexity
        if complexity_metrics.cyclomatic_complexity > 15:
            recommendations.append("Consider breaking down complex functions into smaller, more focused functions.")
        
        if complexity_metrics.nesting_depth > 4:
            recommendations.append("Reduce nesting depth by using early returns or guard clauses.")
        
        if complexity_metrics.maintainability_index < 50:
            recommendations.append("Improve code maintainability by simplifying logic and adding documentation.")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _create_analysis_summary(self, code: str, ast_result: ParseResult, 
                               issues: List[PerformanceIssue]) -> Dict[str, Any]:
        """Create summary of performance analysis"""
        lines_of_code = len([line for line in code.split('\n') if line.strip()])
        
        return {
            'lines_of_code': lines_of_code,
            'language': ast_result.language.value if ast_result.success else 'unknown',
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i.severity == PerformanceLevel.CRITICAL]),
            'issue_types': list(set(issue.issue_type.value for issue in issues)),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

# Global analyzer instance
performance_analyzer = PerformanceAnalyzerEngine()

# Convenience functions
def analyze_code_performance(code: str, filename: str = "") -> PerformanceAnalysisResult:
    """Analyze code performance"""
    return performance_analyzer.analyze_performance(code, filename)

def get_performance_score(code: str, filename: str = "") -> float:
    """Get overall performance score (0-100)"""
    result = analyze_code_performance(code, filename)
    return result.metrics.overall_score