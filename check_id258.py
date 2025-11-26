"""Check ID 258 sentiment_analysis data"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from sqlalchemy import text

def check_id258():
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT 
                    id,
                    duration,
                    assemblyai_features_enabled,
                    sentiment_analysis IS NOT NULL as has_sentiment,
                    CASE 
                        WHEN sentiment_analysis IS NOT NULL 
                        THEN json_array_length(sentiment_analysis)
                        ELSE 0 
                    END as sentiment_count,
                    auto_chapters IS NOT NULL as has_chapters,
                    entities IS NOT NULL as has_entities,
                    highlights IS NOT NULL as has_highlights
                FROM transcriptions 
                WHERE id = 258
            """)
        ).fetchone()
        
        if result:
            print(f"\n{'='*60}")
            print(f"📊 TRANSCRIPTION ID: {result.id}")
            print(f"{'='*60}")
            print(f"⏱️  Duration: {result.duration}s")
            print(f"🎯 AssemblyAI Features: {result.assemblyai_features_enabled}")
            print(f"\n📈 SPEECH UNDERSTANDING RESULTS:")
            print(f"   Sentiment Analysis: {'✅' if result.has_sentiment else '❌'} ({result.sentiment_count} items)")
            print(f"   Chapters: {'✅' if result.has_chapters else '❌'}")
            print(f"   Entities: {'✅' if result.has_entities else '❌'}")
            print(f"   Highlights: {'✅' if result.has_highlights else '❌'}")
            
            # Get first 3 sentiment items
            if result.has_sentiment:
                sentiment_data = db.execute(
                    text("SELECT sentiment_analysis FROM transcriptions WHERE id = 258")
                ).fetchone()
                
                sentiments = json.loads(sentiment_data[0])[:3]
                print(f"\n📝 First 3 Sentiment Items:")
                for i, sent in enumerate(sentiments, 1):
                    print(f"   {i}. {sent['sentiment']} (conf: {sent['confidence']:.2f})")
                    print(f"      Text: {sent['text'][:60]}...")
            
            print(f"{'='*60}\n")
        else:
            print("❌ ID 258 not found")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_id258()
