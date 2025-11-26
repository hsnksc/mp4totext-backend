"""List all transcription IDs to see what's available"""
from app.database import get_db
from app.models.transcription import Transcription

def list_all_transcriptions():
    db = next(get_db())
    
    all_records = db.query(Transcription).order_by(Transcription.id).all()
    
    print(f"\n📊 Total transcriptions: {len(all_records)}\n")
    
    for record in all_records:
        speaker_format = "UNKNOWN"
        if record.speakers:
            if isinstance(record.speakers, list) and len(record.speakers) > 0:
                if isinstance(record.speakers[0], str):
                    speaker_format = "❌ LEGACY (string[])"
                else:
                    speaker_format = "✅ CORRECT (dict[])"
            elif isinstance(record.speakers, list):
                speaker_format = "✅ EMPTY LIST"
        else:
            speaker_format = "✅ NULL"
        
        print(f"ID: {record.id:3d} | {record.status.value:10s} | {speaker_format:20s} | {record.filename[:50]}")
    
    db.close()

if __name__ == "__main__":
    list_all_transcriptions()
