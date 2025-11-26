"""Clean up failed transcriptions with missing files"""
from app.database import get_db
from app.models.transcription import Transcription, TranscriptionStatus

def main():
    db = next(get_db())
    
    # Get transcriptions 149 and 150
    failed_ids = [149, 150]
    
    for tid in failed_ids:
        t = db.query(Transcription).filter(Transcription.id == tid).first()
        if t:
            print(f"\nTranscription #{t.id}:")
            print(f"  Status: {t.status}")
            print(f"  File ID: {t.file_id}")
            print(f"  Original Name: {t.original_filename}")
            
            # Update status to FAILED with error message
            t.status = TranscriptionStatus.FAILED
            t.error_message = "File not found - deleted or missing from storage"
            
            # Clear file references
            t.file_id = None
            t.file_path = None
            
            db.commit()
            print(f"  ✅ Updated to FAILED status and cleared file references")
    
    print(f"\n✅ Cleanup complete!")
    
    # Show summary
    print(f"\nSummary:")
    print(f"  - Transcription #149: Status = FAILED, Files cleared")
    print(f"  - Transcription #150: Status = FAILED, Files cleared")
    print(f"  - These will no longer be retried by workers")

if __name__ == "__main__":
    main()
