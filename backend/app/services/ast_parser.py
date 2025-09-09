#!/usr/bin/env python3
"""
CodeGuard AI - AST Parser Engine

Multi-language Abstract Syntax Tree parser for code analysis.
Supports Python, JavaScript, Java, C++, and other popular languages.
"""

import ast
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set

import esprima  # JavaScript parser
from tree_sitter import Language, Parser, Node

# Configure logging
logger = logging.getLogger(__name__)

class LanguageType(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    UNKNOWN = "unknown"

@dataclass
class CodeMetrics:
    """Code complexity and structure metrics"""
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    nesting_depth: int = 0
    function_count: int = 0
    class_count: int = 0
    import_count: int = 0
    comment_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ASTNode:
    """Unified AST node representation"""
    node_type: str
    name: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    column_start: int = 0
    column_end: int = 0
    children: List['ASTNode'] = None
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.attributes is None:
            self.attributes = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_type': self.node_type,
            'name': self.name,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'column_start': self.column_start,
            'column_end': self.column_end,
            'children': [child.to_dict() for child in self.children],
            'attributes': self.attributes
        }

@dataclass
class ParseResult:
    """Result of AST parsing operation"""
    success: bool
    language: LanguageType
    ast_tree: Optional[ASTNode] = None
    metrics: Optional[CodeMetrics] = None
    errors: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'language': self.language.value,
            'ast_tree': self.ast_tree.to_dict() if self.ast_tree else None,
            'metrics': self.metrics.to_dict() if self.metrics else None,
            'errors': self.errors,
            'warnings': self.warnings
        }

class BaseParser(ABC):
    """Abstract base class for language-specific parsers"""
    
    @abstractmethod
    def parse(self, code: str, filename: str = "") -> ParseResult:
        """Parse code and return AST with metrics"""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> Set[str]:
        """Get file extensions supported by this parser"""
        pass
    
    def calculate_metrics(self, ast_tree: ASTNode, code: str) -> CodeMetrics:
        """Calculate code metrics from AST"""
        metrics = CodeMetrics()
        metrics.lines_of_code = len([line for line in code.split('\n') if line.strip()])
        
        # Count comments
        comment_lines = len(re.findall(r'#.*|//.*|/\*[\s\S]*?\*/', code))
        metrics.comment_ratio = comment_lines / max(metrics.lines_of_code, 1)
        
        # Traverse AST to calculate other metrics
        self._calculate_ast_metrics(ast_tree, metrics)
        
        return metrics
    
    def _calculate_ast_metrics(self, node: ASTNode, metrics: CodeMetrics, depth: int = 0):
        """Recursively calculate metrics from AST nodes"""
        metrics.nesting_depth = max(metrics.nesting_depth, depth)
        
        if node.node_type in ['function', 'method', 'function_definition']:
            metrics.function_count += 1
        elif node.node_type in ['class', 'class_definition']:
            metrics.class_count += 1
        elif node.node_type in ['import', 'import_statement']:
            metrics.import_count += 1
        
        # Calculate cyclomatic complexity
        if node.node_type in ['if', 'while', 'for', 'case', 'catch', 'and', 'or']:
            metrics.cyclomatic_complexity += 1
        
        for child in node.children:
            self._calculate_ast_metrics(child, metrics, depth + 1)

class PythonParser(BaseParser):
    """Python AST parser using built-in ast module"""
    
    def get_supported_extensions(self) -> Set[str]:
        return {'.py', '.pyw', '.pyi'}
    
    def parse(self, code: str, filename: str = "") -> ParseResult:
        try:
            # Parse Python code using built-in ast module
            python_ast = ast.parse(code, filename=filename)
            
            # Convert to unified AST format
            ast_tree = self._convert_python_ast(python_ast)
            
            # Calculate metrics
            metrics = self.calculate_metrics(ast_tree, code)
            
            return ParseResult(
                success=True,
                language=LanguageType.PYTHON,
                ast_tree=ast_tree,
                metrics=metrics
            )
            
        except SyntaxError as e:
            return ParseResult(
                success=False,
                language=LanguageType.PYTHON,
                errors=[f"Syntax error: {str(e)}"]
            )
        except Exception as e:
            return ParseResult(
                success=False,
                language=LanguageType.PYTHON,
                errors=[f"Parse error: {str(e)}"]
            )
    
    def _convert_python_ast(self, node: ast.AST) -> ASTNode:
        """Convert Python AST to unified format"""
        node_type = type(node).__name__.lower()
        name = getattr(node, 'name', None)
        
        # Get line/column info
        line_start = getattr(node, 'lineno', 0)
        line_end = getattr(node, 'end_lineno', line_start)
        column_start = getattr(node, 'col_offset', 0)
        column_end = getattr(node, 'end_col_offset', column_start)
        
        # Create unified node
        unified_node = ASTNode(
            node_type=node_type,
            name=name,
            line_start=line_start,
            line_end=line_end,
            column_start=column_start,
            column_end=column_end
        )
        
        # Add node-specific attributes
        if isinstance(node, ast.FunctionDef):
            unified_node.attributes['args'] = [arg.arg for arg in node.args.args]
            unified_node.attributes['decorators'] = len(node.decorator_list)
        elif isinstance(node, ast.ClassDef):
            unified_node.attributes['bases'] = [base.id if hasattr(base, 'id') else str(base) for base in node.bases]
        
        # Recursively convert children
        for child in ast.iter_child_nodes(node):
            unified_node.children.append(self._convert_python_ast(child))
        
        return unified_node

