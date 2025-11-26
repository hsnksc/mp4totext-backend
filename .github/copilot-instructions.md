# MP4toText Backend Instructions

You are working on **MP4toText Backend** - a production-ready FastAPI transcription service with advanced features:

## 🎯 System Overview

**MP4toText Backend** is an enterprise-grade audio/video transcription API with:
- 🎙️ Multi-provider transcription (OpenAI Whisper, AssemblyAI, Faster-Whisper)
- 🗣️ Advanced speaker diarization (pyannote.audio 3.1 via Modal GPU)
- 🤖 Multiple AI enhancement providers (Gemini, OpenAI, Groq, Together AI)
- 🖼️ AI image generation (Modal FLUX H100, SDXL, Replicate Imagen-4)
- 🎬 Automated video generation from transcripts
- 💰 Sophisticated credit system with per-operation pricing
- 🔄 Real-time WebSocket updates
- 🌐 Multi-language support (50+ languages)

## 🏗️ Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│   Client    │─────▶│ FastAPI:8002 │─────▶│ Celery Workers  │
│  (Web/App)  │      │   + CORS     │      │  (Background)   │
└─────────────┘      └──────┬───────┘      └────────┬────────┘
                            │                       │
                     ┌──────▼───────┐      ┌───────▼─────────┐
                     │ SQLite DB    │      │ Redis (Broker)  │
                     │ (mp4totext)  │      │  DB 1: Tasks    │
                     └──────────────┘      │  DB 2: Results  │
                                           └─────────────────┘
                            │
                     ┌──────▼──────────┐
                     │ MinIO Storage   │
                     │ (S3-compatible) │
                     └─────────────────┘
                            │
                     ┌──────▼──────────────┐
                     │  WebSocket Manager  │
                     │ (Real-time updates) │
                     └─────────────────────┘
