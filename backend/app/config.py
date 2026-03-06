"""
Configuration management for SkillLedger License Verification System
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = "SkillLedger Licenses"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Database
    DATABASE_URL: str
    
    # Redis (for caching and task queue)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AWS S3 (for screenshot storage)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "skilledger-screenshots"
    
    # External APIs (State Boards)
    NURSYS_API_KEY: Optional[str] = None
    NURSYS_API_URL: str = "https://www.nursys.com/api/v1"
    
    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    FROM_EMAIL: str = "noreply@skilledger.com"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Background Workers
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Monitoring
    ENABLE_DAILY_CHECKS: bool = True
    MONITORING_CHECK_HOUR: int = 2  # 2 AM UTC
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    # Render.com specific
    PORT: int = 10000
    HOST: str = "0.0.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance
    """
    return Settings()


# Global settings instance
settings = get_settings()
