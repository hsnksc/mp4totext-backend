"""
Migration script: Add cleaned_text column to transcriptions table
Together AI transcript cleaning (filler removal, grammar fixes)
"""

from sqlalchemy import create_engine, text
from app.settings import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

def migrate():
    """Add cleaned_text column to transcriptions table"""
    try:
        with engine.begin() as conn:
            # Check if column already exists
            result = conn.execute(text("PRAGMA table_info(transcriptions)"))
            columns = [row[1] for row in result]
            
            if 'cleaned_text' not in columns:
                print("Adding cleaned_text column...")
                conn.execute(text(
                    'ALTER TABLE transcriptions ADD COLUMN cleaned_text TEXT'
                ))
                print('✅ cleaned_text column added successfully')
            else:
                print('ℹ️  cleaned_text column already exists')
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