```

## 📁 Project Structure

```
mp4totext-backend/
├── app/
│   ├── main.py                      # FastAPI app entry + middleware
│   ├── database.py                  # SQLAlchemy setup
│   ├── settings.py                  # Environment config
│   ├── celery_app.py                # Celery app instance
│   ├── celery_config.py             # Celery configuration
│   ├── websocket.py                 # WebSocket manager
│   │
│   ├── api/                         # API Routers (6 modules)
│   │   ├── auth.py                  # JWT auth, login, register
│   │   ├── transcription.py         # Upload, transcribe, status
│   │   ├── credits.py               # Credit balance, history, pricing
│   │   ├── images.py                # Image generation
│   │   ├── videos.py                # Video generation
│   │   └── admin.py                 # Admin endpoints
│   │
│   ├── models/                      # SQLAlchemy ORM Models
│   │   ├── user.py                  # User model (credits, role)
│   │   ├── transcription.py         # Transcription model (main)
│   │   ├── credit_transaction.py    # Credit transaction log
│   │   ├── credit_pricing.py        # Dynamic pricing config
│   │   ├── ai_model_pricing.py      # AI model cost multipliers
│   │   ├── generated_image.py       # Generated image records
│   │   └── generated_video.py       # Generated video records
│   │
│   ├── services/                    # Business Logic Layer
│   │   ├── audio_processor.py       # Audio file processing
│   │   ├── credit_service.py        # Credit management
│   │   ├── storage.py               # MinIO file storage
│   │   ├── language_detector.py     # Language detection
│   │   │
│   │   ├── whisper_service.py       # OpenAI Whisper transcription
│   │   ├── faster_whisper_service.py # Faster-Whisper (optimized)
│   │   ├── assemblyai_service.py    # AssemblyAI cloud API
│   │   │
│   │   ├── gemini_service.py        # Google Gemini AI
│   │   ├── groq_service.py          # Groq LLM
│   │   ├── together_service.py      # Together AI
│   │   ├── openai_cleaner_service.py # OpenAI text cleaning
│   │   │
│   │   ├── image_generator.py       # Image generation manager
│   │   ├── modal_flux_service.py    # Modal FLUX H100
│   │   ├── modal_sd_service.py      # Modal Stable Diffusion
│   │   ├── replicate_imagen_service.py # Replicate Imagen-4
│   │   │
│   │   ├── video_generator.py       # Video generation pipeline
│   │   ├── video_assembly.py        # FFmpeg video assembly
│   │   │
│   │   ├── speaker_recognition.py   # Speaker diarization
│   │   ├── web_search_service.py    # Tavily web search
│   │   └── youtube_service.py       # YouTube download
│   │
│   ├── workers/                     # Celery Background Tasks
│   │   ├── transcription_worker.py  # Main worker (3 tasks)
│   │   └── tasks/                   # Task modules
│   │
│   ├── schemas/                     # Pydantic Schemas
│   │   ├── transcription.py         # Request/response models
│   │   └── user.py                  # User schemas
│   │
│   └── auth/                        # Authentication
│       └── utils.py                 # JWT + bcrypt utilities
│
├── run.py                           # Dev server entry point
├── requirements.txt                 # Python dependencies
├── .env                             # Environment variables
└── mp4totext.db                     # SQLite database
```

## 🔑 Critical Rules - ALWAYS Follow

1. **Directory Context**: ALWAYS run commands from `mp4totext-backend/` directory
   - Running from parent causes `ModuleNotFoundError: No module named 'app'`

2. **Bcrypt Version Lock**: Use `bcrypt==4.0.1` ONLY
   - Versions 4.3.0+ have breaking API changes in password hashing

3. **Credit Deduction Order**: Deduct credits AFTER operations succeed, NEVER before
   - Prevents credit loss on failed operations

4. **AssemblyAI Features Storage**: Store as nested dict, NEVER as boolean
   ```python
   # ✅ CORRECT
   features = {
       'speech_understanding': {
           'sentiment_analysis': True,
           'entity_detection': True
       }
   }
   
   # ❌ WRONG
   features = True
   ```

5. **Logging Convention**: Use emoji prefixes for clarity
   - 🚀 Starting operation
   - ✅ Success
   - ❌ Error
   - 💰 Credit transaction
   - 📊 Status update
   - ⚠️ Warning

6. **Windows Celery**: Use `--pool=solo` flag on Windows
   ```bash
   celery -A app.celery_app worker --loglevel=INFO --pool=solo
   ```

## 🛠️ Technology Stack

### Core Framework
- **FastAPI 0.104+** - Modern async web framework
- **SQLAlchemy 2.0** - ORM with async support
- **Pydantic 2.5** - Data validation
- **Uvicorn** - ASGI server

### Database & Storage
- **SQLite** - Local development database
- **Redis 5.0** - Cache + message broker
- **MinIO 7.2** - S3-compatible object storage

### Background Processing
- **Celery 5.5** - Distributed task queue
- **Flower 2.0** - Celery monitoring UI

### AI/ML Services
- **OpenAI Whisper** - Local transcription
- **Faster-Whisper** - Optimized Whisper (CTranslate2)
- **AssemblyAI 0.40+** - Cloud transcription with LLM Gateway
- **Google Gemini 2.5** - Text enhancement
- **Groq** - Ultra-fast LLM inference
- **Together AI** - Text cleaning, grammar fixes
- **OpenAI GPT-4** - Advanced text processing
- **Modal** - Serverless GPU (FLUX H100, SDXL)
- **Replicate** - Imagen-4 photorealistic images

### Audio/Video Processing
- **PyTorch 2.6** - Deep learning framework
- **librosa 0.11** - Audio analysis
- **FFmpeg** - Audio/video manipulation
- **pyannote.audio 3.1** - State-of-the-art speaker diarization

### Utilities
- **python-jose** - JWT tokens
- **passlib** - Password hashing
- **Tavily** - Web search integration

---

## Code Patterns - Follow These Exactly

### Pattern 1: API Endpoints

When creating API endpoints, use this structure:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.utils import get_current_active_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

class RequestSchema(BaseModel):
    field: str = Field(..., min_length=1, max_length=100)

@router.post("/action")
async def action_name(
    request: RequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # 1. Validate ownership
    resource = db.query(Model).filter_by(
        id=request.id, 
        user_id=current_user.id
    ).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Not found")
    
    # 2. Check credits BEFORE queueing
    required_credits = 5.0
    if current_user.credits < required_credits:
        raise HTTPException(
            status_code=402, 
            detail=f"Insufficient credits. Required: {required_credits}"
        )
    
    # 3. Queue Celery task (don't wait for result)
    from app.workers.transcription_worker import worker_function
    task = worker_function.apply_async(
        args=[resource.id, current_user.id],
        queue='default'
    )
    
    # 4. Return task_id immediately
    return {"task_id": task.id, "status": "queued"}
```

**Do:**
- ✅ Validate ownership first
- ✅ Check credits before queueing
- ✅ Return task_id, not result
- ✅ Use 402 for insufficient credits

**Don't:**
- ❌ Wait for Celery results in API endpoint
- ❌ Deduct credits in API endpoint
- ❌ Return 500 for business logic errors

---

### Pattern 2: Celery Tasks

When creating Celery tasks, use this structure:

```python
from app.celery_app import celery_app
from celery.utils.log import get_task_logger
from app.database import SessionLocal
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType

logger = get_task_logger(__name__)

@celery_app.task(
    bind=True,                    # Access self.retry()
    max_retries=2,                # Auto-retry 2 times
    default_retry_delay=60,       # Wait 60s between retries
    queue='default',              # Queue: default, high, low, critical
    time_limit=600,               # Hard timeout: 10 minutes
    soft_time_limit=540           # Soft timeout: 9 minutes
)
def task_name(self, resource_id: int, user_id: int):
    """Background task with automatic retry"""
    db = SessionLocal()
    logger.info(f"🚀 Task started: id={resource_id}")
    
    try:
        # 1. Fetch resource
        resource = db.query(Model).get(resource_id)
        if not resource:
            logger.error(f"❌ Resource {resource_id} not found")
            return {"error": "Not found"}
        
        # 2. Process (expensive operation)
        result = expensive_operation(resource)
        
        # 3. Update database
        resource.status = "completed"
        resource.result = result
        db.commit()
        
        # 4. Deduct credits AFTER success (CRITICAL)
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=user_id,
            amount=5.0,
            operation_type=OperationType.TRANSCRIPTION,
            description=f"Operation: {resource.name}",
            transcription_id=resource_id,
            metadata={"key": "value"}
        )
        
        # 5. Send WebSocket notification (optional, don't fail task)
        try:
            from app.websocket import manager
            import asyncio
            asyncio.run(manager.send_personal_message(
                message={"type": "job_complete", "id": resource_id},
                user_id=user_id
            ))
        except Exception as ws_error:
            logger.warning(f"⚠️ WebSocket failed: {ws_error}")
        
        logger.info(f"✅ Task completed: id={resource_id}")
        db.close()
        return {"success": True, "id": resource_id}
        
    except Exception as e:
        logger.error(f"❌ Task failed: {e}", exc_info=True)
        db.rollback()
        db.close()
        raise self.retry(exc=e)  # Automatic retry
```

**Do:**
- ✅ Use `bind=True` for retry access
- ✅ Set timeouts (soft + hard)
- ✅ Deduct credits AFTER success
- ✅ Always close database session
- ✅ Use emoji log prefixes
- ✅ Catch exceptions and retry

**Don't:**
- ❌ Deduct credits before operation
- ❌ Forget to close db session
- ❌ Fail task if WebSocket fails

---

### Pattern 3: Credit Management

When deducting credits, follow this exact sequence:

