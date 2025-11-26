from app.database import SessionLocal
from app.models.transcription import Transcription
import json

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 254).first()

print("\n" + "="*80)
print(f"ID 254 - Sentiment Analysis Check")
print("="*80 + "\n")

print(f"sentiment_analysis: {'EXISTS ✅' if t.sentiment_analysis else 'NULL ❌'}")

if t.sentiment_analysis:
    print(f"Count: {len(t.sentiment_analysis)} sentiment results")
    print(f"\nFirst 3 items:")
    for i, item in enumerate(t.sentiment_analysis[:3], 1):
        print(f"\n{i}. {json.dumps(item, indent=2)}")
else:
    print("❌ No sentiment data found")
    print("\nOther features:")
    print(f"  auto_chapters: {len(t.auto_chapters) if t.auto_chapters else 0} items")
    print(f"  entities: {len(t.entities) if t.entities else 0} items")
    print(f"  highlights: {len(t.highlights) if t.highlights else 0} items")

db.close()
