"""
Check transcription #120 details
"""
from app.database import SessionLocal
from app.models.transcription import Transcription

def check_transcription():
    db = SessionLocal()
    try:
        trans = db.query(Transcription).filter_by(id=120).first()
        if not trans:
            print("❌ Transcription #120 not found")
            return
        
        print("📄 Transcription #120 Details")
        print("=" * 80)
        print(f"Filename: {trans.filename}")
        print(f"Status: {trans.status}")
        print(f"Duration: {trans.duration}s")
        print(f"Progress: {trans.progress}%")
        print(f"\n🤖 AI Configuration:")
        print(f"   Gemini Mode: {trans.gemini_mode}")
        print(f"   AI Provider: {trans.ai_provider}")
        print(f"   AI Model: {trans.ai_model}")
        print(f"   Web Search: {trans.enable_web_search}")
        
        print(f"\n📊 Text Lengths:")
        print(f"   Original: {len(trans.text) if trans.text else 0} chars")
        print(f"   Enhanced: {len(trans.enhanced_text) if trans.enhanced_text else 0} chars")
        print(f"   Summary: {len(trans.summary) if trans.summary else 0} chars")
        
        print(f"\n💰 Credits:")
        print(f"   Cost: {trans.credit_cost} credits")
        
        # Check if enhanced text is same as original
        if trans.text and trans.enhanced_text:
            if trans.text.strip() == trans.enhanced_text.strip():
                print(f"\n⚠️  WARNING: Enhanced text is IDENTICAL to original text!")
                print(f"   This means AI enhancement did NOT work!")
            else:
                print(f"\n✅ Enhanced text is different from original (AI worked)")
                # Show first difference
                for i, (c1, c2) in enumerate(zip(trans.text[:200], trans.enhanced_text[:200])):
                    if c1 != c2:
                        print(f"   First difference at char {i}: '{c1}' vs '{c2}'")
                        break
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_transcription()
