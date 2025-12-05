"""
Add PKB fields to Source model for Mix Up sources
"""
import sqlite3
import os
from pathlib import Path

# Database path - check multiple locations
def get_db_path():
    """Find database in various locations"""
    paths = [
        os.environ.get("DATABASE_PATH", ""),
        "/data/mp4totext.db",
        "/app/data/mp4totext.db",
        "/app/mp4totext.db",
        Path(__file__).parent / "mp4totext.db",
    ]
    
    for p in paths:
        if p and os.path.exists(str(p)):
            return str(p)
    
    # Default fallback
    return str(Path(__file__).parent / "mp4totext.db")

DB_PATH = get_db_path()

def migrate():
    print(f"📦 Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
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
