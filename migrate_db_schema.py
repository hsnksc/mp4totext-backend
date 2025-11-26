"""
Migrate database schema: Change model_key unique constraint to composite (provider, model_key)
"""
import sqlite3
import os

DB_PATH = "mp4totext.db"

if not os.path.exists(DB_PATH):
    print(f"❌ Database not found: {DB_PATH}")
    exit(1)

print(f"🔧 Migrating database schema...")
print(f"Database: {DB_PATH}")
print()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Step 1: Create backup
    print("📦 Creating backup table...")
    cursor.execute("""
        CREATE TABLE ai_model_pricing_backup AS 
        SELECT * FROM ai_model_pricing
    """)
    backup_count = cursor.execute("SELECT COUNT(*) FROM ai_model_pricing_backup").fetchone()[0]
    print(f"   ✅ Backed up {backup_count} records")
    
    # Step 2: Drop old table
    print("\n🗑️  Dropping old table...")
    cursor.execute("DROP TABLE ai_model_pricing")
    print("   ✅ Dropped")
    
    # Step 3: Create new table with composite unique constraint
    print("\n🏗️  Creating new table with composite unique constraint...")
    cursor.execute("""
        CREATE TABLE ai_model_pricing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_key VARCHAR NOT NULL,
            model_name VARCHAR NOT NULL,
            provider VARCHAR NOT NULL DEFAULT 'gemini',
            credit_multiplier FLOAT NOT NULL DEFAULT 1.0,
            description VARCHAR,
            api_cost_per_1m_input FLOAT,
            api_cost_per_1m_output FLOAT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            is_default BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            UNIQUE(provider, model_key)
        )
    """)
    print("   ✅ Created with UNIQUE(provider, model_key)")
    
    # Step 4: Copy data back
    print("\n📥 Copying data back...")
    cursor.execute("""
        INSERT INTO ai_model_pricing 
        SELECT * FROM ai_model_pricing_backup
    """)
    new_count = cursor.execute("SELECT COUNT(*) FROM ai_model_pricing").fetchone()[0]
    print(f"   ✅ Copied {new_count} records")
    
    # Step 5: Create indexes
    print("\n🔍 Creating indexes...")
    cursor.execute("CREATE INDEX ix_ai_model_pricing_id ON ai_model_pricing (id)")
    cursor.execute("CREATE INDEX ix_ai_model_pricing_model_key ON ai_model_pricing (model_key)")
    print("   ✅ Indexes created")
    
    # Step 6: Drop backup table
    print("\n🗑️  Dropping backup table...")
    cursor.execute("DROP TABLE ai_model_pricing_backup")
    print("   ✅ Backup dropped")
    
    # Commit changes
    conn.commit()
    
    print("\n" + "=" * 80)
    print("✅ Migration successful!")
    print("=" * 80)
    print("\n📊 Verification:")
    
    # Show schema
    schema = cursor.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name='ai_model_pricing'
    """).fetchone()[0]
    print(schema)
    
except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    conn.rollback()
    
    # Try to restore from backup if it exists
    try:
        cursor.execute("SELECT COUNT(*) FROM ai_model_pricing_backup")
        print("\n🔄 Attempting to restore from backup...")
        cursor.execute("DROP TABLE IF EXISTS ai_model_pricing")
        cursor.execute("ALTER TABLE ai_model_pricing_backup RENAME TO ai_model_pricing")
        conn.commit()
        print("✅ Restored from backup")
    except:
        print("❌ Could not restore from backup")
    
    import traceback
    traceback.print_exc()
finally:
    conn.close()
