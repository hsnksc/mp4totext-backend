from app.database import SessionLocal
from app.models.transcription import Transcription
import json

db = SessionLocal()
t = db.query(Transcription).order_by(Transcription.id.desc()).first()

print(f"ID: {t.id}")
print(f"Provider: {t.transcription_provider}")
print(f"Status: {t.status}")

if t.assemblyai_features_enabled:
    print(f"Features: {json.dumps(t.assemblyai_features_enabled, indent=2)}")
else:
    print("Features: NULL/EMPTY")

print(f"\nSentiment Analysis: {'YES' if t.sentiment_analysis else 'NO'}")
print(f"Entities: {'YES' if t.entities else 'NO'}")
print(f"Highlights: {'YES' if t.highlights else 'NO'}")
print(f"LeMUR Summary: {'YES' if t.lemur_summary else 'NO'}")

db.close()
