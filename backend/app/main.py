#!/usr/bin/env python3
"""
CodeGuard AI - Main Application

FastAPI application entry point for CodeGuard AI code analysis platform.
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from .core.config import get_settings
from .core.database import db_manager, init_db
from .core.redis_client import init_redis, close_redis
from .api import router
from .api.llm import router as llm_router
from .models import *  # Import all models to register with SQLAlchemy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('codeguard.log')
    ]
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown"""
    # Startup
    logger.info("Starting CodeGuard AI application...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Initialize Redis
        logger.info("Initializing Redis connection...")
        try:
            await init_redis()
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e} - continuing without Redis")
        
        # Test connections
        db_status = db_manager.health_check()
        try:
            from .core.redis_client import get_redis
            redis_client = get_redis()
            redis_status = await redis_client.ping() if redis_client else False
        except:
            redis_status = False
        
        if not db_status.get('status') == 'healthy':
            logger.error("Database connection failed")
            raise Exception("Database connection failed")
        
        if not redis_status:
            logger.warning("Redis connection failed - caching will be disabled")
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down CodeGuard AI application...")
        
        try:
            # Close database connections
            # Note: db_manager doesn't have a close method, connections are handled by SQLAlchemy
            logger.info("Database connections will be closed by SQLAlchemy")
            
            # Close Redis connections
            try:
                await close_redis()
                logger.info("Redis connections closed")
            except Exception as e:
                logger.warning(f"Redis close failed: {e}")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
        
        logger.info("Application shutdown completed")

# Create FastAPI application
app = FastAPI(
    title="CodeGuard AI",
    description="""
    CodeGuard AI is an advanced code analysis platform that provides:
    
    - **AI-Generated Code Detection**: Identify AI-generated code patterns
    - **Security Vulnerability Scanning**: OWASP Top 10 + AI-specific vulnerabilities
    - **Performance Analysis**: Code complexity and efficiency analysis
    - **Quality Assessment**: Maintainability and code quality scoring
    - **Multi-Language Support**: Python, JavaScript, TypeScript, and more
    
    ## Features
    
    ### Core Analysis
    - AST-based code parsing and analysis
    - Machine learning-powered AI detection
    - Comprehensive security vulnerability scanning
    - Performance bottleneck identification
    - Code quality metrics and scoring
    
    ### API Capabilities
    - RESTful API for programmatic access
    - Batch processing for multiple files
    - Real-time analysis with caching
    - Rate limiting and authentication
    - Comprehensive error handling
    
    ### Integration
    - CI/CD pipeline integration
    - Webhook support for automated analysis
    - Export capabilities for reports
    - Dashboard and visualization tools
    """,
    version="1.0.0",
    contact={
        "name": "CodeGuard AI Team",
        "email": "support@codeguard.ai",
        "url": "https://codeguard.ai"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "CodeGuard AI",
            "description": "Core code analysis endpoints"
        },
        {
            "name": "Health",
            "description": "System health and monitoring"
        },
        {
            "name": "Analysis",
            "description": "Code analysis operations"
        },
        {
            "name": "Quick Analysis",
            "description": "Fast analysis endpoints for specific metrics"
        },
        {
            "name": "History",
            "description": "Analysis history and results"
        },
        {
            "name": "Statistics",
            "description": "Usage statistics and analytics"
        },
        {
            "name": "LLM Integration",
            "description": "AI-powered code analysis and recommendations"
        }
    ],
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# Middleware Configuration

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Processing-Time"]
)

# Trusted Host Middleware
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Request/Response Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time and request ID headers"""
    import time
    import uuid
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Process request
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Processing-Time"] = str(process_time)
    
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(
        f"Response: {response.status_code} "
        f"({duration:.2f}ms) for {request.method} {request.url.path}"
    )
    
    return response

# Include API routers
app.include_router(router)
app.include_router(llm_router)

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "CodeGuard AI",
        "version": "1.0.0",
        "description": "Advanced code analysis platform with AI detection capabilities",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "analyze": "/api/v1/analyze",
            "quick_analysis": "/api/v1/quick/*",
            "history": "/api/v1/history",
            "statistics": "/api/v1/stats"
        },
        "features": [
            "AI-generated code detection",
            "Security vulnerability scanning",
            "Performance analysis",
            "Code quality assessment",
            "Multi-language support",
            "Batch processing",
            "Real-time analysis",
            "CI/CD integration"
        ]
    }

# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="CodeGuard AI API",
        version="1.0.0",
        description="Advanced code analysis platform with AI detection capabilities",
        routes=app.routes,
    )
    
    # Add custom schema extensions
    openapi_schema["info"]["x-logo"] = {
        "url": "https://codeguard.ai/logo.png"
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Global Exception Handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, 'request_id', None),
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred" if not settings.DEBUG else str(exc),
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, 'request_id', None),
            "path": request.url.path
        }
    )

# Development endpoints (only in debug mode)
if settings.DEBUG:
    @app.get("/debug/info", tags=["Debug"])
    async def debug_info():
        """Debug information endpoint"""
        return {
            "settings": {
                "debug": settings.DEBUG,
                "database_url": settings.DATABASE_URL[:20] + "..." if settings.DATABASE_URL else None,
                "redis_url": settings.REDIS_URL[:20] + "..." if settings.REDIS_URL else None,
                "allowed_origins": settings.ALLOWED_ORIGINS,
                "allowed_hosts": settings.ALLOWED_HOSTS
            },
            "system": {
                "python_version": sys.version,
                "platform": sys.platform
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/debug/test-db", tags=["Debug"])
    async def test_database():
        """Test database connection"""
        try:
            status = await database_manager.check_connection()
            return {
                "database_connected": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "database_connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @app.get("/debug/test-redis", tags=["Debug"])
    async def test_redis():
        """Test Redis connection"""
        try:
            status = await redis_client.ping()
            return {
                "redis_connected": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "redis_connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Application factory function
def create_app() -> FastAPI:
    """Application factory function"""
    return app

# For running with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True
    )