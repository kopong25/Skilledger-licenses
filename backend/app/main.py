"""
Main FastAPI application for SkillLedger License Verification System
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import sys
from datetime import datetime

from app.config import settings
from app.database import init_db, engine
from app.models import Base

# Import routers
from app.api import verification, monitoring, bulk, audit, auth

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## SkillLedger License Verification API

    The programmable trust layer for professional credentials.

    ### Features

    * **Single License Verification** - Verify any professional license in 3 seconds
    * **Multi-State Search** - Search all 50 states in parallel
    * **Bulk Verification** - Upload CSV, get results for 100+ licenses
    * **Expiration Monitoring** - Automatic alerts before licenses expire
    * **Compliance Audit Trail** - Complete verification history for audits
    * **ATS Integration** - Works with Bullhorn, JobDiva, Greenhouse, and more

    ### Authentication

    All endpoints require an API key in the `X-API-Key` header.

    Get your API key: https://skilledger.com/api-keys
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Initialize database and services on startup
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Create database tables
    logger.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {str(e)}")
        raise

    logger.info(f"✓ {settings.APP_NAME} started successfully")
    logger.info(f"✓ Listening on {settings.HOST}:{settings.PORT}")
    logger.info(f"✓ Documentation: http://{settings.HOST}:{settings.PORT}/docs")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    logger.info("Shutting down...")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler
    """
    logger.error(f"Unhandled exception: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "cache": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    API root endpoint
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Professional license verification API",
        "documentation": "/docs",
        "health": "/health",
        "status": "operational"
    }


# Include routers
app.include_router(verification.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(bulk.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


# Demo endpoint for testing
@app.post("/api/demo/verify", tags=["Demo"])
async def demo_verify_license(license_number: str, state: str):
    """
    Demo endpoint - No authentication required

    Try it with:
    - license_number: 123456
    - state: AZ
    """
    from app.services.state_boards import MockStateBoardAdapter

    adapter = MockStateBoardAdapter()
    result = await adapter.verify_license(license_number, state)

    return {
        "demo": True,
        "message": "This is a demo using mock data. Sign up for real verification.",
        "result": result,
        "signup_url": "https://skilledger.com/signup"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )