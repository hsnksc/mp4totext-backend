"""
Database Migration Script - Add Gemini Mode and Lecture Notes Support
Adds: gemini_mode, custom_prompt, lecture_notes columns
"""

import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "mp4totext.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🚀 Starting migration...")
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(transcriptions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Existing columns: {len(existing_columns)}")
        
        # Add gemini_mode column
        if "gemini_mode" not in existing_columns:
            print("➕ Adding gemini_mode column...")
            cursor.execute("""
                ALTER TABLE transcriptions 
                ADD COLUMN gemini_mode VARCHAR(20) DEFAULT 'text'
            """)
            print("   ✅ gemini_mode added")
        else:
            print("   ⏭️  gemini_mode already exists")
        
        # Add custom_prompt column
        if "custom_prompt" not in existing_columns:
            print("➕ Adding custom_prompt column...")
            cursor.execute("""
                ALTER TABLE transcriptions 
                ADD COLUMN custom_prompt TEXT
            """)
            print("   ✅ custom_prompt added")
        else:
            print("   ⏭️  custom_prompt already exists")
        
        # Add lecture_notes column
        if "lecture_notes" not in existing_columns:
            print("➕ Adding lecture_notes column...")
            cursor.execute("""
                ALTER TABLE transcriptions 
                ADD COLUMN lecture_notes TEXT
            """)
            print("   ✅ lecture_notes added")
        else:
            print("   ⏭️  lecture_notes already exists")
        
        conn.commit()
        
        # Verify migration
        cursor.execute("PRAGMA table_info(transcriptions)")
        final_columns = [row[1] for row in cursor.fetchall()]
        print(f"\n✅ Migration completed!")
        print(f"📊 Total columns: {len(final_columns)}")
        print(f"🆕 New columns added: gemini_mode, custom_prompt, lecture_notes")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
