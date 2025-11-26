"""
Add custom_prompt_history column to store multiple custom prompt results
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, Column, JSON, text
from app.core.config import settings

def add_custom_prompt_history():
    """Add custom_prompt_history JSON column to transcriptions table"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT COUNT(*) as count 
                FROM pragma_table_info('transcriptions') 
                WHERE name='custom_prompt_history'
            """))
            
            if result.fetchone()[0] > 0:
                print("✅ custom_prompt_history column already exists")
                return
            
            # Add custom_prompt_history column
            print("➕ Adding custom_prompt_history column...")
            conn.execute(text("""
                ALTER TABLE transcriptions 
                ADD COLUMN custom_prompt_history TEXT
            """))
            conn.commit()
            
            print("✅ custom_prompt_history column added successfully")
            print("   Format: JSON array of {prompt, result, model, provider, timestamp}")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("Adding custom_prompt_history column")
    print("=" * 60)
    add_custom_prompt_history()
    print("✅ Migration completed!")
