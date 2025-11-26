"""
Add post-processing columns to transcriptions table
"""
import sqlite3
import os

# Get database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'mp4totext.db')

print(f"📦 Connecting to database: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(transcriptions)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"📋 Existing columns ({len(existing_columns)}): {', '.join(existing_columns)}")

# Columns to add
new_columns = {
    'lecture_notes': 'TEXT',
    'custom_prompt': 'TEXT',
    'gemini_mode': 'VARCHAR(20)',
    'custom_model_path': 'VARCHAR(500)',
    'original_filename': 'VARCHAR(255)',
    'error_message': 'TEXT',
    'error': 'TEXT',
    'retry_count': 'INTEGER DEFAULT 0',
    'updated_at': 'DATETIME',
    'started_at': 'DATETIME',
    'completed_at': 'DATETIME'
}

# Add missing columns
added_count = 0
for column_name, column_type in new_columns.items():
    if column_name not in existing_columns:
        try:
            sql = f"ALTER TABLE transcriptions ADD COLUMN {column_name} {column_type}"
            cursor.execute(sql)
            print(f"✅ Added column: {column_name} ({column_type})")
            added_count += 1
        except sqlite3.OperationalError as e:
            print(f"⚠️  Column {column_name} already exists or error: {e}")
    else:
        print(f"✓  Column {column_name} already exists")

# Commit changes
conn.commit()
conn.close()

print(f"\n🎉 Migration complete! Added {added_count} new columns.")
