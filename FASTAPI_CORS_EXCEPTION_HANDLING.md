# 🎯 FastAPI CORS + Exception Handling Complete Guide

## 🔑 Core Problem Understanding

**WHY CORS errors appear when backend throws 500 errors:**

```
Request Flow (BROKEN):
Browser → Preflight OPTIONS → ✅ CORS OK
Browser → POST Request → Exception in handler → 500 Internal Server Error
                       → Response terminates BEFORE reaching CORS middleware
                       → Browser sees no CORS headers → SHOWS CORS ERROR
```

**The fix:** Catch exceptions BEFORE they become 500 errors!

```
Request Flow (FIXED):
Browser → Preflight OPTIONS → ✅ CORS OK  
Browser → POST Request → Exception in handler 
                       → Global exception handler catches it
                       → Returns proper JSON response with CORS headers
                       → Browser gets response with CORS headers → ✅ SUCCESS
```

## 🏗️ Complete FastAPI Application Structure

### 1. Main Application with Proper Middleware Order

```python
"""
app/main.py - Complete FastAPI application with proper exception handling
"""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Any, Dict
from datetime import datetime

from app.config import get_settings
from app.database import init_db, check_db_connection
from app.api.auth import router as auth_router
from app.api.transcription import router as transcription_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="MP4toText API",
    description="Audio/Video transcription and speaker recognition API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


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
    
    # Return a proper JSON response
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
        headers=exc.headers if hasattr(exc, 'headers') and exc.headers else None,
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
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc.errors()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": exc.body if hasattr(exc, 'body') else None,
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
        },
    )


# ============================================================================
# CORS MIDDLEWARE - MUST COME AFTER EXCEPTION HANDLERS
# ============================================================================

# Compute allowed origins
settings_cors_origins = getattr(settings, "CORS_ORIGINS", []) or []

# Default localhost origins for development
default_cors_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
}

# Merge settings origins with defaults
allow_origin_list = sorted(set(settings_cors_origins) | default_cors_origins)

logger.info(f"🌐 Allowed CORS origins: {allow_origin_list}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origin_list,  # NEVER use ["*"] with credentials!
    allow_credentials=True,  # Required for JWT cookies/auth headers
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers to browser
    max_age=600,  # Cache preflight requests for 10 minutes
)


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 MP4toText API Starting...")
    logger.info(f"📝 API Documentation: http://localhost:8000/docs")
    logger.info(f"🔧 Environment: {settings.APP_ENV}")
    logger.info(f"🐛 Debug Mode: {settings.DEBUG}")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    # Check database connection
    if await check_db_connection():
        logger.info("✅ Database connection successful")
    else:
        logger.error("❌ Database connection failed")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("👋 MP4toText API Shutting down...")


# ============================================================================
# HEALTH CHECK ENDPOINT (NO AUTH REQUIRED)
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    
    Returns API status and basic information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mp4totext-api",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


# ============================================================================
# INCLUDE ROUTERS - MUST BE LAST
# ============================================================================

app.include_router(auth_router)
app.include_router(transcription_router)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information"""
    return {
        "message": "MP4toText API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
```

### 2. Celery Error Handling with Graceful Degradation

