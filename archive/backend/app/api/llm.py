from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..services.llm_service import llm_service, LLMResponse
from ..models.analysis import SecurityVulnerability, PerformanceMetric
from ..core.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/llm", tags=["LLM Integration"])


class CodeAnalysisRequest(BaseModel):
    code: str = Field(..., description="Code to analyze")
    language: str = Field(..., description="Programming language")
    existing_issues: List[Dict[str, Any]] = Field(default=[], description="Existing detected issues")


class SecurityRecommendationRequest(BaseModel):
    security_issues: List[Dict[str, Any]] = Field(..., description="Security issues to analyze")


class PerformanceOptimizationRequest(BaseModel):
    performance_issues: List[Dict[str, Any]] = Field(..., description="Performance issues")
    code_context: str = Field(..., description="Code context for optimization")


class AIDetectionRequest(BaseModel):
    code: str = Field(..., description="Code to analyze for AI generation")
    language: str = Field(..., description="Programming language")


class VulnerabilityExplanationRequest(BaseModel):
    vulnerability: Dict[str, Any] = Field(..., description="Vulnerability details")


class LLMResponseModel(BaseModel):
    content: str
    confidence: float
    reasoning: str
    suggestions: List[str]
    metadata: Dict[str, Any]
    success: bool = True
    error: Optional[str] = None


