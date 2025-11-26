"""
Add model_type column to generated_images table
Support for multiple AI models (SDXL, FLUX, etc.)
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from app.database import SessionLocal, engine


def add_model_type_column():
    """Add model_type column to generated_images"""
    print("🔧 Adding model_type column to generated_images...")
    
    db = SessionLocal()
    try:
        # Add model_type column with default 'sdxl'
        db.execute(text("""
            ALTER TABLE generated_images
            ADD COLUMN model_type VARCHAR(20) NOT NULL DEFAULT 'sdxl'
        """))
        
        db.commit()
        print("✅ Successfully added model_type column")
        
        # Show updated schema
        result = db.execute(text("PRAGMA table_info(generated_images)"))
        print("\n📊 Updated generated_images schema:")
        for row in result:
            print(f"  - {row[1]}: {row[2]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_model_type_column()