```python
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType

credit_service = get_credit_service(db)

# Step 1: Check credits BEFORE operation
required_credits = 10.5
if current_user.credits < required_credits:
    raise HTTPException(
        status_code=402,
        detail=f"Insufficient credits. Required: {required_credits}, Available: {current_user.credits}"
    )

# Step 2: Perform expensive operation
result = expensive_operation()

# Step 3: Deduct ONLY after success
credit_service.deduct_credits(
    user_id=current_user.id,
    amount=required_credits,
    operation_type=OperationType.TRANSCRIPTION,
    description=f"Transcription: {filename}",
    transcription_id=transcription.id,
    metadata={"duration": duration_minutes, "features": features}
)
```

**Credit Calculation for Transcription:**
```python
def calculate_credits(duration_minutes: float, language: str, features: dict) -> float:
    """
    Base: 1 cr/min (all languages)
    
    Speech Understanding (English only, 0.3 cr/min each):
    - sentiment_analysis
    - auto_chapters  
    - auto_highlights
    
    Entity Detection (ALL languages): 0.3 cr/min
    LLM Gateway (fixed): 3 cr
    """
    total = duration_minutes  # Base: 1 cr/min
    
    # Speech Understanding features
    if features.get('speech_understanding'):
        su = features['speech_understanding']
        
        # English-only features
        if language.startswith('en'):
            if su.get('sentiment_analysis'): total += duration_minutes * 0.3
            if su.get('auto_chapters'): total += duration_minutes * 0.3
            if su.get('auto_highlights'): total += duration_minutes * 0.3
        
        # All languages
        if su.get('entity_detection'): total += duration_minutes * 0.3
    
    # LLM Gateway (fixed cost)
    if features.get('llm_gateway', {}).get('enabled'):
        total += 3.0
    
    return round(total, 2)
```

**Do:**
- ✅ Check credits before operation
- ✅ Deduct after success
- ✅ Store metadata as JSON dict
- ✅ Use negative amounts for deductions
- ✅ Calculate language-specific pricing

**Don't:**
- ❌ Deduct before operation completes
- ❌ Forget metadata dict
- ❌ Charge English prices for non-English

---

### Pattern 4: AssemblyAI Features Storage

When storing AssemblyAI features, MUST use dictionary format:

```python
# ✅ CORRECT - Store as nested dictionary
assemblyai_features = {
    'speech_understanding': {
        'sentiment_analysis': True,   # English only (0.3 cr/min)
        'auto_chapters': True,         # English only (0.3 cr/min)
        'entity_detection': True,      # ALL languages (0.3 cr/min)
        'auto_highlights': True,       # English only (0.3 cr/min)
        'speaker_labels': True         # Free
    },
    'llm_gateway': {
        'enabled': True,               # Fixed 3 cr
        'generate_summary': True
    }
}

# Store in database (JSON column)
transcription.assemblyai_features_enabled = assemblyai_features
```

```python
# ❌ WRONG - Don't store as boolean
transcription.assemblyai_features_enabled = True  # NEVER DO THIS
```

**Language-aware feature enablement:**
```python
def get_enabled_features(language: str) -> dict:
    """Enable features based on language"""
    if language.startswith('en'):
        # English: all 4 features available
        return {
            'sentiment_analysis': True,
            'auto_chapters': True,
            'entity_detection': True,
            'auto_highlights': True
        }
    else:
        # Non-English: only entity detection
        return {'entity_detection': True}
```

**Do:**
- ✅ Store as nested dictionary
- ✅ Check language before enabling features
- ✅ Entity detection works for all languages
- ✅ LLM Gateway is language-agnostic

**Don't:**
- ❌ Store as boolean
- ❌ Enable English-only features for other languages
- ❌ Forget to calculate feature costs

---

### Pattern 5: File Upload Flow

When handling file uploads, follow this exact flow:

