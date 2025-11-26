"""Check failed transcriptions with missing files"""
import sys
from pathlib import Path
from app.database import get_db
from app.models.transcription import Transcription, TranscriptionStatus

def main():
    db = next(get_db())
    
    # Get transcription 149 and 150
    for tid in [149, 150]:
        t = db.query(Transcription).filter(Transcription.id == tid).first()
        if t:
            print(f"\n{'='*60}")
            print(f"Transcription #{t.id}")
            print(f"{'='*60}")
            print(f"File ID: {t.file_id}")
            print(f"File Path: {t.file_path}")
            print(f"Original Name: {t.original_filename}")
            print(f"Status: {t.status}")
            print(f"User ID: {t.user_id}")
            print(f"Created: {t.created_at}")
            
            # Check if file exists
            if t.file_path:
                file_path = Path(t.file_path)
                print(f"\nFile exists: {file_path.exists()}")
                if file_path.exists():
                    print(f"File size: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Check uploads folder
            uploads_dir = Path("uploads")
            matching_files = list(uploads_dir.glob(f"{t.file_id}.*"))
            print(f"\nMatching files in uploads/: {len(matching_files)}")
            for f in matching_files:
                print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # List all files in uploads
    print(f"\n{'='*60}")
    print("All MP3 files in uploads/")
    print(f"{'='*60}")
    uploads_dir = Path("uploads")
    for f in sorted(uploads_dir.glob("*.mp3"), key=lambda x: x.stat().st_mtime, reverse=True):
        print(f"{f.name}: {f.stat().st_size / 1024 / 1024:.2f} MB - {f.stat().st_mtime}")

if __name__ == "__main__":
    main()
