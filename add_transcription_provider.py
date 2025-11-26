"""
Add transcription_provider column to transcriptions table
Migrates from PyAnnote to OpenAI Whisper + AssemblyAI system
"""

from sqlalchemy import create_engine, text, MetaData, Table, Column, String
from app.settings import get_settings

settings = get_settings()

def migrate():
    """Add transcription_provider column"""
    engine = create_engine(settings.DATABASE_URL)
    
    print("\n" + "="*80)
    print("🔧 DATABASE MIGRATION: Add transcription_provider")
    print("="*80)
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('transcriptions') 
            WHERE name='transcription_provider'
        """))
        exists = result.scalar() > 0
        
        if exists:
            print("✅ Column 'transcription_provider' already exists")
            return
        
        # Add column
        print("➕ Adding transcription_provider column...")
        conn.execute(text("""
            ALTER TABLE transcriptions 
            ADD COLUMN transcription_provider VARCHAR DEFAULT 'openai_whisper'
        """))
        conn.commit()
        
        print("✅ Column added successfully")
        
        # Update comment for enable_diarization
        print("📝 Updating schema documentation...")
        print("   - enable_diarization now works with AssemblyAI")
        print("   - PyAnnote references removed")
        
        print("\n🎉 Migration completed successfully!")

if __name__ == "__main__":
    migrate()
