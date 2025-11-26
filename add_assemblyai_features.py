"""
Add AssemblyAI Speech Understanding + LeMUR columns
Migration script for new features
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from app.database import SQLALCHEMY_DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_assemblyai_features():
    """Add AssemblyAI Speech Understanding and LeMUR columns to transcriptions table"""
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    # Check if table exists
    if 'transcriptions' not in inspector.get_table_names():
        logger.error("❌ Transcriptions table not found!")
        return
    
    columns = [col['name'] for col in inspector.get_columns('transcriptions')]
    
    new_columns = {
        # Speech Understanding
        'sentiment_analysis': 'JSON',
        'auto_chapters': 'JSON',
        'entities': 'JSON',
        'topics': 'JSON',
        'content_safety': 'JSON',
        'highlights': 'JSON',
        
        # LeMUR
        'lemur_summary': 'TEXT',
        'lemur_questions_answers': 'JSON',
        'lemur_action_items': 'JSON',
        'lemur_custom_tasks': 'JSON',
        
        # Config
        'assemblyai_features_enabled': 'JSON'
    }
    
    with engine.connect() as conn:
        added_count = 0
        
        for col_name, col_type in new_columns.items():
            if col_name not in columns:
                try:
                    sql = text(f"ALTER TABLE transcriptions ADD COLUMN {col_name} {col_type}")
                    conn.execute(sql)
                    conn.commit()
                    logger.info(f"✅ Added column: {col_name} ({col_type})")
                    added_count += 1
                except Exception as e:
                    logger.error(f"❌ Error adding {col_name}: {e}")
            else:
                logger.info(f"⏭️  Column already exists: {col_name}")
        
        logger.info(f"\n📊 Summary: Added {added_count} new columns")
        logger.info(f"✅ Migration completed successfully!")


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🚀 AssemblyAI Features Migration")
    logger.info("=" * 80)
    logger.info("Adding Speech Understanding + LeMUR columns...")
    logger.info("")
    
    add_assemblyai_features()
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("🎉 Migration Complete!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("New Features Available:")
    logger.info("  📊 Sentiment Analysis")
    logger.info("  📖 Auto Chapters")
    logger.info("  🏷️  Entity Detection")
    logger.info("  📁 Topic Detection (IAB)")
    logger.info("  🛡️  Content Moderation")
    logger.info("  ⭐ Auto Highlights")
    logger.info("  🧠 LeMUR Summary")
    logger.info("  ❓ LeMUR Q&A")
    logger.info("  ✅ LeMUR Action Items")
    logger.info("")
