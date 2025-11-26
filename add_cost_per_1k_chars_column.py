"""
Add cost_per_1k_chars column to ai_model_pricing table
For character-based credit calculation (1000 chars = X credits)
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, engine
from sqlalchemy import text

def add_column():
    """Add cost_per_1k_chars column to ai_model_pricing table"""
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text(
            "SELECT COUNT(*) as count FROM pragma_table_info('ai_model_pricing') WHERE name='cost_per_1k_chars'"
        ))
        exists = result.scalar() > 0
        
        if exists:
            print("⚠️ Column 'cost_per_1k_chars' already exists in ai_model_pricing table")
            return
        
        # Add column
        db.execute(text(
            "ALTER TABLE ai_model_pricing ADD COLUMN cost_per_1k_chars REAL"
        ))
        db.commit()
        
        print("✅ Successfully added 'cost_per_1k_chars' column to ai_model_pricing table")
        print("📝 Column type: REAL (Float)")
        print("📝 Nullable: True")
        print("📝 Usage: Store credit cost per 1000 characters for text-based pricing")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Adding cost_per_1k_chars column to ai_model_pricing table...")
    add_column()
