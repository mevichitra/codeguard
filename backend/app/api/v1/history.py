from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ...core.database import get_db
from ...models.analysis import CodeAnalysis
from ...models.user import User
from ..deps import get_current_user

router = APIRouter(tags=["History"])
logger = logging.getLogger(__name__)

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
