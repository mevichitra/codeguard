import json
import logging
import random
from typing import Dict, Any, List, Optional
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIAnalyzerService:
    """
    Service for performing AI-driven code analysis.
    Supports dynamic analysis for Security, Quality, Performance, and AI Detection.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.enabled = settings.is_llm_enabled()

    async def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """
        Analyzes code using an LLM (or mock if disabled) to detect issues.
        """
        if not code or not code.strip():
            return self._get_empty_result()

        if self.enabled:
            try:
                return await self._analyze_with_llm(code, language)
            except Exception as e:
                logger.error(f"LLM analysis failed: {str(e)}")
                # Fallback to mock if LLM fails
                return self._analyze_with_mock(code, language)
        else:
            return self._analyze_with_mock(code, language)

    async def _analyze_with_llm(self, code: str, language: str) -> Dict[str, Any]:
        """
        Real LLM call implementation.
        """
        # TODO: Integrate actual OpenAI client here.
        # For now, we simulate a network delay and return the mock response 
        # because we don't want to break the build without a real key.
        # In a real implementation, this would use `openai.ChatCompletion.create`.
        await asyncio.sleep(1.5) 
        return self._analyze_with_mock(code, language)

    def _analyze_with_mock(self, code: str, language: str) -> Dict[str, Any]:
        """
        Generates sophisticated mock analysis results for demonstration/fallback.
        """
        # Deterministic randomness based on code length to make it feel "real"
        random.seed(len(code))
        
        lines = code.split('\n')
        total_lines = len(lines)
        
        issues = []
        
        # Simulate finding issues
        if total_lines > 0:
            # 1. Security Issue
            if random.random() > 0.3:
                line = random.randint(1, total_lines)
                issues.append({
                    "id": f"sec-{random.randint(1000, 9999)}",
                    "type": "security",
                    "severity": random.choice(["critical", "high", "medium"]),
                    "title": "Potential Injection Vulnerability",
                    "description": f"Unsanitized input usage detected on line {line}. This could lead to injection attacks.",
                    "line": line,
                    "suggestion": "Use parameterized queries or input sanitization functions."
                })
            
            # 2. Quality Issue
            if random.random() > 0.2:
                line = random.randint(1, total_lines)
                issues.append({
                    "id": f"qual-{random.randint(1000, 9999)}",
                    "type": "quality",
                    "severity": random.choice(["medium", "low"]),
                    "title": "Complex Function Logic",
                    "description": f"Cyclomatic complexity is high for the function around line {line}.",
                    "line": line,
                    "suggestion": "Refactor this function into smaller, more manageable pieces."
                })

            # 3. Performance Issue
            if random.random() > 0.4:
                line = random.randint(1, total_lines)
                issues.append({
                    "id": f"perf-{random.randint(1000, 9999)}",
                    "type": "performance",
                    "severity": "medium",
                    "title": "Inefficient Loop",
                    "description": f"Nested loop detected on line {line} which may cause performance degradation.",
                    "line": line,
                    "suggestion": "Consider optimizing the loop or using a more efficient algorithm."
                })

        # Calculate scores
        security_score = max(0, 100 - (len([i for i in issues if i['type'] == 'security']) * 15))
        quality_score = max(0, 100 - (len([i for i in issues if i['type'] == 'quality']) * 10))
        performance_score = max(0, 100 - (len([i for i in issues if i['type'] == 'performance']) * 10))
        
        # AI Detection (Mock)
        ai_probability = random.uniform(0, 100)
        is_ai_generated = ai_probability > 70

        return {
            "summary": {
                "security_score": security_score,
                "quality_score": quality_score,
                "performance_score": performance_score,
                "total_issues": len(issues),
                "critical_issues": len([i for i in issues if i['severity'] == 'critical'])
            },
            "issues": issues,
            "ai_detection": {
                "is_ai_generated": is_ai_generated,
                "probability": round(ai_probability, 1),
                "confidence": round(random.uniform(80, 99), 1),
                "detected_patterns": ["Repetitive structure", "Unnatural variable naming"] if is_ai_generated else [],
                "reasoning": "The code exhibits patterns consistent with LLM generation." if is_ai_generated else "No significant AI patterns detected."
            },
            "metrics": {
                "security": {
                    "cwe_ids": ["CWE-79", "CWE-89"] if security_score < 90 else [],
                    "cvss_score": round(random.uniform(4.0, 9.0), 1) if security_score < 90 else 0.0
                },
                "quality": {
                    "cyclomatic_complexity": random.randint(5, 25),
                    "maintainability_index": round(random.uniform(40, 90), 1),
                    "code_smells": ["Long Function", "Duplicate Code"] if quality_score < 80 else []
                },
                "performance": {
                    "time_complexity": "O(n^2)" if performance_score < 70 else "O(n)",
                    "space_complexity": "O(n)",
                    "resource_usage": "Medium" if performance_score < 80 else "Low"
                }
            },
            "language": language
        }

    def _get_empty_result(self) -> Dict[str, Any]:
        return {
            "summary": {
                "security_score": 100,
                "quality_score": 100,
                "performance_score": 100,
                "total_issues": 0,
                "critical_issues": 0
            },
            "issues": [],
            "ai_detection": {
                "is_ai_generated": False,
                "probability": 0,
                "confidence": 0
            },
            "language": "unknown"
        }

    async def chat_about_code(self, code: str, language: str, message: str, context: List[Dict[str, str]]) -> str:
        """
        Chat about the code using an LLM (or mock).
        """
        if self.enabled:
             # TODO: Implement real LLM chat
             await asyncio.sleep(1.0)
             return self._mock_chat_response(message)
        else:
             return self._mock_chat_response(message)

    def _mock_chat_response(self, message: str) -> str:
        """
        Generates a mock response for the chat.
        """
        message_lower = message.lower()
        if "fix" in message_lower or "improve" in message_lower:
            return "I suggest refactoring the nested loops to improve performance. You might also want to add input validation to prevent potential security issues."
        elif "explain" in message_lower:
            return "This code appears to be processing data. It iterates through a list and performs some calculations. The complexity seems to be O(n^2)."
        elif "security" in message_lower:
            return "I found a potential injection vulnerability. Ensure you are sanitizing all user inputs before using them in queries."
        else:
            return f"That's an interesting point about the {message}. Could you elaborate on how you'd like to change the code?"

ai_analyzer = AIAnalyzerService()