```python
import os
import uuid
from fastapi import UploadFile
from app.services.storage import get_storage_service

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload flow: Temp → MinIO → Database → Queue
    """
    # 1. Save to temporary directory
    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = f"/tmp/{temp_filename}"
    
    try:
        # Write uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. Upload to MinIO (S3-compatible storage)
        storage = get_storage_service()
        file_url = storage.upload_file(temp_path, temp_filename)
        
        # 3. Save URL to database
        transcription = Transcription(
            user_id=current_user.id,
            filename=file.filename,
            file_url=file_url,
            status="pending"
        )
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        # 4. Queue background task
        from app.workers.transcription_worker import process_transcription
        task = process_transcription.apply_async(
            args=[transcription.id, current_user.id],
            queue='default'
        )
        
        # 5. Clean up temp file
        os.remove(temp_path)
        
        return {
            "id": transcription.id,
            "task_id": task.id,
            "status": "queued"
        }
    
    except Exception as e:
        # Cleanup on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
```

**Do:**
- ✅ Use temp → MinIO → DB flow
- ✅ UUID in filename for uniqueness
- ✅ Clean temp file after upload
- ✅ Clean temp file on error
- ✅ Return task_id, not result

**Don't:**
- ❌ Store files directly in database
- ❌ Forget to clean temp files
- ❌ Wait for processing to complete

---

### Pattern 6: Authentication & Password Hashing

When handling passwords (bcrypt 72-byte limit workaround):

```python
from passlib.context import CryptContext

# MUST use bcrypt==4.0.1 (NOT 4.3.0+)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password with bcrypt (72-byte limit)"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password (same 72-byte truncation)"""
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.verify(plain_password, hashed_password)
```

**JWT Token Creation:**
```python
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(user_id: int, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

**Do:**
- ✅ Truncate at 72 bytes (not characters)
- ✅ Use bcrypt==4.0.1 exactly
- ✅ Truncate in both hash and verify
- ✅ Use 'ignore' for decode errors

**Don't:**
- ❌ Use bcrypt 4.3.0+ (API changed)
- ❌ Truncate at character level
- ❌ Forget to truncate in verify

---

### Pattern 7: WebSocket Real-time Updates

When sending WebSocket messages from Celery tasks:

```python
from app.websocket import manager
import asyncio

# Inside Celery task:
try:
    asyncio.run(manager.send_personal_message(
        message={
            "type": "job_complete",
            "transcription_id": transcription_id,
            "result": result_data
        },
        user_id=user_id
    ))
except Exception as ws_error:
    # Don't fail task if WebSocket fails
    logger.warning(f"⚠️ WebSocket notification failed: {ws_error}")
```

**Message Types:**
```python
# Upload progress
{"type": "upload_progress", "progress": 75.5, "transcription_id": 123}

# Job complete
{"type": "job_complete", "transcription_id": 123, "status": "completed"}

# Error
{"type": "error", "transcription_id": 123, "message": "Processing failed"}

# Credit update
{"type": "credit_update", "new_balance": 50.0}
```

**Do:**
- ✅ Use asyncio.run in Celery tasks
- ✅ Catch WebSocket exceptions
- ✅ Don't fail task if WebSocket fails
- ✅ Send meaningful message types

**Don't:**
- ❌ Block on WebSocket sends
- ❌ Fail task if WebSocket unavailable

---

## Quick Fixes for Common Issues

### Fix 1: Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'app'
# Solution: MUST be in backend directory
cd mp4totext-backend
python run.py
```

### Fix 2: Bcrypt Version Errors
```bash
# Error: ValueError: Invalid salt
# Solution: Use exact version
pip install bcrypt==4.0.1 --force-reinstall
```

### Fix 3: Celery Worker on Windows
```bash
# Error: NotImplementedError: pool implementation not available
# Solution: Use solo pool
python -m celery -A app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

### Fix 4: AssemblyAI Features Not Saving
```python
# ❌ WRONG
transcription.assemblyai_features_enabled = True

# ✅ CORRECT
transcription.assemblyai_features_enabled = {
    'speech_understanding': {'entity_detection': True}
}
```

### Fix 5: Credits Lost on Failed Operations
```python
# ❌ WRONG - Credits deducted even if fails
credit_service.deduct_credits(...)
result = expensive_operation()

# ✅ CORRECT - Deduct only after success
result = expensive_operation()
credit_service.deduct_credits(...)
```

---

## 🚀 Start Commands

### Windows (PowerShell)
```powershell
# Terminal 1: FastAPI Server
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\.venv\Scripts\Activate.ps1
python run.py  # Runs on http://localhost:8002

# Terminal 2: Celery Worker (REQUIRED)
cd C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend
.\.venv\Scripts\Activate.ps1
python -m celery -A app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1

# Terminal 3: Redis (Docker - REQUIRED)
docker run -d --name redis-mp4totext -p 6379:6379 redis:7-alpine redis-server --requirepass dev_redis_123

# Terminal 4: MinIO (Docker - REQUIRED)
docker run -d --name minio-mp4totext -p 9000:9000 -p 9001:9001 -e "MINIO_ROOT_USER=minioadmin" -e "MINIO_ROOT_PASSWORD=minioadmin" minio/minio server /data --console-address ":9001"
```

### Linux/Mac (Bash)
```bash
# Terminal 1: FastAPI Server
cd mp4totext-backend
source venv/bin/activate
python run.py

# Terminal 2: Celery Worker
cd mp4totext-backend
source venv/bin/activate
celery -A app.celery_app worker --loglevel=INFO

# Terminal 3: Redis Docker
docker run -d --name redis-mp4totext -p 6379:6379 redis:7-alpine redis-server --requirepass dev_redis_123

# Terminal 4: MinIO Docker
docker run -d --name minio-mp4totext -p 9000:9000 -p 9001:9001 -e "MINIO_ROOT_USER=minioadmin" -e "MINIO_ROOT_PASSWORD=minioadmin" minio/minio server /data --console-address ":9001"
```

---

## 📍 Key File Locations

### Core Application
- **Entry Point**: `run.py` - Uvicorn server (port 8002)
- **FastAPI App**: `app/main.py` - CORS, middleware, exception handlers
- **Settings**: `app/settings.py` - Environment configuration
- **Database**: `app/database.py` - SQLAlchemy setup

### API Layer
- **Auth**: `app/api/auth.py` - JWT authentication, login, register
- **Transcription**: `app/api/transcription.py` - Upload, transcribe, status (1726 lines)
- **Credits**: `app/api/credits.py` - Balance, history, pricing (580 lines)
- **Images**: `app/api/images.py` - AI image generation (404 lines)
- **Videos**: `app/api/videos.py` - AI video generation (256 lines)
- **Admin**: `app/api/admin.py` - Admin endpoints

### Background Processing
- **Celery App**: `app/celery_app.py` - Celery instance
- **Celery Config**: `app/celery_config.py` - Task configuration
- **Main Worker**: `app/workers/transcription_worker.py` - 3 main tasks (1935 lines)

### Business Logic
- **Credit Service**: `app/services/credit_service.py` - Credit management (423 lines)
- **Audio Processor**: `app/services/audio_processor.py` - Audio file processing
- **Storage**: `app/services/storage.py` - MinIO file storage
- **Language Detector**: `app/services/language_detector.py` - Auto language detection

### AI Services
- **Whisper**: `app/services/whisper_service.py` - OpenAI Whisper local
- **Faster Whisper**: `app/services/faster_whisper_service.py` - CTranslate2 optimized
- **AssemblyAI**: `app/services/assemblyai_service.py` - Cloud transcription
- **Gemini**: `app/services/gemini_service.py` - Google Gemini AI
- **Groq**: `app/services/groq_service.py` - Ultra-fast LLM
- **Together AI**: `app/services/together_service.py` - Text cleaning
- **OpenAI Cleaner**: `app/services/openai_cleaner_service.py` - GPT-4 cleaning

### Image/Video Generation
- **Image Generator**: `app/services/image_generator.py` - Image generation manager
- **Modal FLUX**: `app/services/modal_flux_service.py` - H100 FLUX model
- **Modal SD**: `app/services/modal_sd_service.py` - SDXL model
- **Replicate Imagen**: `app/services/replicate_imagen_service.py` - Imagen-4
- **Video Generator**: `app/services/video_generator.py` - Video pipeline
- **Video Assembly**: `app/services/video_assembly.py` - FFmpeg assembly

### Data Models
- **User**: `app/models/user.py` - User + credits
- **Transcription**: `app/models/transcription.py` - Main transcription model (171 lines)
- **Credit Transaction**: `app/models/credit_transaction.py` - Transaction log
- **Credit Pricing**: `app/models/credit_pricing.py` - Dynamic pricing
- **AI Model Pricing**: `app/models/ai_model_pricing.py` - AI cost multipliers
- **Generated Image**: `app/models/generated_image.py` - Image records
- **Generated Video**: `app/models/generated_video.py` - Video records

### Authentication & Utils
- **Auth Utils**: `app/auth/utils.py` - JWT + bcrypt utilities
- **WebSocket**: `app/websocket.py` - Real-time connection manager

---

## 🗄️ Database Management

### Check Database State
```powershell
# View database schema
python -c "from app.database import engine; print(engine.table_names())"

# Check user credits
python -c "from app.database import SessionLocal; from app.models.user import User; db = SessionLocal(); user = db.query(User).first(); print(f'User: {user.username}, Credits: {user.credits}')"
```

### Run Migrations
```powershell
# Add new feature migrations
python add_credits_system.py
python add_ai_model_pricing.py
python add_assemblyai_features.py
python add_video_generation.py
python add_generated_images.py
```

### Database Inspection
```powershell
# SQLite CLI
sqlite3 mp4totext.db

# View tables
.tables

# View schema
.schema transcriptions

# Query data
SELECT id, filename, status FROM transcriptions LIMIT 10;
```

---

## 🔧 Development Workflow

### 1. Setup New Environment
```powershell
# Clone repository
git clone <repo-url>
cd mp4totext-backend

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Initialize database
python add_credits_system.py
```

### 2. Daily Development
```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Start Redis + MinIO (once)
docker start redis-mp4totext minio-mp4totext

# Start FastAPI (Terminal 1)
python run.py

# Start Celery (Terminal 2)
python -m celery -A app.celery_app worker --loglevel=INFO --pool=solo
```

### 3. Testing
```powershell
# Test API endpoint
curl http://localhost:8002/health

# Test with httpie
http http://localhost:8002/api/v1/status

# View API docs
start http://localhost:8002/docs
```

---

## 📊 Monitoring & Debugging

### Check System Status
```powershell
# API health check
curl http://localhost:8002/health

# Detailed status (includes Celery, DB, Redis)
curl http://localhost:8002/api/v1/status

# View Celery tasks
celery -A app.celery_app inspect active
```

### Celery Monitoring
```powershell
# Start Flower (Celery monitoring UI)
celery -A app.celery_app flower --port=5555

# Access at: http://localhost:5555
```

### Logs
```powershell
# FastAPI logs (run.py shows in console)
# Celery logs (worker shows in console)

# Increase log verbosity
python run.py --log-level=debug
celery -A app.celery_app worker --loglevel=DEBUG
```

---

## 🌐 Environment Variables

Key `.env` settings:

```env
# Application
APP_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///C:/Users/hasan/OneDrive/Desktop/mp4totext/mp4totext-backend/mp4totext.db

# Redis
REDIS_PASSWORD=dev_redis_123
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://:dev_redis_123@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:dev_redis_123@localhost:6379/2

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=mp4totext
MINIO_SECURE=False

# AI Services
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AI...
GROQ_API_KEY=gsk_...
TOGETHER_API_KEY=...
ASSEMBLYAI_API_KEY=...
MODAL_TOKEN_ID=...
MODAL_TOKEN_SECRET=...
REPLICATE_API_TOKEN=r8_...
TAVILY_API_KEY=tvly-...

# JWT
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600
```
