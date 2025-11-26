from app.database import SessionLocal
from app.models import Transcription
import json

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 211).first()

if t:
    print(f"\n📊 Transkripsiyon #211 Detayı:")
    print("=" * 80)
    print(f"Status: {t.status}")
    print(f"Progress: {t.progress}%")
    print(f"File: {t.original_filename}")
    print(f"Error: {t.error_message[:200] if t.error_message else 'None'}")
    print(f"Started: {t.started_at}")
    print(f"Completed: {t.completed_at}")
    print(f"User ID: {t.user_id}")
    print(f"Transcript Length: {len(t.transcript) if t.transcript else 0} chars")
else:
    print("Transkripsiyon bulunamadı")

db.close()
