"""
Add translated_text column to transcriptions table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_translated_text_column():
    """Add translated_text column to existing transcriptions table"""
    try:
        conn = sqlite3.connect('mp4totext.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'translated_text' in columns:
            logger.info("✅ translated_text column already exists")
            conn.close()
            return
        
        # Add column
        logger.info("📝 Adding translated_text column to transcriptions table...")
        cursor.execute("""
            ALTER TABLE transcriptions 
            ADD COLUMN translated_text TEXT
        """)
        
        conn.commit()
        logger.info("✅ translated_text column added successfully")
        
        # Verify
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"📊 Total columns: {len(columns)}")
        logger.info(f"   translated_text exists: {'translated_text' in columns}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    add_translated_text_column()
