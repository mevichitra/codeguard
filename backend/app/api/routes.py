#!/usr/bin/env python3
"""
CodeGuard AI - API Routes

RESTful API endpoints for code analysis services.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.redis_client import cache_manager, rate_limiter
from ..services import (
    parse_code, detect_ai_code, scan_code_security,
    analyze_code_performance, assess_code_quality,
    get_ai_confidence, get_security_score,
    get_performance_score, get_quality_score
)
from ..services.llm_service import LLMService
from ..models.analysis import CodeAnalysis, SecurityVulnerability, AIPattern
from ..models.user import User
from ..models.project import Project

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["CodeGuard AI"])

# Request/Response Models
class CodeAnalysisRequest(BaseModel):
    """Request model for code analysis"""
    code: str = Field(..., description="Source code to analyze", min_length=1, max_length=100000)
    filename: Optional[str] = Field(None, description="Optional filename for context")
    language: Optional[str] = Field(None, description="Programming language (auto-detected if not provided)")
    analysis_types: List[str] = Field(
        default=["ai_detection", "security", "performance", "quality"],
        description="Types of analysis to perform"
    )
    
    @validator('analysis_types')
    def validate_analysis_types(cls, v):
        valid_types = {"ai_detection", "security", "performance", "quality", "ast"}
        for analysis_type in v:
            if analysis_type not in valid_types:
                raise ValueError(f"Invalid analysis type: {analysis_type}. Valid types: {valid_types}")
        return v

class FileAnalysisRequest(BaseModel):
    """Request model for file analysis"""
    analysis_types: List[str] = Field(
        default=["ai_detection", "security", "performance", "quality"],
        description="Types of analysis to perform"
    )

class BatchAnalysisRequest(BaseModel):
    """Request model for batch analysis"""
    files: List[Dict[str, str]] = Field(..., description="List of files with 'filename' and 'code' keys")
    analysis_types: List[str] = Field(
        default=["ai_detection", "security", "performance", "quality"],
        description="Types of analysis to perform"
    )

class AnalysisResponse(BaseModel):
    """Response model for analysis results"""
    success: bool
    analysis_id: Optional[str] = None
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    processing_time_ms: float

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    services: Dict[str, str]

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    timestamp: datetime
    request_id: Optional[str] = None

# Utility Functions
def get_current_user(db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user (placeholder for authentication)"""
    # TODO: Implement proper authentication
    return None

async def check_rate_limit(user_id: str = "anonymous") -> bool:
    """Check rate limiting"""
    allowed, _ = await rate_limiter.is_allowed(f"api:{user_id}", limit=100, window_seconds=3600)
    return allowed

