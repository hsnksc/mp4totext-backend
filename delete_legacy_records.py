"""Delete transcription #213 and find all legacy records"""
from app.database import get_db
from app.models.transcription import Transcription
import json

def delete_and_check():
    db = next(get_db())
    
    # First, check if #213 exists
    print("🔍 Checking ID #213...")
    t = db.query(Transcription).filter(Transcription.id == 213).first()
    
    if t:
        print(f"✅ Found: {t.filename}")
        print(f"Speakers: {t.speakers}")
        print("\n🗑️ Deleting...")
        
        try:
            db.delete(t)
            db.commit()
            print("✅ Successfully deleted and committed")
            
            # Verify deletion
            check = db.query(Transcription).filter(Transcription.id == 213).first()
            if check is None:
                print("✅ Verified: Record #213 is gone")
            else:
                print("❌ ERROR: Record still exists after deletion!")
                
        except Exception as e:
            print(f"❌ Delete failed: {e}")
            db.rollback()
    else:
        print("❌ Record #213 not found")
    
    # Now find all legacy records
    print("\n\n🔍 Searching for all legacy format records...")
    all_transcriptions = db.query(Transcription).filter(
        Transcription.speakers.isnot(None)
    ).all()
    
    legacy_records = []
    for record in all_transcriptions:
        if isinstance(record.speakers, list) and len(record.speakers) > 0:
            first_speaker = record.speakers[0]
            if isinstance(first_speaker, str):
                legacy_records.append({
                    'id': record.id,
                    'filename': record.filename,
                    'speakers': record.speakers,
                    'status': record.status.value
                })
    
    if legacy_records:
        print(f"\n⚠️ Found {len(legacy_records)} legacy format records:")
        for rec in legacy_records:
            print(f"\n  ID: {rec['id']}")
            print(f"  File: {rec['filename']}")
            print(f"  Status: {rec['status']}")
            print(f"  Speakers: {rec['speakers']}")
    else:
        print("\n✅ No legacy format records found")
    
    db.close()
    return legacy_records

if __name__ == "__main__":
    legacy = delete_and_check()
    
    if legacy:
        print("\n\n💡 To delete all legacy records, run:")
        ids = [str(rec['id']) for rec in legacy]
        print(f"   IDs to delete: {', '.join(ids)}")
