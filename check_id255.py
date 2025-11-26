"""Check ID 255 sentiment_analysis status"""
from app.database import get_db
from app.models.transcription import Transcription
import json

db = next(get_db())
t = db.query(Transcription).filter(Transcription.id == 255).first()

if not t:
    print("❌ ID 255 not found")
else:
    print(f"\n{'='*60}")
    print(f"ID 255 - Sentiment Analysis Check")
    print(f"{'='*60}")
    print(f"Status: {t.status}")
    print(f"Speech Understanding Enabled: {t.assemblyai_features_enabled}")
    print(f"\nsentiment_analysis: {t.sentiment_analysis}")
    
    if t.sentiment_analysis:
        print(f"✅ Sentiment data found: {len(t.sentiment_analysis)} items")
        if len(t.sentiment_analysis) > 0:
            print(f"\nFirst item:")
            print(json.dumps(t.sentiment_analysis[0], indent=2))
    else:
        print("❌ No sentiment data found")
    
    print(f"\nOther features:")
    print(f"  auto_chapters: {len(t.auto_chapters) if t.auto_chapters else 0} items")
    print(f"  entities: {len(t.entities) if t.entities else 0} items")
    print(f"  highlights: {len(t.highlights) if t.highlights else 0} items")
    print(f"{'='*60}\n")