async def perform_analysis(code: str, filename: str, analysis_types: List[str]) -> Dict[str, Any]:
    """Perform comprehensive code analysis"""
    results = {}
    
    # Expand "comprehensive" to all analysis types
    if "comprehensive" in analysis_types:
        analysis_types = ["ai_detection", "security", "performance", "quality", "ast"]
    
    try:
        # AST parsing (always performed for other analyses)
        ast_result = parse_code(code, filename)
        if "ast" in analysis_types:
            results["ast"] = {
                "success": ast_result.success,
                "language": ast_result.language.value if ast_result.success else "unknown",
                "metrics": ast_result.metrics.to_dict() if ast_result.metrics else None,
                "error": ast_result.errors[0] if not ast_result.success and ast_result.errors else None
            }
        
        # AI Detection
        if "ai_detection" in analysis_types:
            ai_result = detect_ai_code(code, filename)
            results["ai_detection"] = {
                "confidence": ai_result.overall_confidence,
                "is_ai_generated": ai_result.is_likely_ai_generated,
                "patterns": [pattern.to_dict() for pattern in ai_result.patterns],
                "analysis_summary": ai_result.analysis_summary
            }
        
        # Security Analysis
        if "security" in analysis_types:
            security_result = scan_code_security(code, filename)
            # Calculate overall score based on vulnerabilities
            overall_score = get_security_score(code, filename)
            # Determine risk level based on score
            if overall_score >= 80:
                risk_level = "low"
            elif overall_score >= 60:
                risk_level = "medium"
            elif overall_score >= 40:
                risk_level = "high"
            else:
                risk_level = "critical"
            
            results["security"] = {
                "overall_score": overall_score,
                "risk_level": risk_level,
                "vulnerabilities": [vuln.to_dict() for vuln in security_result.vulnerabilities],
                "total_count": security_result.total_count,
                "severity_counts": security_result.severity_counts,
                "scan_summary": security_result.scan_summary
            }
        
        # Performance Analysis
        if "performance" in analysis_types:
            performance_result = analyze_code_performance(code, filename)
            results["performance"] = {
                "metrics": performance_result.metrics.to_dict(),
                "issues": [issue.to_dict() for issue in performance_result.issues],
                "recommendations": performance_result.recommendations,
                "analysis_summary": performance_result.analysis_summary
            }
        
        # Quality Assessment
        if "quality" in analysis_types:
            quality_result = assess_code_quality(code, filename)
            results["quality"] = {
                "metrics": quality_result.metrics.to_dict(),
                "quality_level": quality_result.quality_level.value,
                "issues": [issue.to_dict() for issue in quality_result.issues],
                "recommendations": quality_result.recommendations,
                "improvement_suggestions": quality_result.improvement_suggestions,
                "analysis_summary": quality_result.analysis_summary
            }
        
        # Generate comprehensive summary using GPT-4o-mini
        try:
            llm_service = LLMService()
            comprehensive_summary = await llm_service.generate_comprehensive_summary(
                code=code,
                filename=filename,
                analysis_results=results
            )
            results["comprehensive_summary"] = comprehensive_summary
        except Exception as llm_error:
            logger.warning(f"Failed to generate comprehensive summary: {str(llm_error)}")
            results["comprehensive_summary"] = {
                "summary": "Summary generation unavailable",
                "key_findings": [],
                "recommendations": [],
                "overall_assessment": "Unable to generate assessment"
            }
        
        return results
        
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# API Endpoints

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={
            "ast_parser": "operational",
            "ai_detector": "operational",
            "security_scanner": "operational",
            "performance_analyzer": "operational",
            "quality_assessor": "operational"
        }
    )

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_code(
    request: CodeAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Analyze source code with specified analysis types"""
    start_time = datetime.utcnow()
    
    # Rate limiting
    user_id = current_user.id if current_user else "anonymous"
    if not await check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Check cache first
        cache_key = f"analysis:{hash(request.code)}:{':'.join(sorted(request.analysis_types))}"
        cached_result = await cache_manager.get(cache_key)
        
        if cached_result:
            return AnalysisResponse(
                success=True,
                results=cached_result,
                metadata={"cached": True, "filename": request.filename},
                timestamp=datetime.utcnow(),
                processing_time_ms=0
            )
        
        # Perform analysis
        results = await perform_analysis(
            request.code, 
            request.filename or "unknown.py", 
            request.analysis_types
        )
        
        # Cache results
        await cache_manager.set(cache_key, results, expire=3600)
        
        # Store in database (background task)
        def store_analysis():
            try:
                import hashlib
                code_hash = hashlib.sha256(request.code.encode()).hexdigest()
                
                analysis = CodeAnalysis(
                    filename=request.filename or "unknown.py",
                    language=results.get("ast", {}).get("language", "unknown"),
                    code_hash=code_hash,
                    code_content=request.code,
                    status="completed",
                    completed_at=datetime.utcnow(),
                    # Extract specific results for database fields
                    ai_detection_confidence=results.get("ai_detection", {}).get("confidence"),
                    is_ai_generated=results.get("ai_detection", {}).get("is_ai_generated"),
                    vulnerability_count=len(results.get("security_analysis", {}).get("vulnerabilities", [])),
                    cyclomatic_complexity=results.get("performance_analysis", {}).get("complexity", {}).get("cyclomatic_complexity"),
                    lines_of_code=results.get("ast", {}).get("metrics", {}).get("lines_of_code")
                )
                db.add(analysis)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to store analysis: {str(e)}")
        
        background_tasks.add_task(store_analysis)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AnalysisResponse(
            success=True,
            results=results,
            metadata={
                "cached": False,
                "filename": request.filename,
                "analysis_types": request.analysis_types
            },
            timestamp=datetime.utcnow(),
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/file", response_model=AnalysisResponse)
async def analyze_file(
    file: UploadFile = File(...),
    analysis_types: str = Form(default="ai_detection,security,performance,quality"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Analyze uploaded file"""
    start_time = datetime.utcnow()
    
    # Rate limiting
    user_id = current_user.id if current_user else "anonymous"
    if not await check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    try:
        # Read file content
        content = await file.read()
        
        # Check file size (max 1MB)
        if len(content) > 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 1MB)")
        
        # Decode content
        try:
            code = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
        
        # Parse analysis types
        analysis_types_list = [t.strip() for t in analysis_types.split(',')]
        
        # Perform analysis
        results = await perform_analysis(code, file.filename, analysis_types_list)
        
        # Store in database (background task)
        def store_file_analysis():
            try:
                import hashlib
                code_hash = hashlib.sha256(code.encode()).hexdigest()
                
                analysis = CodeAnalysis(
                    filename=file.filename or "unknown",
                    language=results.get("ast", {}).get("language", "unknown"),
                    code_hash=code_hash,
                    code_content=code,
                    status="completed",
                    completed_at=datetime.utcnow(),
                    # Extract specific results for database fields
                    ai_detection_confidence=results.get("ai_detection", {}).get("confidence"),
                    is_ai_generated=results.get("ai_detection", {}).get("is_ai_generated"),
                    vulnerability_count=len(results.get("security_analysis", {}).get("vulnerabilities", [])),
                    cyclomatic_complexity=results.get("performance_analysis", {}).get("complexity", {}).get("cyclomatic_complexity"),
                    lines_of_code=results.get("ast", {}).get("metrics", {}).get("lines_of_code")
                )
                db.add(analysis)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to store file analysis: {str(e)}")
        
        background_tasks.add_task(store_file_analysis)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return AnalysisResponse(
            success=True,
            results=results,
            metadata={
                "filename": file.filename,
                "file_size": len(content),
                "analysis_types": analysis_types_list
            },
            timestamp=datetime.utcnow(),
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze/batch", response_model=Dict[str, Any])
async def analyze_batch(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Analyze multiple files in batch"""
    start_time = datetime.utcnow()
    
    # Rate limiting (stricter for batch)
    user_id = current_user.id if current_user else "anonymous"
    batch_allowed, _ = await rate_limiter.is_allowed(f"batch:{user_id}", limit=10, window_seconds=3600)
    if not batch_allowed:
        raise HTTPException(status_code=429, detail="Batch analysis rate limit exceeded")
    
    # Limit batch size
    if len(request.files) > 20:
        raise HTTPException(status_code=400, detail="Batch size limited to 20 files")
    
    try:
        results = {}
        total_processing_time = 0
        
        for i, file_data in enumerate(request.files):
            filename = file_data.get('filename', f'file_{i}.py')
            code = file_data.get('code', '')
            
            if not code:
                results[filename] = {"error": "Empty code content"}
                continue
            
            try:
                file_results = await perform_analysis(code, filename, request.analysis_types)
                results[filename] = file_results
            except Exception as e:
                results[filename] = {"error": str(e)}
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "results": results,
            "metadata": {
                "file_count": len(request.files),
                "analysis_types": request.analysis_types,
                "processing_time_ms": processing_time
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Quick Analysis Endpoints

@router.post("/quick/ai-detection")
async def quick_ai_detection(request: CodeAnalysisRequest):
    """Quick AI detection analysis"""
    try:
        confidence = get_ai_confidence(request.code, request.filename or "unknown.py")
        return {
            "confidence": confidence,
            "is_ai_generated": confidence > 0.7,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick/security-score")
async def quick_security_score(request: CodeAnalysisRequest):
    """Quick security score analysis"""
    try:
        score = get_security_score(request.code, request.filename or "unknown.py")
        return {
            "security_score": score,
            "risk_level": "high" if score < 40 else "medium" if score < 70 else "low",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick/performance-score")
async def quick_performance_score(request: CodeAnalysisRequest):
    """Quick performance score analysis"""
    try:
        score = get_performance_score(request.code, request.filename or "unknown.py")
        return {
            "performance_score": score,
            "performance_level": "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "poor",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quick/quality-score")
async def quick_quality_score(request: CodeAnalysisRequest):
    """Quick quality score analysis"""
    try:
        score = get_quality_score(request.code, request.filename or "unknown.py")
        return {
            "quality_score": score,
            "quality_level": "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "poor",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Analysis History Endpoints

@router.get("/history")
async def get_analysis_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get analysis history"""
    try:
        query = db.query(CodeAnalysis)
        
        if current_user:
            query = query.filter(CodeAnalysis.user_id == current_user.id)
        
        analyses = query.order_by(CodeAnalysis.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "analyses": [{
                "id": analysis.id,
                "filename": analysis.filename,
                "language": analysis.language,
                "analysis_types": analysis.analysis_types,
                "created_at": analysis.created_at.isoformat(),
                "status": analysis.status.value
            } for analysis in analyses],
            "total": query.count(),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"History retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{analysis_id}")
async def get_analysis_result(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get specific analysis result"""
    try:
        query = db.query(CodeAnalysis).filter(CodeAnalysis.id == analysis_id)
        
        if current_user:
            query = query.filter(CodeAnalysis.user_id == current_user.id)
        
        analysis = query.first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        return {
            "id": analysis.id,
            "filename": analysis.filename,
            "language": analysis.language,
            "analysis_types": analysis.analysis_types,
            "results": analysis.results,
            "created_at": analysis.created_at.isoformat(),
            "status": analysis.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Statistics Endpoints

@router.get("/stats")
async def get_statistics(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get analysis statistics"""
    try:
        # Get basic statistics from database
        total_analyses = db.query(CodeAnalysis).count()
        total_vulnerabilities = db.query(SecurityVulnerability).count()
        total_ai_patterns = db.query(AIPattern).count()
        
        return {
            "success": True,
            "statistics": {
                "total_analyses": total_analyses,
                "total_vulnerabilities": total_vulnerabilities,
                "total_ai_patterns": total_ai_patterns,
                "supported_languages": [
                    "python", "javascript", "typescript", "java", "cpp", "c", "go", "rust"
                ],
                "analysis_types": [
                    "ai_detection", "security", "performance", "quality", "ast"
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

# Add missing endpoints for demo compatibility
@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported programming languages"""
    return {
        "success": True,
        "languages": [
            {"name": "Python", "code": "python", "extensions": [".py"]},
            {"name": "JavaScript", "code": "javascript", "extensions": [".js", ".mjs"]},
            {"name": "TypeScript", "code": "typescript", "extensions": [".ts"]},
            {"name": "Java", "code": "java", "extensions": [".java"]},
            {"name": "C++", "code": "cpp", "extensions": [".cpp", ".cc", ".cxx"]},
            {"name": "C", "code": "c", "extensions": [".c"]},
            {"name": "Go", "code": "go", "extensions": [".go"]},
            {"name": "Rust", "code": "rust", "extensions": [".rs"]}
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/statistics")
async def get_statistics_alt(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get analysis statistics (alternative endpoint for demo compatibility)"""
    try:
        # Get basic statistics from database
        total_analyses = db.query(CodeAnalysis).count()
        total_vulnerabilities = db.query(SecurityVulnerability).count()
        total_ai_patterns = db.query(AIPattern).count()
        
        return {
            "success": True,
            "statistics": {
                "total_analyses": total_analyses,
                "total_vulnerabilities": total_vulnerabilities,
                "total_ai_patterns": total_ai_patterns,
                "supported_languages": [
                    "python", "javascript", "typescript", "java", "cpp", "c", "go", "rust"
                ],
                "analysis_types": [
                    "ai_detection", "security", "performance", "quality", "ast"
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

# Error handlers are defined in main.py