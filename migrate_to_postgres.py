"""
SQLite to PostgreSQL Migration Script
Migrates all data from SQLite to PostgreSQL (Coolify)

Usage:
    python migrate_to_postgres.py
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

# Source: SQLite (current)
SQLITE_PATH = "C:/Users/hasan/OneDrive/Desktop/mp4totext/mp4totext-backend/mp4totext.db"

# Target: PostgreSQL (Coolify)
# Internal URL: postgres://postgres:ynmAx9MMLaWUhWntZK9Cypbt0PGueVaCuP5ByXSiTyXZZbet7kNOADn4EeIUuBdX@tg84sccokc0oc8oog4kwko4w:5432/postgres
# Since we're accessing from outside, we need to use the public URL
# Try different connection methods:

# Option 1: Direct subdomain (if configured in Coolify)
# Option 2: gistify.pro with mapped port
# Option 3: Direct IP with port

POSTGRES_CONFIG = {
    "host": "82.29.173.6",  # Coolify server's public IP
    "port": 5433,           # Public port (mapped to internal 5432)
    "database": "postgres",
    "user": "postgres",
    "password": "ynmAx9MMLaWUhWntZK9Cypbt0PGueVaCuP5ByXSiTyXZZbet7kNOADn4EeIUuBdX",
    "sslmode": "require"    # SSL enabled as per Coolify config
}

# Tables to migrate (in order due to foreign keys)
TABLES_ORDER = [
    "users",
    "credit_pricing",
    "ai_model_pricing", 
    "transcriptions",
    "credit_transactions",
    "custom_prompt_history",
    "generated_images",
    "generated_videos"
]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_sqlite_connection():
    """Connect to SQLite database"""
    return sqlite3.connect(SQLITE_PATH)

def get_postgres_connection():
    """Connect to PostgreSQL database"""
    return psycopg2.connect(**POSTGRES_CONFIG)

def get_table_columns(sqlite_cursor, table_name):
    """Get column names for a table"""
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in sqlite_cursor.fetchall()]

def convert_value(value, col_name):
    """Convert SQLite values to PostgreSQL compatible format"""
    if value is None:
        return None
    
    # JSON columns - ensure proper format
    json_columns = [
        'assemblyai_features_enabled', 'speech_understanding', 'llm_gateway',
        'speakers', 'chapters', 'sentiment', 'entities', 'topics', 
        'content_safety', 'highlights', 'custom_prompt_history', 'metadata',
        'video_segments', 'diarization_params', 'segment_prompts', 'image_urls',
        'generation_params', 'style_config'
    ]
    
    if col_name in json_columns:
        if isinstance(value, str):
            try:
                # Validate JSON
                json.loads(value)
                return value
            except:
                return None
        return json.dumps(value) if value else None
    
    # Boolean columns
    bool_columns = [
        'is_active', 'use_llm_gateway', 'web_context_enrichment', 
        'speaker_diarization_enabled', 'is_admin'
    ]
    
    if col_name in bool_columns:
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)
    
    return value

def create_postgres_tables(pg_cursor):
    """Create tables in PostgreSQL matching SQLite schema"""
    
    # Drop existing tables in reverse order (due to foreign keys)
    for table in reversed(TABLES_ORDER):
        pg_cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    
    # Create tables
    create_statements = """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        is_admin BOOLEAN DEFAULT FALSE,
        credits FLOAT DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Credit Pricing table
    CREATE TABLE IF NOT EXISTS credit_pricing (
        id SERIAL PRIMARY KEY,
        operation_type VARCHAR(50) NOT NULL,
        credit_cost FLOAT NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- AI Model Pricing table
    CREATE TABLE IF NOT EXISTS ai_model_pricing (
        id SERIAL PRIMARY KEY,
        provider VARCHAR(50) NOT NULL,
        model_name VARCHAR(100) NOT NULL,
        model_type VARCHAR(50) DEFAULT 'text',
        cost_per_minute FLOAT DEFAULT 0.0,
        cost_per_1k_chars FLOAT DEFAULT 0.0,
        cost_per_image FLOAT DEFAULT 0.0,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(provider, model_name)
    );

    -- Transcriptions table
    CREATE TABLE IF NOT EXISTS transcriptions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        filename VARCHAR(255),
        file_url TEXT,
        audio_url TEXT,
        status VARCHAR(50) DEFAULT 'pending',
        transcription_provider VARCHAR(50) DEFAULT 'faster-whisper',
        whisper_model VARCHAR(50) DEFAULT 'base',
        language VARCHAR(10) DEFAULT 'auto',
        text TEXT,
        enhanced_text TEXT,
        exam_questions TEXT,
        translated_text TEXT,
        lecture_notes TEXT,
        ai_provider VARCHAR(50),
        ai_model VARCHAR(100),
        duration FLOAT,
        credits_used FLOAT DEFAULT 0.0,
        error_message TEXT,
        task_id VARCHAR(255),
        
        -- AssemblyAI features
        assemblyai_features_enabled JSON,
        use_llm_gateway BOOLEAN DEFAULT FALSE,
        
        -- Speech Understanding Results
        speech_understanding JSON,
        llm_gateway JSON,
        speakers JSON,
        chapters JSON,
        sentiment JSON,
        entities JSON,
        topics JSON,
        content_safety JSON,
        highlights JSON,
        
        -- Speaker Diarization
        speaker_diarization_enabled BOOLEAN DEFAULT FALSE,
        speakers_expected INTEGER,
        min_speakers INTEGER,
        max_speakers INTEGER,
        diarization_params JSON,
        
        -- Web Context Enrichment
        web_context_enrichment BOOLEAN DEFAULT FALSE,
        web_context_results TEXT,
        
        -- Custom Prompt History
        custom_prompt_history JSON,
        
        -- YouTube
        youtube_url TEXT,
        youtube_title TEXT,
        youtube_thumbnail TEXT,
        youtube_channel TEXT,
        youtube_duration INTEGER,
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    );

    -- Credit Transactions table
    CREATE TABLE IF NOT EXISTS credit_transactions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        amount FLOAT NOT NULL,
        balance_after FLOAT,
        operation_type VARCHAR(50),
        description TEXT,
        transcription_id INTEGER REFERENCES transcriptions(id),
        metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Custom Prompt History table
    CREATE TABLE IF NOT EXISTS custom_prompt_history (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        transcription_id INTEGER REFERENCES transcriptions(id),
        prompt TEXT NOT NULL,
        result TEXT,
        model VARCHAR(100),
        provider VARCHAR(50),
        credits_used FLOAT DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Generated Images table
    CREATE TABLE IF NOT EXISTS generated_images (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        transcription_id INTEGER REFERENCES transcriptions(id),
        prompt TEXT,
        style VARCHAR(100),
        provider VARCHAR(50),
        model VARCHAR(100),
        image_url TEXT,
        thumbnail_url TEXT,
        width INTEGER,
        height INTEGER,
        credits_used FLOAT DEFAULT 0.0,
        generation_params JSON,
        status VARCHAR(50) DEFAULT 'pending',
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Generated Videos table
    CREATE TABLE IF NOT EXISTS generated_videos (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        transcription_id INTEGER REFERENCES transcriptions(id),
        title VARCHAR(255),
        description TEXT,
        video_url TEXT,
        thumbnail_url TEXT,
        duration FLOAT,
        segment_count INTEGER,
        video_segments JSON,
        segment_prompts JSON,
        image_urls JSON,
        style VARCHAR(100),
        style_config JSON,
        image_provider VARCHAR(50),
        image_model VARCHAR(100),
        tts_provider VARCHAR(50),
        tts_voice VARCHAR(100),
        credits_used FLOAT DEFAULT 0.0,
        status VARCHAR(50) DEFAULT 'pending',
        error_message TEXT,
        task_id VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);
    CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);
    CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
    CREATE INDEX IF NOT EXISTS idx_generated_images_user_id ON generated_images(user_id);
    CREATE INDEX IF NOT EXISTS idx_generated_videos_user_id ON generated_videos(user_id);
    """
    
    for statement in create_statements.split(';'):
        statement = statement.strip()
        if statement:
            try:
                pg_cursor.execute(statement)
            except Exception as e:
                print(f"⚠️ Warning executing: {statement[:50]}... - {e}")

def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate a single table from SQLite to PostgreSQL"""
    print(f"\n📦 Migrating table: {table_name}")
    
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Get columns
    columns = get_table_columns(sqlite_cursor, table_name)
    print(f"   Columns: {', '.join(columns)}")
    
    # Fetch all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️ No data in table {table_name}")
        return 0
    
    print(f"   Found {len(rows)} rows")
    
    # Convert and insert data
    converted_rows = []
    for row in rows:
        converted_row = []
        for i, value in enumerate(row):
            converted_value = convert_value(value, columns[i])
            converted_row.append(converted_value)
        converted_rows.append(tuple(converted_row))
    
    # Build INSERT statement
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join([f'"{col}"' for col in columns])
    
    insert_sql = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})'
    
    # Insert data
    success_count = 0
    for row in converted_rows:
        try:
            pg_cursor.execute(insert_sql, row)
            success_count += 1
        except Exception as e:
            print(f"   ❌ Error inserting row: {e}")
            print(f"      Row: {row[:3]}...")  # Print first 3 values
    
    # Reset sequence for serial columns
    if 'id' in columns:
        try:
            pg_cursor.execute(f"""
                SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                       COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)
            """)
        except Exception as e:
            print(f"   ⚠️ Could not reset sequence: {e}")
    
    pg_conn.commit()
    print(f"   ✅ Migrated {success_count}/{len(rows)} rows")
    return success_count

