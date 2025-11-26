"""Check transcription #213 status"""
from app.database import get_db
from app.models.transcription import Transcription
import json

def check_transcription_213():
    db = next(get_db())
    t = db.query(Transcription).filter(Transcription.id == 213).first()
    
    if t:
        print(f"✅ Kayıt mevcut - ID: {t.id}")
        print(f"Status: {t.status}")
        print(f"Filename: {t.filename}")
        print(f"Speakers tipi: {type(t.speakers)}")
        print(f"Speakers değeri: {t.speakers}")
        print(f"Segments tipi: {type(t.segments)}")
        
        if t.speakers:
            if isinstance(t.speakers, list):
                print(f"\n📊 Speakers listesi uzunluğu: {len(t.speakers)}")
                if len(t.speakers) > 0:
                    first_speaker = t.speakers[0]
                    print(f"İlk speaker tipi: {type(first_speaker)}")
                    print(f"İlk speaker değeri: {first_speaker}")
                    
                    if isinstance(first_speaker, str):
                        print("\n⚠️ LEGACY FORMAT DETECTED: String array")
                        print("Beklenen format: [{'speaker': 'A', 'start': 0.0, 'end': 10.0, ...}]")
                        print(f"Mevcut format: {t.speakers[:3]}")
                    else:
                        print("\n✅ CORRECT FORMAT: Dictionary array")
    else:
        print("❌ Kayıt bulunamadı (silme başarılı)")
        
    db.close()

if __name__ == "__main__":
    check_transcription_213()