```python
"""
app/api/transcription.py - Transcription endpoints with Celery error handling
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import logging

from app.database import get_db
from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus
from app.schemas.transcription import TranscriptionCreate, TranscriptionResponse
from app.auth.utils import get_current_active_user
from app.services.storage import get_storage_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/transcriptions", tags=["Transcriptions"])

# Try to import Celery task
try:
    from app.workers.transcription_worker import process_transcription_task
    CELERY_AVAILABLE = True
    logger.info("✅ Celery worker module imported successfully")
except ImportError as e:
    CELERY_AVAILABLE = False
    logger.warning(f"⚠️ Celery not available: {e}")


@router.post("/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    data: TranscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage_service)
) -> TranscriptionResponse:
    """
    Create transcription job with proper Celery error handling
    """
    # Verify file exists
    file_path = storage.get_file_path(data.file_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {data.file_id}"
        )
    
    # Get file info
    file_size = storage.get_file_size(data.file_id)
    filename = file_path.name
    
    # Create transcription job
    transcription = Transcription(
        user_id=current_user.id,
        file_id=data.file_id,
        filename=filename,
        file_size=file_size,
        file_path=str(file_path),
        content_type="audio/mpeg",
        language=data.language,
        whisper_model=data.whisper_model.value,
        use_speaker_recognition=data.use_speaker_recognition,
        use_gemini_enhancement=data.use_gemini_enhancement,
        status=TranscriptionStatus.PENDING
    )
    
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # ========================================================================
    # CRITICAL: Celery error handling with graceful degradation
    # ========================================================================
    
    if CELERY_AVAILABLE:
        try:
            # Try to dispatch Celery task
            task = process_transcription_task.delay(transcription.id)
            logger.info(
                f"🚀 Celery task {task.id} started for transcription {transcription.id}"
            )
            
        except Exception as celery_error:
            # Celery dispatch failed (likely Redis connection error)
            logger.error(
                f"❌ Celery dispatch failed for transcription {transcription.id}: {celery_error}",
                exc_info=True
            )
            
            # Check if it's a connection error
            error_type = type(celery_error).__name__
            is_connection_error = any(
                err in error_type.lower() 
                for err in ['connection', 'operational', 'timeout']
            )
            
            if settings.is_development and is_connection_error:
                # DEVELOPMENT: Fallback to synchronous processing
                logger.warning(
                    f"⚠️ Development mode: Falling back to synchronous processing "
                    f"for transcription {transcription.id}"
                )
                
                try:
                    # Run task synchronously (blocking!)
                    result = process_transcription_task.apply(
                        args=(transcription.id,)
                    ).get(timeout=300)  # 5 minute timeout
                    logger.info(f"✅ Sync processing completed: {result}")
                    
                except Exception as sync_error:
                    logger.error(
                        f"❌ Sync processing failed: {sync_error}",
                        exc_info=True
                    )
                    # Update transcription status
                    transcription.status = TranscriptionStatus.FAILED
                    transcription.error_message = f"Processing failed: {sync_error}"
                    db.commit()
                    
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Transcription processing failed: {sync_error}"
                    )
            else:
                # PRODUCTION: Return 503 Service Unavailable
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Background processing service is currently unavailable. "
                        "Please try again in a few moments."
                    ),
                    headers={"Retry-After": "60"}  # Suggest retry after 60 seconds
                )
    else:
        # Celery module not available at all
        logger.warning(
            f"⚠️ Celery not available. Transcription {transcription.id} "
            f"created but not processed. Use /api/v1/transcriptions/{transcription.id}/process"
        )
    
    return transcription
```

### 3. Frontend Axios Configuration

