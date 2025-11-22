from datetime import datetime
from typing import Dict
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    services: Dict[str, str]

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