def main():
    """Main migration function"""
    print("=" * 60)
    print("🚀 SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"\n📂 Source: {SQLITE_PATH}")
    print(f"🐘 Target: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}")
    
    # Check SQLite file exists
    if not os.path.exists(SQLITE_PATH):
        print(f"\n❌ SQLite database not found: {SQLITE_PATH}")
        return
    
    # Connect to databases
    print("\n🔌 Connecting to databases...")
    
    try:
        sqlite_conn = get_sqlite_connection()
        print("   ✅ SQLite connected")
    except Exception as e:
        print(f"   ❌ SQLite connection failed: {e}")
        return
    
    try:
        pg_conn = get_postgres_connection()
        print("   ✅ PostgreSQL connected")
    except Exception as e:
        print(f"   ❌ PostgreSQL connection failed: {e}")
        print(f"      Host: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
        return
    
    try:
        pg_cursor = pg_conn.cursor()
        
        # Create tables
        print("\n📋 Creating PostgreSQL tables...")
        create_postgres_tables(pg_cursor)
        pg_conn.commit()
        print("   ✅ Tables created")
        
        # Migrate each table
        print("\n" + "=" * 60)
        print("📦 MIGRATING DATA")
        print("=" * 60)
        
        total_migrated = 0
        for table in TABLES_ORDER:
            try:
                count = migrate_table(sqlite_conn, pg_conn, table)
                total_migrated += count
            except Exception as e:
                print(f"\n❌ Error migrating {table}: {e}")
        
        print("\n" + "=" * 60)
        print(f"✅ MIGRATION COMPLETE - {total_migrated} total rows migrated")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()
