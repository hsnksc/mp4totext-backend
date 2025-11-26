"""Check transcription 232 data"""
from app.database import SessionLocal
from app.models import Transcription
import json

db = SessionLocal()

try:
    t = db.query(Transcription).filter(Transcription.id == 232).first()
    
    if not t:
        print("❌ Transcription 232 NOT FOUND in database")
        exit(1)
    
    print("=" * 60)
    print(f"📊 TRANSCRIPTION #{t.id}")
    print("=" * 60)
    print(f"Status: {t.status}")
    print(f"Text: {len(t.text) if t.text else 0} chars")
    print(f"Duration: {t.duration}s")
    print()
    
    print("🎤 SPEECH UNDERSTANDING:")
    
    def parse_json(field):
        if not field:
            return None
        if isinstance(field, str):
            try:
                return json.loads(field)
            except:
                return None
        return field
    
    chapters = parse_json(t.auto_chapters)
    entities = parse_json(t.entities)
    highlights = parse_json(t.highlights)
    sentiment = parse_json(t.sentiment_analysis)
    
    print(f"  Chapters: {len(chapters) if chapters else 0}")
    if chapters and len(chapters) > 0:
        print(f"    Example: {chapters[0].get('headline', 'N/A')[:50]}")
    
    print(f"  Entities: {len(entities) if entities else 0}")
    if entities and len(entities) > 0:
        print(f"    Example: {entities[0].get('text', 'N/A')}")
    
    print(f"  Highlights: {len(highlights) if highlights else 0}")
    if highlights and len(highlights) > 0:
        print(f"    Example: {highlights[0].get('text', 'N/A')[:50]}")
    
    print(f"  Sentiment: {len(sentiment) if sentiment else 0}")
    print()
    
    print("🧠 LEMUR:")
    print(f"  Summary: {len(t.lemur_summary) if t.lemur_summary else 0} chars")
    if t.lemur_summary:
        print(f"    Preview: {t.lemur_summary[:100]}...")
    
    action_items = parse_json(t.lemur_action_items)
    qa_results = parse_json(t.lemur_questions_answers)
    
    print(f"  Action Items: {len(action_items) if action_items else 0}")
    print(f"  Q&A: {len(qa_results) if qa_results else 0}")
    print()
    
    print("=" * 60)
    print("✅ DATA CHECK COMPLETE")
    print("=" * 60)
    
    # Check if data exists but frontend not showing
    has_data = (chapters and len(chapters) > 0) or (entities and len(entities) > 0)
    if has_data:
        print("✅ Data exists in database")
        print("⚠️ If frontend shows nothing, check:")
        print("   1. API endpoint /api/v1/transcriptions/232")
        print("   2. Browser console for errors")
        print("   3. Web frontend parseField() function")
    else:
        print("⚠️ No Speech Understanding data in database")
        print("   Processing may have failed")
    
finally:
    db.close()