```typescript
// src/config/api.ts - Axios instance with proper error handling

import axios, { AxiosError, AxiosResponse } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create Axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  withCredentials: true, // CRITICAL for JWT cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError<any>) => {
    // DISTINGUISH between network errors and HTTP errors
    if (error.response) {
      // HTTP error response from server (400, 500, etc.)
      const status = error.response.status;
      const data = error.response.data;
      
      console.error(`HTTP ${status} Error:`, {
        url: error.config?.url,
        method: error.config?.method,
        status,
        detail: data?.detail || data?.message,
        errors: data?.errors,
      });
      
      // Handle specific status codes
      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          console.warn('Authentication failed. Redirecting to login...');
          localStorage.removeItem('access_token');
          window.location.href = '/login';
          break;
          
        case 403:
          console.error('Access forbidden');
          break;
          
        case 404:
          console.error('Resource not found');
          break;
          
        case 422:
          console.error('Validation error:', data?.errors);
          break;
          
        case 500:
          console.error('Internal server error:', data?.detail);
          break;
          
        case 503:
          console.warn('Service temporarily unavailable:', data?.detail);
          // You could show a retry UI here
          break;
      }
      
    } else if (error.request) {
      // Request made but no response (network error, CORS, etc.)
      console.error('Network Error - No response from server:', {
        url: error.config?.url,
        method: error.config?.method,
        message: error.message,
      });
      
      // Check if it's a CORS error (though we can't know for sure)
      if (error.message === 'Network Error') {
        console.error(
          '🚨 Network Error - Possible causes:\n' +
          '1. Backend server is down\n' +
          '2. CORS not properly configured\n' +
          '3. Backend returned 500 error (check backend logs)\n' +
          '4. Firewall/network issue'
        );
      }
      
    } else {
      // Something else happened
      console.error('Request setup error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

### 4. Vite Proxy Configuration (Alternative/Backup)

```typescript
// vite.config.ts - Proxy to avoid CORS during development

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  
  server: {
    port: 5173,
    
    // PROXY CONFIGURATION - Forwards /api requests to backend
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // rewrite: (path) => path.replace(/^\/api/, ''),  // Remove /api prefix if needed
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
```

Then update your Axios base URL:

```typescript
// When using proxy, use relative URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
```

## 🧪 Testing & Verification

### PowerShell Test Commands

```powershell
# 1. Test CORS Preflight (OPTIONS request)
curl.exe -I -X OPTIONS http://localhost:8000/api/v1/transcriptions/ `
  -H "Origin: http://localhost:5173" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: authorization,content-type"

# Expected response headers:
# access-control-allow-origin: http://localhost:5173
# access-control-allow-credentials: true
# access-control-allow-methods: *
# access-control-allow-headers: *


# 2. Test actual POST request with CORS headers
curl.exe -v -X POST http://localhost:8000/api/v1/transcriptions/ `
  -H "Origin: http://localhost:5173" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN_HERE" `
  -d '{\"file_id\":\"test\",\"language\":\"tr\"}'

# Should see CORS headers even if it returns 404/422/500


# 3. Test exception handler (should return JSON with CORS headers)
curl.exe -v http://localhost:8000/api/v1/nonexistent `
  -H "Origin: http://localhost:5173"

# Should return 404 with CORS headers


# 4. Check Docker services
docker ps --filter "name=mp4totext" --format "table {{.Names}}\t{{.Status}}"


# 5. Test Redis connection
docker exec mp4totext-redis redis-cli -a dev_redis_123 ping
# Should return: PONG


# 6. Test PostgreSQL connection
docker exec mp4totext-postgres pg_isready -U dev_user
# Should return: accepting connections


# 7. Backend health check
curl.exe http://localhost:8000/health
# Should return JSON with status: healthy


# 8. Run diagnostic script
.\debug_backend_clean.ps1
```

## 🎓 Critical Concepts Explained

### 1. Why Middleware Order Matters

```python
# ❌ WRONG ORDER - CORS added before exception handlers defined
app.add_middleware(CORSMiddleware, ...)
app.include_router(router)

# Exception in route → 500 error → No CORS headers → Browser shows CORS error


# ✅ CORRECT ORDER - Exception handlers defined first
@app.exception_handler(Exception)
async def global_handler(...):  # Defined FIRST
    return JSONResponse(...)

app.add_middleware(CORSMiddleware, ...)  # Added SECOND
app.include_router(router)  # Routes LAST

# Exception in route → Caught by handler → Returns JSONResponse 
# → CORS middleware adds headers → Browser gets response with CORS headers
```

### 2. Why allow_origins=["*"] Doesn't Work with Credentials

```python
# ❌ WRONG - Browser rejects this combination
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wildcard
    allow_credentials=True,  # Credentials enabled
)
# Browser error: "Wildcard is not allowed when credentials flag is true"


# ✅ CORRECT - Explicit origin list
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
)
```

### 3. Why localhost AND 127.0.0.1 Need Separate Entries

```python
# Browser treats these as DIFFERENT origins:
# - http://localhost:5173
# - http://127.0.0.1:5173

# If you only allow localhost, requests from 127.0.0.1 will fail CORS
# If you only allow 127.0.0.1, requests from localhost will fail CORS

# ✅ SOLUTION: Include both
allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
```

### 4. Exception Handler Return Type

```python
# ❌ WRONG - Returning dict (FastAPI auto-converts to JSONResponse)
@app.exception_handler(Exception)
async def handler(request, exc):
    return {"error": str(exc)}  # This skips CORS middleware!


