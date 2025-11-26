from app.database import SessionLocal
from app.models.transcription import Transcription

db = SessionLocal()

try:
    t = db.query(Transcription).filter(Transcription.id == 149).first()
    
    if t:
        print(f"\n{'='*80}")
        print(f"📄 Transcription #{t.id} - {t.filename}")
        print(f"{'='*80}")
        print(f"Status: {t.status.value}")
        print(f"Created: {t.created_at}")
        print(f"Updated: {t.updated_at}")
        print(f"Duration: {t.duration_seconds}s")
        print(f"\n📝 Text Lengths:")
        print(f"   Original: {len(t.original_text or '')} chars")
        print(f"   Enhanced: {len(t.enhanced_text or '')} chars")
        print(f"\n🎯 AI Config:")
        print(f"   Provider: {t.ai_provider}")
        print(f"   Model: {t.ai_model}")
        print(f"   Gemini Status: {t.gemini_enhancement_status}")
        print(f"   Web Search: {t.enable_web_search}")
        print(f"\n⚠️ Errors:")
        print(f"   Error: {t.error_message or 'None'}")
        print(f"{'='*80}\n")
    else:
        print("❌ Transcription not found")
        
finally:
    db.close()
