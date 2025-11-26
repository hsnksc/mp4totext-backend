"""Delete all legacy format transcription records"""
from app.database import get_db
from app.models.transcription import Transcription
import sys

def delete_all_legacy_records():
    """Find and delete all transcription records with legacy speaker format"""
    db = next(get_db())
    
    # Legacy IDs found
    legacy_ids = [7, 8, 9, 16, 20, 21, 50, 51, 52]
    
    print(f"🗑️ Deleting {len(legacy_ids)} legacy format records...")
    print(f"IDs: {legacy_ids}\n")
    
    deleted_count = 0
    failed = []
    
    for record_id in legacy_ids:
        try:
            record = db.query(Transcription).filter(Transcription.id == record_id).first()
            if record:
                filename = record.filename
                db.delete(record)
                db.commit()
                deleted_count += 1
                print(f"✅ Deleted ID {record_id}: {filename[:60]}...")
            else:
                print(f"⚠️ ID {record_id}: Already deleted")
        except Exception as e:
            print(f"❌ Failed to delete ID {record_id}: {e}")
            failed.append(record_id)
            db.rollback()
    
    print(f"\n📊 Summary:")
    print(f"   Successfully deleted: {deleted_count}")
    if failed:
        print(f"   Failed: {len(failed)} - IDs: {failed}")
    else:
        print(f"   Failed: 0")
    
    # Verify all are gone
    print("\n🔍 Verifying deletion...")
    remaining = []
    for record_id in legacy_ids:
        check = db.query(Transcription).filter(Transcription.id == record_id).first()
        if check:
            remaining.append(record_id)
    
    if remaining:
        print(f"❌ ERROR: {len(remaining)} records still exist: {remaining}")
    else:
        print(f"✅ All legacy records successfully deleted!")
    
    # Check if any other legacy records exist
    print("\n🔍 Scanning for any remaining legacy records...")
    all_transcriptions = db.query(Transcription).filter(
        Transcription.speakers.isnot(None)
    ).all()
    
    other_legacy = []
    for record in all_transcriptions:
        if isinstance(record.speakers, list) and len(record.speakers) > 0:
            first_speaker = record.speakers[0]
            if isinstance(first_speaker, str):
                other_legacy.append(record.id)
    
    if other_legacy:
        print(f"⚠️ Found {len(other_legacy)} additional legacy records: {other_legacy}")
    else:
        print(f"✅ No other legacy records found")
    
    db.close()

if __name__ == "__main__":
    # Confirmation
    print("⚠️ WARNING: This will delete 9 transcription records with legacy speaker format")
    print("These records have string arrays instead of dictionary arrays in 'speakers' field")
    print("\nContinue? (yes/no): ", end="")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        confirm = "yes"
        print("yes (auto-confirmed)")
    else:
        confirm = input().strip().lower()
    
    if confirm == "yes":
        delete_all_legacy_records()
    else:
        print("❌ Operation cancelled")
