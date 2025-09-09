#!/usr/bin/env python3
"""
CodeGuard AI - Main Application Entry Point

This module initializes and configures the FastAPI application for CodeGuard AI,
a specialized static analysis platform for AI-generated code security.
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from rich.console import Console
from rich.panel import Panel

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.core.config import get_settings
from app.api.v1.router import api_router
from app.core.database import init_db
from app.core.redis_client import init_redis

console = Console()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    console.print(Panel.fit(
        "[bold blue]CodeGuard AI - Starting Up[/bold blue]\n"
        "🔍 AI Code Detection Engine\n"
        "🛡️  Security Vulnerability Scanner\n"
        "⚡ Performance Analysis Module\n"
        "📊 Code Quality Assessment",
        border_style="blue"
    ))
    
    try:
        # Initialize database
        await init_db()
        console.print("✅ Database initialized")
        
        # Initialize Redis
        await init_redis()
        console.print("✅ Redis cache initialized")
        
        console.print("🚀 [bold green]CodeGuard AI is ready![/bold green]")
        
    except Exception as e:
        console.print(f"❌ [bold red]Startup failed: {e}[/bold red]")
        raise
    
    yield
    
    # Shutdown
    console.print("🔄 [yellow]CodeGuard AI shutting down...[/yellow]")


# Create FastAPI application
app = FastAPI(
    title="CodeGuard AI",
    description="Specialized static analysis platform for AI-generated code security and quality assessment",
    version="1.0.0-MVP",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "CodeGuard AI - Securing the future of AI-assisted development",
        "version": "1.0.0-MVP",
        "docs": "/docs",
        "api": "/api/v1",
        "features": [
            "AI Code Detection",
            "Security Vulnerability Scanner",
            "Performance Analysis",
            "Code Quality Assessment"
        ]
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "CodeGuard AI",
        "version": "1.0.0-MVP"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler for unexpected errors."""
    console.print(f"❌ [bold red]Unexpected error: {exc}[/bold red]")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error"
            }
        }
    )


if __name__ == "__main__":
    # Development server
    console.print(Panel.fit(
        "[bold cyan]CodeGuard AI - Development Server[/bold cyan]\n"
        f"🌐 Server: http://localhost:{settings.PORT}\n"
        f"📚 Docs: http://localhost:{settings.PORT}/docs\n"
        f"🔧 API: http://localhost:{settings.PORT}/api/v1",
        border_style="cyan"
    ))
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )