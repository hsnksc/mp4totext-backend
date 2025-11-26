# MP4toText Backend Instructions

You are working on **MP4toText Backend** - a FastAPI transcription service with Celery workers, WebSocket real-time updates, and multi-AI providers (AssemblyAI, Gemini, Modal FLUX).

## Critical Rules - Follow These Always

1. **ALWAYS run commands from `mp4totext-backend/` directory** - running from parent causes `ModuleNotFoundError`
2. **Use `bcrypt==4.0.1` ONLY** - versions 4.3.0+ break password hashing
3. **Deduct credits AFTER operations succeed** - never before (prevents credit loss on failures)
4. **Store AssemblyAI features as dict, never boolean** - `{'speech_understanding': {...}}` not `True`
5. **Use emoji prefixes in logs** - 🚀 (start), ✅ (success), ❌ (error), 💰 (credits)
6. **On Windows: use `--pool=solo`** for Celery workers

## Architecture

```
Client → FastAPI:8002 → Celery Workers
         ↓              ↓
    SQLite/MinIO    Redis (DB 1/2)
         ↓              ↓
    WebSocket ←────────┘
```

**Key Components:**
- `app/api/` - 6 FastAPI routers (auth, transcription, credits, images, videos, admin)
- `app/workers/` - Celery background tasks with retry logic
- `app/services/` - Business logic + AI integrations
- `app/models/` - SQLAlchemy ORM models

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

## Start Commands

```powershell
# PowerShell - Terminal 1: FastAPI
cd mp4totext-backend
.\venv\Scripts\Activate.ps1
python run.py  # Runs on port 8002

# PowerShell - Terminal 2: Celery Worker
cd mp4totext-backend
.\venv\Scripts\Activate.ps1
python -m celery -A app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

```bash
# Linux/Mac - Terminal 1: FastAPI
cd mp4totext-backend
source venv/bin/activate
python run.py

# Linux/Mac - Terminal 2: Celery Worker
cd mp4totext-backend
source venv/bin/activate
celery -A app.celery_app worker --loglevel=INFO
```

---

## Key File Locations

- **Entry Point**: `run.py` - Uvicorn server (port 8002)
- **FastAPI App**: `app/main.py` - CORS, middleware, exception handlers
- **Celery Config**: `app/celery_app.py` - Task autodiscovery
- **Workers**: `app/workers/transcription_worker.py` - 3 main tasks
- **Credit Service**: `app/services/credit_service.py` - Credit management
- **Auth Utils**: `app/auth/utils.py` - JWT + bcrypt
- **AssemblyAI**: `app/services/assemblyai/client.py` - API integration
- **WebSocket**: `app/websocket.py` - Connection manager

---

## Database Management

```bash
# Check database state
python check_db.py

# Run migration
python add_credits_system.py

# Inspect specific record
python check_id124.py
```