class JavaScriptParser(BaseParser):
    """JavaScript/TypeScript parser using esprima"""
    
    def get_supported_extensions(self) -> Set[str]:
        return {'.js', '.jsx', '.ts', '.tsx', '.mjs'}
    
    def parse(self, code: str, filename: str = "") -> ParseResult:
        try:
            # Parse JavaScript code using esprima
            js_ast = esprima.parseScript(code, {'loc': True, 'range': True})
            
            # Convert to unified AST format
            ast_tree = self._convert_js_ast(js_ast)
            
            # Calculate metrics
            metrics = self.calculate_metrics(ast_tree, code)
            
            language = LanguageType.TYPESCRIPT if filename.endswith(('.ts', '.tsx')) else LanguageType.JAVASCRIPT
            
            return ParseResult(
                success=True,
                language=language,
                ast_tree=ast_tree,
                metrics=metrics
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                language=LanguageType.JAVASCRIPT,
                errors=[f"Parse error: {str(e)}"]
            )
    
    def _convert_js_ast(self, node: Dict[str, Any]) -> ASTNode:
        """Convert JavaScript AST to unified format"""
        node_type = node.get('type', 'unknown').lower()
        name = node.get('name') or node.get('id', {}).get('name')
        
        # Get location info
        loc = node.get('loc', {})
        start = loc.get('start', {})
        end = loc.get('end', {})
        
        unified_node = ASTNode(
            node_type=node_type,
            name=name,
            line_start=start.get('line', 0),
            line_end=end.get('line', 0),
            column_start=start.get('column', 0),
            column_end=end.get('column', 0)
        )
        
        # Add node-specific attributes
        if node_type == 'functiondeclaration':
            params = node.get('params', [])
            unified_node.attributes['params'] = [p.get('name', '') for p in params]
        
        # Recursively convert children
        for key, value in node.items():
            if isinstance(value, dict) and 'type' in value:
                unified_node.children.append(self._convert_js_ast(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'type' in item:
                        unified_node.children.append(self._convert_js_ast(item))
        
        return unified_node

class ASTParserEngine:
    """Main AST parser engine that coordinates language-specific parsers"""
    
    def __init__(self):
        self.parsers: Dict[LanguageType, BaseParser] = {
            LanguageType.PYTHON: PythonParser(),
            LanguageType.JAVASCRIPT: JavaScriptParser(),
            LanguageType.TYPESCRIPT: JavaScriptParser(),
        }
        
        # Build extension to language mapping
        self.extension_map: Dict[str, LanguageType] = {}
        for lang, parser in self.parsers.items():
            for ext in parser.get_supported_extensions():
                self.extension_map[ext] = lang
    
    def detect_language(self, filename: str, code: str = "") -> LanguageType:
        """Detect programming language from filename and/or code content"""
        # First try by file extension
        ext = Path(filename).suffix.lower()
        if ext in self.extension_map:
            return self.extension_map[ext]
        
        # Fallback to content-based detection
        if code:
            return self._detect_language_by_content(code)
        
        return LanguageType.UNKNOWN
    
    def _detect_language_by_content(self, code: str) -> LanguageType:
        """Detect language by analyzing code content"""
        code_lower = code.lower()
        
        # Python indicators
        if any(keyword in code for keyword in ['def ', 'import ', 'from ', '__init__']):
            return LanguageType.PYTHON
        
        # JavaScript indicators
        if any(keyword in code for keyword in ['function ', 'var ', 'let ', 'const ', '=>']):
            return LanguageType.JAVASCRIPT
        
        # Java indicators
        if any(keyword in code for keyword in ['public class', 'private ', 'protected ']):
            return LanguageType.JAVA
        
        return LanguageType.UNKNOWN
    
    def parse_code(self, code: str, filename: str = "") -> ParseResult:
        """Parse code and return unified AST with metrics"""
        # Detect language
        language = self.detect_language(filename, code)
        
        if language == LanguageType.UNKNOWN:
            return ParseResult(
                success=False,
                language=language,
                errors=["Unsupported or undetected language"]
            )
        
        # Get appropriate parser
        parser = self.parsers.get(language)
        if not parser:
            return ParseResult(
                success=False,
                language=language,
                errors=[f"No parser available for {language.value}"]
            )
        
        # Parse code
        return parser.parse(code, filename)
    
    def parse_file(self, file_path: str) -> ParseResult:
        """Parse a file and return AST with metrics"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            return self.parse_code(code, file_path)
            
        except FileNotFoundError:
            return ParseResult(
                success=False,
                language=LanguageType.UNKNOWN,
                errors=[f"File not found: {file_path}"]
            )
        except Exception as e:
            return ParseResult(
                success=False,
                language=LanguageType.UNKNOWN,
                errors=[f"Error reading file: {str(e)}"]
            )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages"""
        return [lang.value for lang in self.parsers.keys()]
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return list(self.extension_map.keys())

# Global parser instance
parser_engine = ASTParserEngine()

# Convenience functions
def parse_code(code: str, filename: str = "") -> ParseResult:
    """Parse code string and return AST with metrics"""
    return parser_engine.parse_code(code, filename)

def parse_file(file_path: str) -> ParseResult:
    """Parse file and return AST with metrics"""
    return parser_engine.parse_file(file_path)

def detect_language(filename: str, code: str = "") -> LanguageType:
    """Detect programming language"""
    return parser_engine.detect_language(filename, code)

def get_code_metrics(code: str, filename: str = "") -> CodeMetrics:
    """Get code metrics from code string"""
    result = parser_engine.parse_code(code, filename)
    return result.metrics if result.metrics else CodeMetrics()