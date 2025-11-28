"""
MP4toText Backend API
FastAPI application main entry point with proper exception handling
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime
import logging
from typing import Dict, Any
from pathlib import Path

from app.database import init_db, check_db_connection
from app.api.auth import router as auth_router
from app.api.transcription import router as transcription_router
from app.api.credits import router as credits_router
from app.websocket import setup_websocket
from app.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()
settings_cors_origins = getattr(settings, "CORS_ORIGINS", []) or []

# Compute CORS origins dynamically so credentials can be used safely.
default_cors_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
}

allow_origin_list = sorted(set(settings_cors_origins) | default_cors_origins)

# Create FastAPI app
app = FastAPI(
    title="MP4toText API",
    description="Audio/Video transcription and speaker recognition API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# REQUEST LOGGING MIDDLEWARE - Debug every incoming request
# ============================================================================

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """
    Log EVERY incoming request - helps diagnose CORS and routing issues
    """
    logger.info(
        f"🔵 INCOMING: {request.method} {request.url} | "
        f"Origin: {request.headers.get('origin', 'NO ORIGIN')} | "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    # Log all headers in debug mode
    if settings.is_development:
        logger.debug(f"📋 Request Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    logger.info(
        f"🟢 RESPONSE: {request.method} {request.url.path} -> {response.status_code}"
    )
    
    return response


# ============================================================================
# CRITICAL: EXCEPTION HANDLERS FIRST - MUST BE DEFINED BEFORE MIDDLEWARE
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler - catches ALL unhandled exceptions
    
    This MUST be defined before CORS middleware to ensure CORS headers
    are added to error responses.
    """
    logger.error(
        f"Global exception handler caught: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "client": request.client.host if request.client else None,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred. Please try again later.",
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            # Only include error details in development
            **({"error_details": str(exc)} if settings.is_development else {})
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, 
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    HTTP exception handler - handles HTTPException instances
    
    This ensures CORS headers are present even for HTTP errors like 404, 401, etc.
    """
    logger.warning(
        f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
        headers=getattr(exc, 'headers', None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """
    Validation error handler - handles Pydantic validation errors
    
    Returns 422 Unprocessable Entity with detailed validation errors
    """
    # Clean errors to remove non-JSON-serializable values (e.g., bytes)
    errors = []
    for error in exc.errors():
        cleaned_error = {}
        for key, value in error.items():
            if isinstance(value, bytes):
                cleaned_error[key] = f"<bytes: {len(value)} bytes>"
            elif key == "input" and isinstance(value, dict):
                # Skip large file data in validation errors
                cleaned_error[key] = {k: v for k, v in value.items() if not isinstance(v, bytes)}
            else:
                cleaned_error[key] = value
        errors.append(cleaned_error)
    
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {len(errors)} error(s) - {errors}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


# ============================================================================
# CORS MIDDLEWARE - MUST COME AFTER EXCEPTION HANDLERS
# ============================================================================

logger.info(f"🌐 Allowed CORS origins: ALL ORIGINS + localhost:5173")

# Configure CORS (must be registered before routers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# Include routers
from app.api.admin import router as admin_router
from app.api.images import router as images_router
from app.api.videos import router as videos_router
app.include_router(auth_router)
app.include_router(transcription_router)
app.include_router(credits_router)
app.include_router(admin_router)
app.include_router(images_router)
app.include_router(videos_router, prefix="/api/v1/videos", tags=["videos"])

# Setup WebSocket
setup_websocket(app)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("🚀 MP4toText API Starting...")
    logger.info("📝 API Documentation: http://localhost:8000/docs")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
        
        if check_db_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️  Database connection failed")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("👋 MP4toText API Shutting down...")


@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Root endpoint - API bilgileri
    """
    return {
        "message": "MP4toText Backend API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    Sistem sağlık durumunu kontrol eder
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "mp4totext-api",
        "version": "1.0.0"
    }


@app.get("/api/v1/status")
async def api_status() -> Dict[str, Any]:
    """
    API status endpoint
    Detaylı sistem durumu bilgisi - Database, Redis, Celery worker kontrolü
    """
    from app.celery_config import celery_app
    
    # Check database
    db_status = "operational" if check_db_connection() else "error"
    
    # Check Celery worker
    celery_status = "error"
    celery_workers = []
    registered_tasks = []
    try:
        # Inspect active workers
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            celery_status = "operational"
            celery_workers = list(stats.keys())
        else:
            celery_status = "error"
        
        # Get registered tasks
        registered = inspect.registered()
        if registered:
            for worker, tasks in registered.items():
                registered_tasks = tasks
                break
    except Exception as e:
        logger.warning(f"⚠️ Celery worker check failed: {e}")
        celery_status = "error"
    
    return {
        "api": {
            "status": "operational",
            "version": "1.0.0",
            "uptime": "running"
        },
        "services": {
            "database": db_status,
            "celery": {
                "status": celery_status,
                "workers": celery_workers,
                "registered_tasks": registered_tasks,
                "message": "Celery worker is running" if celery_status == "operational" else "⚠️ Celery worker is not running! Start it with: celery -A app.workers.transcription_worker worker --loglevel=info --pool=solo"
            }
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/debug/processes")
async def debug_processes() -> Dict[str, Any]:
    """
    Debug endpoint - running processes in container
    """
    import subprocess
    import os
    
    result = {
        "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
        "pid": os.getpid(),
        "processes": [],
        "celery_import_test": None
    }
    
    # List processes
    try:
        ps_output = subprocess.check_output(["ps", "aux"], text=True)
        result["processes"] = ps_output.split("\n")[:20]  # First 20 lines
    except Exception as e:
        result["processes"] = [f"Error: {e}"]
    
    # Test celery import
    try:
        from app.workers.transcription_worker import generate_transcript_images
        result["celery_import_test"] = {
            "status": "success",
            "task_name": generate_transcript_images.name
        }
    except Exception as e:
        result["celery_import_test"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test Redis connection
    try:
        import redis
        from app.settings import get_settings
        settings = get_settings()
        broker_url = settings.CELERY_BROKER_URL
        
        # Parse Redis URL
        r = redis.from_url(broker_url)
        ping_result = r.ping()
        
        # Check queue length
        queue_length = r.llen("celery")
        
        result["redis_test"] = {
            "status": "connected",
            "ping": ping_result,
            "broker_url": broker_url[:50] + "..." if len(broker_url) > 50 else broker_url,
            "celery_queue_length": queue_length
        }
    except Exception as e:
        result["redis_test"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test Celery broker connection
    try:
        from app.celery_app import celery_app
        inspector = celery_app.control.inspect()
        
        # Get active tasks
        active = inspector.active()
        reserved = inspector.reserved()
        
        result["celery_broker_test"] = {
            "status": "connected",
            "active_tasks": active,
            "reserved_tasks": reserved
        }
    except Exception as e:
        result["celery_broker_test"] = {
            "status": "error", 
            "error": str(e)
        }
    
    return result


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 error handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint does not exist",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500 error handler"""
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


# Serve WebSocket test HTML
@app.get("/websocket_test")
async def websocket_test():
    """Serve WebSocket test client"""
    html_path = Path(__file__).parent.parent / "websocket_test.html"
    if html_path.exists():
        return FileResponse(html_path)
    raise HTTPException(status_code=404, detail="Test page not found")


if __name__ == "__main__":
    import uvicorn
    import os
    import sys
    
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("""
    ╔════════════════════════════════════════╗
    ║     MP4toText Backend API v1.0.0       ║
    ╚════════════════════════════════════════╝
    
    🚀 Server starting...
    📝 Docs: http://localhost:8000/docs
    🔍 ReDoc: http://localhost:8000/redoc
    ❤️  Health: http://localhost:8000/health
    
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        app_dir=os.path.dirname(os.path.abspath(__file__))
    )

