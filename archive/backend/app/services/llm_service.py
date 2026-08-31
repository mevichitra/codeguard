from typing import Dict, List, Optional, Any
from openai import AsyncOpenAI
import json
from dataclasses import dataclass
from enum import Enum

from ..core.config import settings
from ..models.analysis import CodeAnalysis, SecurityVulnerability, PerformanceMetric


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


@dataclass
class LLMResponse:
    content: str
    confidence: float
    reasoning: str
    suggestions: List[str]
    metadata: Dict[str, Any]


class LLMService:
    """Service for integrating with Large Language Models for context-aware analysis."""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.provider = provider
        self._setup_client()
    
    def _setup_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == LLMProvider.OPENAI:
            if settings.OPENAI_API_KEY:
                self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            else:
                self.client = None
        # Add other providers as needed
    
    async def analyze_code_context(self, code: str, language: str, 
                                 existing_issues: List[Dict]) -> LLMResponse:
        """Analyze code with context awareness and provide recommendations."""
        
        prompt = self._build_analysis_prompt(code, language, existing_issues)
        
        try:
            response = await self._call_llm(prompt, max_tokens=1000)
            return self._parse_analysis_response(response)
        except Exception as e:
            return LLMResponse(
                content=f"Analysis failed: {str(e)}",
                confidence=0.0,
                reasoning="LLM service error",
                suggestions=[],
                metadata={"error": str(e)}
            )
    
    async def generate_security_recommendations(self, 
                                               security_issues: List[SecurityVulnerability]) -> LLMResponse:
        """Generate contextual security recommendations based on found issues."""
        
        prompt = self._build_security_prompt(security_issues)
        
        try:
            response = await self._call_llm(prompt, max_tokens=800)
            return self._parse_recommendation_response(response)
        except Exception as e:
            return LLMResponse(
                content="Failed to generate security recommendations",
                confidence=0.0,
                reasoning=str(e),
                suggestions=[],
                metadata={"error": str(e)}
            )
    
    async def suggest_performance_optimizations(self, 
                                               performance_issues: List[PerformanceMetric],
                                               code_context: str) -> LLMResponse:
        """Suggest performance optimizations based on detected issues."""
        
        prompt = self._build_performance_prompt(performance_issues, code_context)
        
        try:
            response = await self._call_llm(prompt, max_tokens=1200)
            return self._parse_optimization_response(response)
        except Exception as e:
            return LLMResponse(
                content="Failed to generate performance suggestions",
                confidence=0.0,
                reasoning=str(e),
                suggestions=[],
                metadata={"error": str(e)}
            )
    
    async def detect_ai_generated_patterns(self, code: str, language: str) -> LLMResponse:
        """Use LLM to detect AI-generated code patterns and characteristics."""
        
        prompt = self._build_ai_detection_prompt(code, language)
        
        try:
            response = await self._call_llm(prompt, max_tokens=600)
            return self._parse_ai_detection_response(response)
        except Exception as e:
            return LLMResponse(
                content="AI detection analysis failed",
                confidence=0.0,
                reasoning=str(e),
                suggestions=[],
                metadata={"error": str(e)}
            )
    
    async def explain_vulnerability(self, vulnerability: SecurityVulnerability) -> LLMResponse:
        """Provide detailed explanation of a security vulnerability."""
        
        prompt = self._build_vulnerability_explanation_prompt(vulnerability)
        
        try:
            response = await self._call_llm(prompt, max_tokens=800)
            return self._parse_explanation_response(response)
        except Exception as e:
            return LLMResponse(
                content="Failed to explain vulnerability",
                confidence=0.0,
                reasoning=str(e),
                suggestions=[],
                metadata={"error": str(e)}
            )
    
    async def generate_comprehensive_summary(self, code: str, language: str, 
                                           analysis_results: Dict[str, Any]) -> LLMResponse:
        """Generate a comprehensive summary of all analysis results using GPT-4o-mini."""
        
        prompt = self._build_comprehensive_summary_prompt(code, language, analysis_results)
        
        try:
            response = await self._call_llm(prompt, max_tokens=1200)
            return self._parse_summary_response(response)
        except Exception as e:
            return LLMResponse(
                content="Summary generation failed",
                confidence=0.0,
                reasoning=str(e),
                suggestions=[],
                metadata={"error": str(e)}
            )
    
    def _build_analysis_prompt(self, code: str, language: str, 
                              existing_issues: List[Dict]) -> str:
        """Build prompt for general code analysis."""
        issues_summary = "\n".join([f"- {issue.get('type', 'Unknown')}: {issue.get('description', 'No description')}" 
                                   for issue in existing_issues[:5]])  # Limit to top 5
        
        return f"""
Analyze the following {language} code for potential issues, improvements, and best practices.

Existing detected issues:
{issues_summary}

Code to analyze:
```{language}
{code[:2000]}  # Limit code length
```

Provide:
1. Overall code quality assessment
2. Additional issues not already detected
3. Specific improvement recommendations
4. Best practice suggestions
5. Confidence level (0-1)

Respond in JSON format:
{{
    "assessment": "overall quality assessment",
    "additional_issues": ["issue1", "issue2"],
    "recommendations": ["rec1", "rec2"],
    "best_practices": ["practice1", "practice2"],
    "confidence": 0.85,
    "reasoning": "explanation of analysis"
}}
"""
    
    def _build_security_prompt(self, security_issues: List[SecurityVulnerability]) -> str:
        """Build prompt for security recommendations."""
        issues_text = "\n".join([
            f"- {issue.severity.value}: {issue.description} (Line {issue.line_number})"
            for issue in security_issues[:10]  # Limit to top 10
        ])
        
        return f"""
Based on the following security issues found in the code, provide comprehensive remediation recommendations:

Security Issues:
{issues_text}

Provide:
1. Prioritized remediation steps
2. Code examples for fixes where applicable
3. Prevention strategies
4. Security best practices

Respond in JSON format:
{{
    "priority_fixes": ["fix1", "fix2"],
    "code_examples": {{"issue_type": "example_code"}},
    "prevention_strategies": ["strategy1", "strategy2"],
    "best_practices": ["practice1", "practice2"],
    "confidence": 0.9,
    "reasoning": "explanation"
}}
"""
    
    def _build_performance_prompt(self, performance_issues: List[PerformanceMetric], 
                                 code_context: str) -> str:
        """Build prompt for performance optimization suggestions."""
        issues_text = "\n".join([
            f"- {issue.category}: {issue.description} (Impact: {issue.impact})"
            for issue in performance_issues[:8]  # Limit to top 8
        ])
        
        return f"""
Analyze the following performance issues and provide optimization recommendations:

Performance Issues:
{issues_text}

Code Context (first 1000 chars):
```
{code_context[:1000]}
```

Provide:
1. Specific optimization techniques
2. Code refactoring suggestions
3. Algorithm improvements
4. Resource usage optimizations

Respond in JSON format:
{{
    "optimizations": ["opt1", "opt2"],
    "refactoring_suggestions": ["refactor1", "refactor2"],
    "algorithm_improvements": ["algo1", "algo2"],
    "resource_optimizations": ["resource1", "resource2"],
    "confidence": 0.8,
    "reasoning": "explanation"
}}
"""
    
    def _build_ai_detection_prompt(self, code: str, language: str) -> str:
        """Build prompt for AI-generated code detection."""
        return f"""
Analyze the following {language} code to determine if it was likely generated by AI:

Code:
```{language}
{code[:1500]}
```

Look for patterns such as:
- Overly verbose or repetitive comments
- Unusual variable naming patterns
- Generic or template-like structure
- Inconsistent coding style
- Lack of domain-specific optimizations

Respond in JSON format:
{{
    "ai_generated_probability": 0.75,
    "indicators": ["indicator1", "indicator2"],
    "human_like_aspects": ["aspect1", "aspect2"],
    "confidence": 0.8,
    "reasoning": "detailed explanation"
}}
"""
    
    def _build_vulnerability_explanation_prompt(self, vulnerability: SecurityVulnerability) -> str:
        """Build prompt for vulnerability explanation."""
        return f"""
Provide a detailed explanation of the following security vulnerability:

Vulnerability: {vulnerability.description}
Severity: {vulnerability.severity.value}
Type: {vulnerability.vulnerability_type}
Location: Line {vulnerability.line_number}
Code Context: {vulnerability.code_context[:500] if vulnerability.code_context else 'Not available'}

Explain:
1. What this vulnerability is
2. How it can be exploited
3. Potential impact
4. Step-by-step remediation
5. Prevention measures

Respond in JSON format:
{{
    "explanation": "what this vulnerability is",
    "exploitation_method": "how it can be exploited",
    "potential_impact": "impact description",
    "remediation_steps": ["step1", "step2"],
    "prevention_measures": ["measure1", "measure2"],
    "confidence": 0.9,
    "reasoning": "explanation basis"
}}
"""
    
    async def _call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Make API call to the LLM provider."""
        if self.provider == LLMProvider.OPENAI:
            if not self.client:
                raise Exception("OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior software engineer and security expert. Provide accurate, actionable advice."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content
        
        raise NotImplementedError(f"Provider {self.provider} not implemented")
    
    def _parse_analysis_response(self, response: str) -> LLMResponse:
        """Parse general analysis response."""
        try:
            data = json.loads(response)
            return LLMResponse(
                content=data.get("assessment", ""),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggestions=data.get("recommendations", []) + data.get("best_practices", []),
                metadata={
                    "additional_issues": data.get("additional_issues", []),
                    "type": "analysis"
                }
            )
        except json.JSONDecodeError:
            return LLMResponse(
                content=response,
                confidence=0.3,
                reasoning="Failed to parse structured response",
                suggestions=[],
                metadata={"raw_response": response}
            )
    
    def _parse_recommendation_response(self, response: str) -> LLMResponse:
        """Parse security recommendation response."""
        try:
            data = json.loads(response)
            return LLMResponse(
                content="Security recommendations generated",
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggestions=data.get("priority_fixes", []) + data.get("best_practices", []),
                metadata={
                    "code_examples": data.get("code_examples", {}),
                    "prevention_strategies": data.get("prevention_strategies", []),
                    "type": "security_recommendations"
                }
            )
        except json.JSONDecodeError:
            return LLMResponse(
                content=response,
                confidence=0.3,
                reasoning="Failed to parse structured response",
                suggestions=[],
                metadata={"raw_response": response}
            )
    
    def _parse_optimization_response(self, response: str) -> LLMResponse:
        """Parse performance optimization response."""
        try:
            data = json.loads(response)
            all_suggestions = (
                data.get("optimizations", []) +
                data.get("refactoring_suggestions", []) +
                data.get("algorithm_improvements", []) +
                data.get("resource_optimizations", [])
            )
            return LLMResponse(
                content="Performance optimization suggestions generated",
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggestions=all_suggestions,
                metadata={
                    "optimizations": data.get("optimizations", []),
                    "refactoring": data.get("refactoring_suggestions", []),
                    "algorithms": data.get("algorithm_improvements", []),
                    "resources": data.get("resource_optimizations", []),
                    "type": "performance_optimization"
                }
            )
        except json.JSONDecodeError:
            return LLMResponse(
                content=response,
                confidence=0.3,
                reasoning="Failed to parse structured response",
                suggestions=[],
                metadata={"raw_response": response}
            )
    
    def _parse_ai_detection_response(self, response: str) -> LLMResponse:
        """Parse AI detection response."""
        try:
            data = json.loads(response)
            probability = data.get("ai_generated_probability", 0.5)
            return LLMResponse(
                content=f"AI generation probability: {probability:.2%}",
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggestions=data.get("indicators", []),
                metadata={
                    "ai_probability": probability,
                    "indicators": data.get("indicators", []),
                    "human_aspects": data.get("human_like_aspects", []),
                    "type": "ai_detection"
                }
            )
        except json.JSONDecodeError:
            return LLMResponse(
                content=response,
                confidence=0.3,
                reasoning="Failed to parse structured response",
                suggestions=[],
                metadata={"raw_response": response}
            )
    
    def _parse_explanation_response(self, response: str) -> LLMResponse:
        """Parse vulnerability explanation response."""
        try:
            data = json.loads(response)
            return LLMResponse(
                content=data.get("explanation", ""),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggestions=data.get("remediation_steps", []) + data.get("prevention_measures", []),
                metadata={
                    "exploitation_method": data.get("exploitation_method", ""),
                    "potential_impact": data.get("potential_impact", ""),
                    "remediation_steps": data.get("remediation_steps", []),
                    "prevention_measures": data.get("prevention_measures", []),
                    "type": "vulnerability_explanation"
                }
            )
        except json.JSONDecodeError:
            return LLMResponse(
                content=response,
                confidence=0.3,
                reasoning="Failed to parse structured response",
                suggestions=[],
                metadata={"raw_response": response}
            )
    
    def _build_comprehensive_summary_prompt(self, code: str, language: str, 
                                          analysis_results: Dict[str, Any]) -> str:
        """Build prompt for comprehensive summary generation."""
        return f"""
