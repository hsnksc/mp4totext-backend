from app.database import SessionLocal
from app.models import Transcription

db = SessionLocal()
transcriptions = db.query(Transcription).order_by(Transcription.id.desc()).limit(5).all()

print("\n📊 Son 5 Transkripsiyon:")
print("=" * 80)
for t in transcriptions:
    print(f"ID: {t.id:3d} | Status: {t.status:12s} | Progress: {t.progress:3d}% | File: {t.original_filename[:40] if t.original_filename else 'None'}")

db.close()
