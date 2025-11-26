from app.database import SessionLocal
from app.models.transcription import Transcription
import json

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 249).first()

print("=== ID 249 Analysis ===\n")
print("AssemblyAI Features (at upload):")
if t.assemblyai_features_enabled:
    print(json.dumps(t.assemblyai_features_enabled, indent=2))
else:
    print("NULL")

print("\n=== Results ===")
print(f"Sentiment Analysis: {'YES' if t.sentiment_analysis else 'NULL'}")
print(f"Entities: {len(t.entities) if t.entities else 'NULL'}")
print(f"Chapters: {len(t.auto_chapters) if t.auto_chapters else 'NULL'}")
print(f"Topics: {'YES' if t.topics else 'NULL'}")
print(f"Content Safety: {'YES' if t.content_safety else 'NULL'}")
print(f"Highlights: {len(t.highlights) if t.highlights else 'NULL'}")
print(f"LeMUR Summary: {'YES' if t.lemur_summary else 'NULL'}")

# Check what features were enabled in config
config = t.assemblyai_features_enabled
if config and 'speech_understanding' in config:
    su_config = config['speech_understanding']
    print("\n=== Speech Understanding Config ===")
    print(f"Sentiment: {su_config.get('sentiment_analysis', False)}")
    print(f"Chapters: {su_config.get('auto_chapters', False)}")
    print(f"Entities: {su_config.get('entity_detection', False)}")
    print(f"Topics: {su_config.get('iab_categories', False)}")
    print(f"Content Safety: {su_config.get('content_safety', False)}")
    print(f"Highlights: {su_config.get('auto_highlights', False)}")

db.close()
