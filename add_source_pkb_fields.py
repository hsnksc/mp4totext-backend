"""
Add PKB fields to Source model for Mix Up sources
"""
import sqlite3
import os
import sys
from pathlib import Path

# Database path - check multiple locations
def get_db_path():
    """Find database in various locations"""
    paths = [
        os.environ.get("DATABASE_PATH", ""),
        os.environ.get("DATABASE_URL", "").replace("sqlite:///", ""),  # Handle SQLAlchemy URL
        "/data/mp4totext.db",
        "/app/data/mp4totext.db", 
        "/app/mp4totext.db",
        str(Path(__file__).parent / "mp4totext.db"),
        "./mp4totext.db",
    ]
    
    print(f"🔍 Searching for database in: {paths}")
    
    for p in paths:
        if p and os.path.exists(str(p)):
            print(f"✅ Found database at: {p}")
            return str(p)
    
    # Default fallback
    default = str(Path(__file__).parent / "mp4totext.db")
    print(f"⚠️ No database found, using default: {default}")
    return default

def migrate():
    DB_PATH = get_db_path()
    print(f"📦 Connecting to database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file does not exist: {DB_PATH}")
        print("   Available files in /app:")
        try:
            for f in os.listdir("/app"):
                print(f"     - {f}")
        except:
            pass
        print("   Available files in current directory:")
        for f in os.listdir("."):
            print(f"     - {f}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check if sources table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sources'")
    if not cursor.fetchone():
        print("❌ 'sources' table does not exist! Skipping migration.")
        conn.close()
        return
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(sources)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"📋 Existing columns: {existing_columns}")
    
    # PKB fields to add
    pkb_fields = [
        ("pkb_enabled", "BOOLEAN DEFAULT 0"),
        ("pkb_status", "VARCHAR(50) DEFAULT 'not_created'"),  # not_created, processing, ready, error
        ("pkb_collection_name", "VARCHAR(255)"),
        ("pkb_chunk_count", "INTEGER DEFAULT 0"),
        ("pkb_embedding_model", "VARCHAR(100)"),
        ("pkb_chunk_size", "INTEGER"),
        ("pkb_chunk_overlap", "INTEGER"),
        ("pkb_created_at", "DATETIME"),
        ("pkb_credits_used", "FLOAT DEFAULT 0.0"),
        ("pkb_error_message", "TEXT"),
    ]
    
    added = []
    for field_name, field_type in pkb_fields:
        if field_name not in existing_columns:
            try:
                sql = f"ALTER TABLE sources ADD COLUMN {field_name} {field_type}"
                cursor.execute(sql)
                added.append(field_name)
                print(f"✅ Added column: {field_name}")
            except Exception as e:
                print(f"⚠️ Error adding {field_name}: {e}")
        else:
            print(f"⏭️ Column already exists: {field_name}")
    
    conn.commit()
    conn.close()
    
    if added:
        print(f"\n✅ Migration complete! Added {len(added)} columns: {added}")
    else:
        print("\n✅ All columns already exist. No changes needed.")


if __name__ == "__main__":
    migrate()
