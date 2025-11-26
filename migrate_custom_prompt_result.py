"""
Database migration: Add custom_prompt_result column

Run this script to add the new custom_prompt_result column to existing database.
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str = "mp4totext.db"):
    """Add custom_prompt_result column to transcriptions table"""
    
    print(f"🔄 Starting database migration...")
    print(f"📁 Database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'custom_prompt_result' in columns:
            print("✅ Column 'custom_prompt_result' already exists. No migration needed.")
            conn.close()
            return
        
        print("➕ Adding 'custom_prompt_result' column...")
        
        # Add new column
        cursor.execute("""
            ALTER TABLE transcriptions 
            ADD COLUMN custom_prompt_result TEXT
        """)
        
        conn.commit()
        
        # Verify
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'custom_prompt_result' in columns:
            print("✅ Migration successful!")
            print(f"📊 Total columns in transcriptions table: {len(columns)}")
        else:
            print("❌ Migration failed! Column not found after addition.")
            sys.exit(1)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Default database path
    db_path = "mp4totext.db"
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("Please run this script from mp4totext-backend directory.")
        sys.exit(1)
    
    migrate_database(db_path)