Generate a comprehensive summary of the code analysis results for the following {language} code:

Code (first 1000 chars):
```{language}
{code[:1000]}
```

Analysis Results:
{json.dumps(analysis_results, indent=2)[:2000]}

Provide:
1. Overall code quality assessment
2. Key findings summary
3. Priority recommendations
4. Risk assessment
5. Next steps

Respond in JSON format:
{{
    "overall_quality": "assessment",
    "key_findings": ["finding1", "finding2"],
    "priority_recommendations": ["rec1", "rec2"],
    "risk_assessment": "risk level and explanation",
    "next_steps": ["step1", "step2"],
    "confidence": 0.9,
    "reasoning": "summary basis"
}}
"""
    
    def _parse_summary_response(self, response: str) -> LLMResponse:
        """Parse comprehensive summary response."""
        try:
            data = json.loads(response)
            return LLMResponse(
                content=data.get("overall_quality", ""),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", ""),
                suggestions=data.get("priority_recommendations", []) + data.get("next_steps", []),
                metadata={
                    "key_findings": data.get("key_findings", []),
                    "risk_assessment": data.get("risk_assessment", ""),
                    "type": "comprehensive_summary"
                }
            )
        except json.JSONDecodeError:
            return LLMResponse(
                content=response,
                confidence=0.3,
                reasoning="Failed to parse structured response",
                suggestions=[],
                metadata={"raw_response": response}
            )


# Singleton instance
llm_service = LLMService()