@router.post("/analyze-code", response_model=LLMResponseModel)
async def analyze_code_with_llm(
    request: CodeAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze code using LLM for context-aware insights and recommendations.
    
    This endpoint uses Large Language Models to provide:
    - Overall code quality assessment
    - Additional issues not detected by static analysis
    - Specific improvement recommendations
    - Best practice suggestions
    """
    try:
        if len(request.code) > 10000:  # Limit code size
            raise HTTPException(
                status_code=400, 
                detail="Code too large. Maximum 10,000 characters allowed."
            )
        
        response = await llm_service.analyze_code_context(
            code=request.code,
            language=request.language,
            existing_issues=request.existing_issues
        )
        
        return LLMResponseModel(
            content=response.content,
            confidence=response.confidence,
            reasoning=response.reasoning,
            suggestions=response.suggestions,
            metadata=response.metadata
        )
    
    except Exception as e:
        return LLMResponseModel(
            content="Analysis failed",
            confidence=0.0,
            reasoning=str(e),
            suggestions=[],
            metadata={},
            success=False,
            error=str(e)
        )


@router.post("/security-recommendations", response_model=LLMResponseModel)
async def get_security_recommendations(
    request: SecurityRecommendationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate contextual security recommendations based on detected issues.
    
    Provides:
    - Prioritized remediation steps
    - Code examples for fixes
    - Prevention strategies
    - Security best practices
    """
    try:
        # Convert dict issues to SecurityIssue objects for processing
        security_issues = []
        for issue_dict in request.security_issues:
            # Create a mock SecurityIssue object from dict
            # In a real implementation, you'd properly deserialize
            security_issues.append(type('SecurityIssue', (), issue_dict)())
        
        response = await llm_service.generate_security_recommendations(security_issues)
        
        return LLMResponseModel(
            content=response.content,
            confidence=response.confidence,
            reasoning=response.reasoning,
            suggestions=response.suggestions,
            metadata=response.metadata
        )
    
    except Exception as e:
        return LLMResponseModel(
            content="Failed to generate security recommendations",
            confidence=0.0,
            reasoning=str(e),
            suggestions=[],
            metadata={},
            success=False,
            error=str(e)
        )


@router.post("/performance-optimization", response_model=LLMResponseModel)
async def get_performance_optimizations(
    request: PerformanceOptimizationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Suggest performance optimizations based on detected issues.
    
    Provides:
    - Specific optimization techniques
    - Code refactoring suggestions
    - Algorithm improvements
    - Resource usage optimizations
    """
    try:
        if len(request.code_context) > 5000:  # Limit context size
            raise HTTPException(
                status_code=400,
                detail="Code context too large. Maximum 5,000 characters allowed."
            )
        
        # Convert dict issues to PerformanceIssue objects
        performance_issues = []
        for issue_dict in request.performance_issues:
            performance_issues.append(type('PerformanceIssue', (), issue_dict)())
        
        response = await llm_service.suggest_performance_optimizations(
            performance_issues=performance_issues,
            code_context=request.code_context
        )
        
        return LLMResponseModel(
            content=response.content,
            confidence=response.confidence,
            reasoning=response.reasoning,
            suggestions=response.suggestions,
            metadata=response.metadata
        )
    
    except Exception as e:
        return LLMResponseModel(
            content="Failed to generate performance suggestions",
            confidence=0.0,
            reasoning=str(e),
            suggestions=[],
            metadata={},
            success=False,
            error=str(e)
        )


@router.post("/detect-ai-code", response_model=LLMResponseModel)
async def detect_ai_generated_code(
    request: AIDetectionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Detect if code was likely generated by AI.
    
    Analyzes patterns such as:
    - Overly verbose or repetitive comments
    - Unusual variable naming patterns
    - Generic or template-like structure
    - Inconsistent coding style
    """
    try:
        if len(request.code) > 8000:  # Limit code size
            raise HTTPException(
                status_code=400,
                detail="Code too large. Maximum 8,000 characters allowed."
            )
        
        response = await llm_service.detect_ai_generated_patterns(
            code=request.code,
            language=request.language
        )
        
        return LLMResponseModel(
            content=response.content,
            confidence=response.confidence,
            reasoning=response.reasoning,
            suggestions=response.suggestions,
            metadata=response.metadata
        )
    
    except Exception as e:
        return LLMResponseModel(
            content="AI detection analysis failed",
            confidence=0.0,
            reasoning=str(e),
            suggestions=[],
            metadata={},
            success=False,
            error=str(e)
        )


@router.post("/explain-vulnerability", response_model=LLMResponseModel)
async def explain_vulnerability(
    request: VulnerabilityExplanationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Provide detailed explanation of a security vulnerability.
    
    Explains:
    - What the vulnerability is
    - How it can be exploited
    - Potential impact
    - Step-by-step remediation
    - Prevention measures
    """
    try:
        # Convert dict to SecurityIssue object
        vulnerability = type('SecurityIssue', (), request.vulnerability)()
        
        response = await llm_service.explain_vulnerability(vulnerability)
        
        return LLMResponseModel(
            content=response.content,
            confidence=response.confidence,
            reasoning=response.reasoning,
            suggestions=response.suggestions,
            metadata=response.metadata
        )
    
    except Exception as e:
        return LLMResponseModel(
            content="Failed to explain vulnerability",
            confidence=0.0,
            reasoning=str(e),
            suggestions=[],
            metadata={},
            success=False,
            error=str(e)
        )


@router.get("/health")
async def llm_health_check():
    """
    Check if LLM service is available and configured properly.
    """
    try:
        # Simple test to check if LLM service is working
        test_response = await llm_service.analyze_code_context(
            code="print('hello world')",
            language="python",
            existing_issues=[]
        )
        
        return {
            "status": "healthy",
            "provider": llm_service.provider.value,
            "test_confidence": test_response.confidence,
            "available": True
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "provider": llm_service.provider.value,
            "error": str(e),
            "available": False
        }


@router.get("/capabilities")
async def get_llm_capabilities(
    current_user: User = Depends(get_current_user)
):
    """
    Get information about LLM service capabilities and limits.
    """
    return {
        "provider": llm_service.provider.value,
        "capabilities": [
            "code_analysis",
            "security_recommendations",
            "performance_optimization",
            "ai_detection",
            "vulnerability_explanation"
        ],
        "limits": {
            "max_code_size": 10000,
            "max_context_size": 5000,
            "max_ai_detection_size": 8000
        },
        "supported_languages": [
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
            "c",
            "go",
            "rust",
            "php",
            "ruby",
            "swift",
            "kotlin"
        ]
    }