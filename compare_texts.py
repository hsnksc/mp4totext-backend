"""
Compare raw vs cleaned text from transcription ID 80
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import get_settings
from app.models.transcription import Transcription

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()

# Get transcription 80
trans = db.query(Transcription).filter(Transcription.id == 80).first()

if trans:
    print("=" * 80)
    print("TRANSCRIPTION ID 80 - TEXT COMPARISON")
    print("=" * 80)
    
    print("\n📝 RAW TEXT (Whisper output):")
    print("-" * 80)
    raw_preview = trans.text[:500] if trans.text else "None"
    print(raw_preview)
    print(f"\n... (total: {len(trans.text) if trans.text else 0} chars)")
    
    print("\n✨ CLEANED TEXT (AI cleaned):")
    print("-" * 80)
    cleaned_preview = trans.cleaned_text[:500] if trans.cleaned_text else "None"
    print(cleaned_preview)
    print(f"\n... (total: {len(trans.cleaned_text) if trans.cleaned_text else 0} chars)")
    
    print("\n📊 STATISTICS:")
    print("-" * 80)
    if trans.text and trans.cleaned_text:
        diff = len(trans.text) - len(trans.cleaned_text)
        percentage = (diff / len(trans.text)) * 100
        print(f"Original length:  {len(trans.text)} chars")
        print(f"Cleaned length:   {len(trans.cleaned_text)} chars")
        print(f"Difference:       {diff} chars ({percentage:.1f}% reduction)")
        
        # Count filler words in raw text
        filler_words = ['işte', 'yani', 'şey', 'hani', 'falan', 'filan', 'ee', 'aa', 'öyle', 'böyle', 'gibi', 'mesela']
        raw_lower = trans.text.lower()
        filler_counts = {word: raw_lower.count(word) for word in filler_words}
        total_fillers = sum(filler_counts.values())
        
        print(f"\n🔍 Filler words in RAW text:")
        for word, count in filler_counts.items():
            if count > 0:
                print(f"  '{word}': {count} times")
        print(f"  TOTAL: {total_fillers} filler words")
        
        # Check if fillers still exist in cleaned text
        if trans.cleaned_text:
            cleaned_lower = trans.cleaned_text.lower()
            remaining_fillers = {word: cleaned_lower.count(word) for word in filler_words}
            total_remaining = sum(remaining_fillers.values())
            
            print(f"\n🧹 Filler words in CLEANED text:")
            for word, count in remaining_fillers.items():
                if count > 0:
                    print(f"  '{word}': {count} times (was {filler_counts[word]})")
            print(f"  TOTAL: {total_remaining} filler words (removed {total_fillers - total_remaining})")
    else:
        print("❌ Text or cleaned_text is missing")
    
else:
    print("❌ Transcription 80 not found")

db.close()
