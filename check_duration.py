"""Check transcription duration issue"""
from app.database import SessionLocal
from app.models.transcription import Transcription
import json

db = SessionLocal()

# Get last transcription
t = db.query(Transcription).get(131)

print(f"\n📊 Transkripsiyon #131:")
print(f"Dosya: {t.filename}")
print(f"Duration (DB): {t.duration}")
print(f"Status: {t.status}")

# Check segments
if t.segments:
    segments = t.segments if isinstance(t.segments, list) else json.loads(t.segments)
    print(f"\n📝 Segments:")
    print(f"Toplam segment: {len(segments)}")
    
    if len(segments) > 0:
        first = segments[0]
        last = segments[-1]
        
        print(f"\nİlk segment:")
        print(f"  start: {first.get('start', 'N/A')}")
        print(f"  end: {first.get('end', 'N/A')}")
        print(f"  text: {first.get('text', 'N/A')[:50]}...")
        
        print(f"\nSon segment:")
        print(f"  start: {last.get('start', 'N/A')}")
        print(f"  end: {last.get('end', 'N/A')}")
        print(f"  text: {last.get('text', 'N/A')[:50]}...")
        
        # Calculate actual duration
        actual_duration = last.get('end', 0)
        print(f"\n⏱️ Gerçek Süre (son segment end): {actual_duration} saniye = {actual_duration/60:.1f} dakika")
else:
    print("\n⚠️ Segments bulunamadı!")

db.close()
