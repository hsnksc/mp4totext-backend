"""
Add PKB fields to Source model for Mix Up sources - PostgreSQL version
"""
import os
import sys

def migrate():
    """Add PKB columns to sources table (PostgreSQL)"""
    
    # Import SQLAlchemy
    from sqlalchemy import create_engine, text
    
    # Get database URL from environment
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print(f"📦 Connecting to database...")
    engine = create_engine(database_url)
    
    # PKB fields to add (PostgreSQL syntax)
    pkb_fields = [
        ("pkb_enabled", "BOOLEAN DEFAULT FALSE"),
        ("pkb_status", "VARCHAR(50) DEFAULT 'not_created'"),
        ("pkb_collection_name", "VARCHAR(255)"),
        ("pkb_chunk_count", "INTEGER DEFAULT 0"),
        ("pkb_embedding_model", "VARCHAR(100)"),
        ("pkb_chunk_size", "INTEGER"),
        ("pkb_chunk_overlap", "INTEGER"),
        ("pkb_created_at", "TIMESTAMP"),
        ("pkb_credits_used", "FLOAT DEFAULT 0.0"),
        ("pkb_error_message", "TEXT"),
    ]
    
    with engine.connect() as conn:
        # Check if sources table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sources'
            )
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            print("❌ 'sources' table does not exist! Skipping migration.")
            return
        
        # Get existing columns
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'sources'
        """))
        existing_columns = {row[0] for row in result.fetchall()}
        print(f"📋 Existing columns: {existing_columns}")
        
        added = []
        for field_name, field_type in pkb_fields:
            if field_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE sources ADD COLUMN {field_name} {field_type}"
                    conn.execute(text(alter_sql))
                    added.append(field_name)
                    print(f"  ✅ Added column: {field_name}")
                except Exception as e:
                    print(f"  ⚠️ Could not add {field_name}: {e}")
            else:
                print(f"  ℹ️ Column already exists: {field_name}")
        
        # Commit the transaction
        conn.commit()
        
        if added:
            print(f"\n✅ Migration complete! Added {len(added)} PKB columns: {added}")
        else:
            print("\n✅ No new columns needed - all PKB fields already exist")

if __name__ == "__main__":
    migrate()
