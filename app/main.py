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
from app.api.auth import router as auth_router, oauth_router
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
    
    # Get origin for CORS
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin in allow_origin_list or origin.endswith(".gistify.pro"):
        cors_headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),  # Always show error details for debugging
            "error_type": type(exc).__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
        headers=cors_headers,
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
from app.api.admin import router as admin_router, load_legal_content
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.images import router as images_router
from app.api.videos import router as videos_router
from app.api.sources import router as sources_router
from app.api.pulse import router as pulse_router
from app.api.portal import router as portal_router
# Note: Chat endpoints will be added to sources_router later
app.include_router(auth_router)
app.include_router(oauth_router)  # Google OAuth callback
app.include_router(transcription_router)
app.include_router(credits_router)
app.include_router(admin_router)
app.include_router(admin_dashboard_router)
app.include_router(images_router)
app.include_router(videos_router, prefix="/api/v1/videos", tags=["videos"])
app.include_router(sources_router)
app.include_router(pulse_router, prefix="/api/v1", tags=["pulse"])
app.include_router(portal_router, tags=["portal"])


# Public endpoint for legal content (no auth required)
@app.get("/api/v1/legal-content", tags=["public"])
async def get_public_legal_content():
    """Get legal content for public pages (no authentication required)"""
    content = load_legal_content()
    return content

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
    
    # Run PKB migration if needed
    try:
        await run_pkb_migration()
    except Exception as e:
        logger.warning(f"⚠️ PKB migration skipped: {e}")


async def run_pkb_migration():
    """Add PKB columns to sources table if they don't exist"""
    import os
    from sqlalchemy import create_engine, text
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.info("ℹ️ DATABASE_URL not set, skipping PKB migration")
        return
    
    # Skip for SQLite (local dev)
    if "sqlite" in database_url.lower():
        logger.info("ℹ️ SQLite detected, skipping PKB migration (run add_source_pkb_fields.py manually)")
        return
    
    logger.info("🔄 Running PKB migration for PostgreSQL...")
    
    pkb_fields = [
        ("pkb_enabled", "BOOLEAN DEFAULT FALSE"),
        ("pkb_status", "VARCHAR(50) DEFAULT 'not_created'"),
        ("pkb_collection_name", "VARCHAR(255)"),
        ("pkb_chunk_count", "INTEGER DEFAULT 0"),
        ("pkb_embedding_model", "VARCHAR(100)"),
        ("pkb_chunk_size", "INTEGER"),
        ("pkb_chunk_overlap", "INTEGER"),
        ("pkb_created_at", "TIMESTAMP"),
        ("pkb_credits_used", "FLOAT DEFAULT 0.0"),
        ("pkb_error_message", "TEXT"),
    ]
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check if sources table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sources'
            )
        """))
        if not result.scalar():
            logger.info("ℹ️ sources table doesn't exist yet, skipping PKB migration")
            return
        
        # Get existing columns
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sources'
        """))
        existing_columns = {row[0] for row in result.fetchall()}
        
        added = []
        for field_name, field_type in pkb_fields:
            if field_name not in existing_columns:
                try:
                    conn.execute(text(f"ALTER TABLE sources ADD COLUMN {field_name} {field_type}"))
                    added.append(field_name)
                except Exception as e:
                    logger.warning(f"⚠️ Could not add {field_name}: {e}")
        
        conn.commit()
        
        if added:
            logger.info(f"✅ PKB migration complete! Added columns: {added}")
        else:
            logger.info("✅ PKB columns already exist")
        
        # Add RAG_PKB_CREATION to operationtype enum if not exists
        try:
            # Check if enum value exists
            result = conn.execute(text("""
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'rag_pkb_creation' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'operationtype')
            """))
            if not result.fetchone():
                conn.execute(text("ALTER TYPE operationtype ADD VALUE IF NOT EXISTS 'rag_pkb_creation'"))
                conn.commit()
                logger.info("✅ Added 'rag_pkb_creation' to operationtype enum")
            else:
                logger.info("✅ operationtype enum already has 'rag_pkb_creation'")
        except Exception as e:
            logger.warning(f"⚠️ Could not add enum value: {e}")


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
    import os
    import time
    
    # Check database
    db_status = "operational" if check_db_connection() else "error"
    
    # Check Qdrant connectivity
    qdrant_status = "unknown"
    qdrant_time_ms = 0
    qdrant_url = os.environ.get("QDRANT_URL", "not_set")
    try:
        import httpx
        start = time.time()
        response = httpx.get(
            f"{qdrant_url}/collections",
            headers={"api-key": os.environ.get("QDRANT_API_KEY", "")},
            timeout=10.0
        )
        qdrant_time_ms = int((time.time() - start) * 1000)
        if response.status_code == 200:
            qdrant_status = "operational"
        else:
            qdrant_status = f"error: {response.status_code}"
    except Exception as e:
        qdrant_status = f"error: {str(e)[:100]}"
    
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
            "qdrant": {
                "status": qdrant_status,
                "url": qdrant_url,
                "response_time_ms": qdrant_time_ms
            },
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
    
    # Test Redis connection and show ALL queues
    try:
        import redis
        from app.settings import get_settings
        settings = get_settings()
        broker_url = settings.CELERY_BROKER_URL
        
        # Parse Redis URL
        r = redis.from_url(broker_url)
        ping_result = r.ping()
        
        # Check ALL queue lengths
        queues = {
            "celery": r.llen("celery"),
            "high": r.llen("high"),
            "default": r.llen("default"),
            "low": r.llen("low")
        }
        
        result["redis_test"] = {
            "status": "connected",
            "ping": ping_result,
            "broker_url": broker_url[:50] + "..." if len(broker_url) > 50 else broker_url,
            "queue_lengths": queues,
            "total_pending": sum(queues.values())
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


@app.post("/api/v1/debug/purge-queues")
async def purge_queues():
    """Purge all Celery queues - USE WITH CAUTION"""
    try:
        import redis
        from app.settings import get_settings
        settings = get_settings()
        r = redis.from_url(settings.CELERY_BROKER_URL)
        
        # Get counts before purge
        before = {
            "celery": r.llen("celery"),
            "high": r.llen("high"),
            "default": r.llen("default")
        }
        
        # Purge queues
        r.delete("celery", "high", "default", "low")
        
        return {
            "status": "purged",
            "queues_cleared": before
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


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

