# MP4toText - AI Coding Assistant Instructions

## Architecture Overview

**Multi-platform transcription service** with credit-based usage:
- **Backend**: FastAPI + Celery + SQLAlchemy + MinIO (video/audio transcription, AI image generation)
- **Web**: React/Next.js frontend
- **Mobile**: React Native app

**Key Backend Structure** (`mp4totext-backend/`):
- `app/api/` - FastAPI routers (images.py, transcriptions.py, auth.py)
- `app/models/` - SQLAlchemy models (User, Transcription, GeneratedImage, CreditTransaction)
- `app/services/` - Business logic (image_generator.py, storage.py, credit_service.py)
- `app/workers/` - Celery tasks for long-running operations (transcription_worker.py)

## Critical Backend Patterns

### 1. Always Use Celery for Long Operations
**ALL operations > 5 seconds MUST use Celery tasks** to prevent HTTP timeout.

```python
# ✅ CORRECT - See app/api/images.py lines 133-149
from app.workers.transcription_worker import generate_transcript_images

task = generate_transcript_images.delay(
    transcription_id=transcription_id,
    user_id=current_user.id,
    num_images=request.num_images
)
return {"status": "processing", "task_id": task.id}
```

**Why**: Image generation takes 10-60s, transcription takes 30s-5min. Synchronous code was removed (see lines 151-264 marked as "OLD CODE - REMOVED").

### 2. Credit System: Check → Process → Deduct (Never Deduct First)
**Critical order** to prevent charging users for failed operations:

```python
# 1. Check credits BEFORE operation (line 109-115)
if current_user.credits < required_credits:
    raise HTTPException(status_code=402, detail="Insufficient credits")

# 2. Process operation (Celery task or sync)
result = await process_operation()

# 3. Deduct credits AFTER success (lines 241-256)