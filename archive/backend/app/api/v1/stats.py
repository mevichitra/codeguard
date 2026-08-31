from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ...core.database import get_db
from ...models.analysis import CodeAnalysis, SecurityVulnerability, AIPattern
from ...models.user import User

# We need a way to get current user, maybe move it to a common dependency module later
# For now, I'll redefine or import if I can find where it was. 
# It was in routes.py as a placeholder. I should probably create a dependencies.py.

# Let's create a dependencies.py first or just put it here for now and refactor later.
# Actually, better to put shared dependencies in `backend/app/api/deps.py`.

router = APIRouter(tags=["Statistics"])
logger = logging.getLogger(__name__)

# Placeholder for get_current_user until we have deps.py
def get_current_user(db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user (placeholder for authentication)"""
    return None

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
    return await get_statistics(db, current_user)
