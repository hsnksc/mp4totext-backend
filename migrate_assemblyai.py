"""Simple migration using existing app setup"""
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add new columns to transcriptions table"""
    
    new_columns = [
        ("sentiment_analysis", "JSON"),
        ("auto_chapters", "JSON"),
        ("entities", "JSON"),
        ("topics", "JSON"),
        ("content_safety", "JSON"),
        ("highlights", "JSON"),
        ("lemur_summary", "TEXT"),
        ("lemur_questions_answers", "JSON"),
        ("lemur_action_items", "JSON"),
        ("lemur_custom_tasks", "JSON"),
        ("assemblyai_features_enabled", "JSON")
    ]
    
    with engine.connect() as conn:
        added = 0
        for col_name, col_type in new_columns:
            try:
                sql = text(f"ALTER TABLE transcriptions ADD COLUMN {col_name} {col_type}")
                conn.execute(sql)
                conn.commit()
                logger.info(f"✅ Added: {col_name}")
                added += 1
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"⏭️  Exists: {col_name}")
                else:
                    logger.error(f"❌ Error: {col_name} - {e}")
        
        logger.info(f"\n✅ Migration complete! Added {added} columns")

if __name__ == "__main__":
    logger.info("🚀 Adding AssemblyAI features columns...")
    run_migration()
