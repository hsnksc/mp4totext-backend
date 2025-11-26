"""
Add YouTube fields to transcriptions table
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_youtube_columns():
    """Add youtube_url, youtube_title, youtube_duration columns to transcriptions table"""
    
    try:
        # Connect to database
        conn = sqlite3.connect('mp4totext.db')
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(transcriptions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        columns_to_add = [
            ('youtube_url', 'TEXT'),
            ('youtube_title', 'TEXT'),
            ('youtube_duration', 'INTEGER')
        ]
        
        added_columns = []
        for column_name, column_type in columns_to_add:
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE transcriptions ADD COLUMN {column_name} {column_type}")
                added_columns.append(column_name)
                logger.info(f"✅ Added column: {column_name}")
            else:
                logger.info(f"⏭️  Column already exists: {column_name}")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        if added_columns:
            logger.info(f"✅ Successfully added {len(added_columns)} column(s): {', '.join(added_columns)}")
        else:
            logger.info("✅ All YouTube columns already exist")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    add_youtube_columns()
