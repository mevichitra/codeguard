#!/usr/bin/env python3
"""
CodeGuard AI - Configuration Management

This module handles all configuration settings for the CodeGuard AI application,
including database connections, API keys, and feature flags.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "CodeGuard AI"
    VERSION: str = "1.0.0-MVP"
    DEBUG: bool = Field(default=True, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Security
    SECRET_KEY: str = Field(
        default="codeguard-ai-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALGORITHM: str = "HS256"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ],
        env="ALLOWED_ORIGINS"
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./codeguard.db",
        env="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_EXPIRE_SECONDS: int = Field(default=3600, env="REDIS_EXPIRE_SECONDS")
    
    # AI/ML Configuration
    ML_MODEL_PATH: str = Field(
        default="./models",
        env="ML_MODEL_PATH"
    )
    AI_DETECTION_THRESHOLD: float = Field(default=0.7, env="AI_DETECTION_THRESHOLD")
    VULNERABILITY_CONFIDENCE_THRESHOLD: float = Field(
        default=0.6,
        env="VULNERABILITY_CONFIDENCE_THRESHOLD"
    )
    
    # LLM Integration
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4", env="OPENAI_MODEL")
    LLM_ENABLED: bool = Field(default=False, env="LLM_ENABLED")
    LLM_RATE_LIMIT: int = Field(default=1000, env="LLM_RATE_LIMIT")  # requests per hour
    
    # Analysis Configuration
    MAX_FILE_SIZE_MB: int = Field(default=10, env="MAX_FILE_SIZE_MB")
    MAX_ANALYSIS_TIME_SECONDS: int = Field(default=30, env="MAX_ANALYSIS_TIME_SECONDS")
    SUPPORTED_LANGUAGES: List[str] = Field(
        default=["python", "javascript", "java", "cpp", "typescript", "go", "rust"],
        env="SUPPORTED_LANGUAGES"
    )
    
    # Security Scanner Configuration
    ENABLE_SQL_INJECTION_DETECTION: bool = Field(default=True, env="ENABLE_SQL_INJECTION_DETECTION")
    ENABLE_XSS_DETECTION: bool = Field(default=True, env="ENABLE_XSS_DETECTION")
    ENABLE_AUTH_FLAW_DETECTION: bool = Field(default=True, env="ENABLE_AUTH_FLAW_DETECTION")
    ENABLE_CRYPTO_DETECTION: bool = Field(default=True, env="ENABLE_CRYPTO_DETECTION")
    ENABLE_BUSINESS_LOGIC_DETECTION: bool = Field(default=True, env="ENABLE_BUSINESS_LOGIC_DETECTION")
    ENABLE_RESOURCE_EXHAUSTION_DETECTION: bool = Field(default=True, env="ENABLE_RESOURCE_EXHAUSTION_DETECTION")
    
    # Performance Analysis
    COMPLEXITY_THRESHOLD_WARNING: int = Field(default=10, env="COMPLEXITY_THRESHOLD_WARNING")
    COMPLEXITY_THRESHOLD_ERROR: int = Field(default=20, env="COMPLEXITY_THRESHOLD_ERROR")
    MEMORY_USAGE_THRESHOLD_MB: int = Field(default=100, env="MEMORY_USAGE_THRESHOLD_MB")
    
    # Code Quality
    MIN_QUALITY_SCORE: int = Field(default=60, env="MIN_QUALITY_SCORE")
    MAINTAINABILITY_THRESHOLD: float = Field(default=70.0, env="MAINTAINABILITY_THRESHOLD")
    DUPLICATION_THRESHOLD_PERCENT: float = Field(default=10.0, env="DUPLICATION_THRESHOLD_PERCENT")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    # Feature Flags
    ENABLE_AI_DETECTION: bool = Field(default=True, env="ENABLE_AI_DETECTION")
    ENABLE_SECURITY_SCANNER: bool = Field(default=True, env="ENABLE_SECURITY_SCANNER")
    ENABLE_PERFORMANCE_ANALYSIS: bool = Field(default=True, env="ENABLE_PERFORMANCE_ANALYSIS")
    ENABLE_QUALITY_ASSESSMENT: bool = Field(default=True, env="ENABLE_QUALITY_ASSESSMENT")
    ENABLE_REAL_TIME_ANALYSIS: bool = Field(default=True, env="ENABLE_REAL_TIME_ANALYSIS")
    
    # Development
    ENABLE_DEMO_DATA: bool = Field(default=True, env="ENABLE_DEMO_DATA")
    ENABLE_TEST_ENDPOINTS: bool = Field(default=True, env="ENABLE_TEST_ENDPOINTS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def get_database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return self.DATABASE_URL
    
    def get_redis_url(self) -> str:
        """Get the Redis URL for connection."""
        return self.REDIS_URL
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.DEBUG
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages."""
        return self.SUPPORTED_LANGUAGES
    
    def is_llm_enabled(self) -> bool:
        """Check if LLM integration is enabled and configured."""
        return self.LLM_ENABLED and self.OPENAI_API_KEY is not None
    
    def get_analysis_features(self) -> dict:
        """Get enabled analysis features."""
        return {
            "ai_detection": self.ENABLE_AI_DETECTION,
            "security_scanner": self.ENABLE_SECURITY_SCANNER,
            "performance_analysis": self.ENABLE_PERFORMANCE_ANALYSIS,
            "quality_assessment": self.ENABLE_QUALITY_ASSESSMENT,
            "real_time_analysis": self.ENABLE_REAL_TIME_ANALYSIS
        }
    
    def get_security_features(self) -> dict:
        """Get enabled security detection features."""
        return {
            "sql_injection": self.ENABLE_SQL_INJECTION_DETECTION,
            "xss": self.ENABLE_XSS_DETECTION,
            "auth_flaws": self.ENABLE_AUTH_FLAW_DETECTION,
            "crypto_issues": self.ENABLE_CRYPTO_DETECTION,
            "business_logic": self.ENABLE_BUSINESS_LOGIC_DETECTION,
            "resource_exhaustion": self.ENABLE_RESOURCE_EXHAUSTION_DETECTION
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Export settings instance
settings = get_settings()