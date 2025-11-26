# Database Migration: Speaker Diarization Fields

# Run this script to add speaker diarization columns to existing database
# python add_speaker_diarization.py

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from app.database import engine

def migrate():
    """Add speaker diarization columns to transcriptions table"""
    
    print("🔄 Adding speaker diarization columns...")
    
    with engine.connect() as conn:
        try:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM pragma_table_info('transcriptions') 
                WHERE name IN ('enable_diarization', 'min_speakers', 'max_speakers', 'speakers_json', 'transcript_with_speakers')
            """))
            
            existing_count = result.fetchone()[0]
            
            if existing_count == 5:
                print("✅ All speaker diarization columns already exist")
                return
            
            # Add columns if they don't exist
            columns_to_add = [
                ("enable_diarization", "BOOLEAN DEFAULT 0"),
                ("min_speakers", "INTEGER NULL"),
                ("max_speakers", "INTEGER NULL"),
                ("speakers_json", "TEXT NULL"),  # JSON stored as TEXT in SQLite
                ("transcript_with_speakers", "TEXT NULL"),
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    conn.execute(text(f"ALTER TABLE transcriptions ADD COLUMN {col_name} {col_type}"))
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower():
                        print(f"⚠️ Column {col_name} already exists, skipping")
                    else:
                        raise
            
            conn.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
