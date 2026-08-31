from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.ai_analyzer import ai_analyzer
from app.core.auth import get_current_user
from app.models.user import User

router = APIRouter()

class AnalysisRequest(BaseModel):
    code: str
    language: str
    filename: Optional[str] = None

class AnalysisResponse(BaseModel):
    summary: Dict[str, Any]
    issues: list
    ai_detection: Dict[str, Any]
    metrics: Dict[str, Any]
    language: str

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_code(
    request: AnalysisRequest,
    # current_user: User = Depends(get_current_user) # Optional: Require auth
):
    """
    Analyze code using AI to detect security, quality, and performance issues.
    """
    try:
        result = await ai_analyzer.analyze_code(request.code, request.language)
        
        # TODO: Save result to database for history
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatRequest(BaseModel):
    code: str
    language: str
    message: str
    context: Optional[list] = [] # Previous messages for context
    analysis_result: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    reply: str

@router.post("/chat", response_model=ChatResponse)
async def chat_about_code(
    request: ChatRequest,
    # current_user: User = Depends(get_current_user)
):
    """
    Chat about the code with the AI.
    """
    try:
        reply = await ai_analyzer.chat_about_code(
            request.code, 
            request.language, 
            request.message, 
            request.context,
            request.analysis_result
        )
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_analysis_history(
    # current_user: User = Depends(get_current_user)
):
    """
    Retrieve analysis history.
    """
    # Placeholder for history retrieval
    return {"history": []}