# ✅ CORRECT - Explicitly return JSONResponse
@app.exception_handler(Exception)
async def handler(request, exc):
    return JSONResponse(  # CORS middleware processes this
        status_code=500,
        content={"error": str(exc)}
    )
```

## 🐛 Common Pitfalls

### 1. Forgetting to Import JSONResponse

```python
# ❌ Missing import
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Exception handler tries to use JSONResponse
return JSONResponse(...)  # NameError!


# ✅ Correct imports
from fastapi import FastAPI
from fastapi.responses import JSONResponse  # Add this!
from fastapi.middleware.cors import CORSMiddleware
```

### 2. Using raise instead of return in Exception Handlers

```python
# ❌ WRONG - Re-raising exception
@app.exception_handler(Exception)
async def handler(request, exc):
    logger.error(f"Error: {exc}")
    raise exc  # This creates a new 500 error!


# ✅ CORRECT - Return JSONResponse
@app.exception_handler(Exception)
async def handler(request, exc):
    logger.error(f"Error: {exc}")
    return JSONResponse(  # Properly handled response
        status_code=500,
        content={"error": str(exc)}
    )
```

### 3. Not Catching Specific Celery Exceptions

```python
# ❌ TOO BROAD - Catches everything
try:
    task = process_transcription_task.delay(id)
except Exception as e:
    # Can't tell if it's a connection error or something else
    pass


# ✅ SPECIFIC - Handle connection errors differently
try:
    task = process_transcription_task.delay(id)
except (ConnectionRefusedError, OperationalError) as conn_error:
    # Redis is down - handle gracefully
    if settings.is_development:
        # Fallback to sync
        task.apply(args=(id,))
    else:
        # Return 503
        raise HTTPException(status_code=503, ...)
except Exception as other_error:
    # Other errors
    logger.error(f"Unexpected error: {other_error}")
    raise
```

### 4. Forgetting to Clear Browser Cache

```bash
# After fixing CORS, browser still shows old cached preflight response
# Solution:
# 1. Ctrl + Shift + Delete → Clear cache
# 2. Or use Incognito: Ctrl + Shift + N
# 3. Or hard refresh: Ctrl + Shift + R (doesn't always work for preflight)
```

## 📊 Decision Tree

```
Is backend responding?
├─ NO → Start backend: .\venv\Scripts\python.exe -m uvicorn app.main:app --reload
│
└─ YES → Does curl preflight show CORS headers?
    ├─ NO → Check middleware order (exception handlers before CORS)
    │
    └─ YES → Does actual POST request show CORS headers?
        ├─ NO → Backend returning 500 before CORS middleware
        │      → Check backend logs for exceptions
        │      → Add global exception handler
        │
        └─ YES → Browser still shows CORS error?
            ├─ Clear browser cache (Ctrl+Shift+Delete)
            ├─ Try Incognito mode (Ctrl+Shift+N)
            └─ Check if request origin matches allowed origins exactly
```

## 🎯 Checklist for CORS + Exception Handling

- [ ] Exception handlers defined BEFORE `app.add_middleware()`
- [ ] Exception handlers return `JSONResponse`, not dict
- [ ] CORS middleware uses explicit origin list (not `["*"]`)
- [ ] Both `localhost` and `127.0.0.1` in allowed origins
- [ ] `allow_credentials=True` is set
- [ ] Celery errors caught and handled gracefully
- [ ] Development mode has sync fallback
- [ ] Production mode returns 503 for Celery errors
- [ ] Backend logs exceptions properly
- [ ] Frontend distinguishes network vs HTTP errors
- [ ] Browser cache cleared after CORS changes

## 📚 Additional Resources

- [FastAPI Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Starlette Middleware](https://www.starlette.io/middleware/)
- [CORS Specification](https://fetch.spec.whatwg.org/#http-cors-protocol)
- [MDN: Preflight Requests](https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request)

---

**Last Updated:** October 21, 2025  
**Status:** ✅ Complete production-ready solution with exception handling and CORS
