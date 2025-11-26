"""
Add Generated Images Table
Creates table for AI-generated images from transcripts
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.settings import get_settings
from app.database import Base
from app.models.generated_image import GeneratedImage
from app.models.transcription import Transcription

settings = get_settings()

def add_generated_images_table():
    """Add generated_images table to database"""
    
    print("=" * 80)
    print("ADDING GENERATED IMAGES TABLE")
    print("=" * 80)
    
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if table exists (SQLite compatible)
        result = session.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='generated_images';
        """))
        table_exists = result.scalar() is not None
        
        if table_exists:
            print("✅ generated_images table already exists")
            return
        
        print("📝 Creating generated_images table...")
        
        # Create table
        Base.metadata.create_all(engine, tables=[GeneratedImage.__table__])
        
        print("✅ generated_images table created successfully")
        
        # Verify table structure (SQLite compatible)
        result = session.execute(text("""
            PRAGMA table_info(generated_images);
        """))
        
        print("\n📋 Table Structure:")
        print("-" * 60)
        for row in result:
            print(f"  {row[1]:20} {row[2]}")  # column name, type
        print("-" * 60)
        
        session.commit()
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    add_generated_images_table()
