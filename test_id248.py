from app.database import SessionLocal
from app.models.transcription import Transcription
import json

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 248).first()

print(f"ID: {t.id}")
print(f"Provider: {t.transcription_provider}")
print(f"Status: {t.status}")
print(f"\n=== AssemblyAI Features (at upload) ===")
if t.assemblyai_features_enabled:
    print(json.dumps(t.assemblyai_features_enabled, indent=2))
else:
    print("NULL or EMPTY")

print(f"\n=== Results ===")
print(f"Sentiment Analysis: {'YES' if t.sentiment_analysis else 'NO'}")
print(f"Entities: {'YES' if t.entities else 'NO'}")
print(f"Highlights: {'YES' if t.highlights else 'NO'}")
print(f"Topics: {'YES' if t.topics else 'NO'}")
print(f"Content Safety: {'YES' if t.content_safety else 'NO'}")
print(f"LeMUR Summary: {'YES' if t.lemur_summary else 'NO'}")

db.close()
