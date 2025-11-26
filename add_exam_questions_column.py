"""
Add exam_questions column to transcriptions table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_exam_questions_column():
    """Add exam_questions column to existing transcriptions table"""
    try:
        conn = sqlite3.connect('mp4totext.db')
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'exam_questions' in columns:
            logger.info("✅ exam_questions column already exists")
            conn.close()
            return
        
        # Add column
        logger.info("📝 Adding exam_questions column to transcriptions table...")
        cursor.execute("""
            ALTER TABLE transcriptions 
            ADD COLUMN exam_questions TEXT
        """)
        
        conn.commit()
        logger.info("✅ exam_questions column added successfully")
        
        # Verify
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"📊 Total columns: {len(columns)}")
        logger.info(f"   exam_questions exists: {'exam_questions' in columns}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    add_exam_questions_column()
