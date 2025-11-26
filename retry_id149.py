"""
Retry failed/stuck transcription
"""
from app.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus
from app.workers.transcription_worker import process_transcription_task

db = SessionLocal()

try:
    # Get transcription ID 149
    t = db.query(Transcription).filter(Transcription.id == 149).first()
    
    if not t:
        print("❌ Transcription #149 not found")
        exit(1)
    
    print(f"\n📄 Transcription #{t.id} - {t.filename}")
    print(f"Current Status: {t.status.value}")
    print(f"Text: {len(t.text or '')} chars")
    print(f"Enhanced: {len(t.enhanced_text or '')} chars")
    
    # Reset to pending
    print(f"\n🔄 Resetting to PENDING status...")
    t.status = TranscriptionStatus.PENDING
    t.error_message = None
    db.commit()
    
    print(f"✅ Status reset complete")
    print(f"\n🚀 Triggering Celery task...")
    
    # Trigger task
    task = process_transcription_task.apply_async(
        args=[t.id],
        queue='high',
        priority=10
    )
    
    print(f"✅ Task queued: {task.id}")
    print(f"   Check status with: task.status")
    
finally:
    db.close()
