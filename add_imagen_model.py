"""
Add Imagen-4 model support to generated_images table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from sqlalchemy import text

def add_imagen_model():
    """Add Imagen-4 as a valid model_type"""
    db = SessionLocal()
    
    try:
        print("🔧 Adding Imagen-4 model support...")
        
        # Check if model_type column allows 'imagen'
        # SQLite doesn't have ALTER COLUMN, so we just verify the column exists
        result = db.execute(text("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name='generated_images'
        """))
        
        table_schema = result.fetchone()[0]
        print(f"✅ Current schema: {table_schema}")
        
        # Insert a test record to verify it works (use existing transcription)
        db.execute(text("""
            INSERT INTO generated_images 
            (transcription_id, user_id, prompt, model_type, style, image_url, filename, created_at)
            VALUES (1, 1, 'Test Imagen', 'imagen', 'professional', 'test.png', 'test.png', datetime('now'))
        """))
        
        # Delete the test record
        db.execute(text("""
            DELETE FROM generated_images 
            WHERE prompt = 'Test Imagen' AND model_type = 'imagen'
        """))
        
        db.commit()
        
        print("✅ Imagen-4 model support verified!")
        print("\n📊 Available models:")
        print("   - sdxl (Stable Diffusion XL - A10G)")
        print("   - flux (FLUX.1-schnell - H100)")
        print("   - imagen (Google Imagen-4 - Replicate)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_imagen_model()
