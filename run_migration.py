"""
Migration script for AssemblyAI features - To be run directly without imports
"""
import sqlite3
import os

# Get database path
db_path = os.path.join(os.path.dirname(__file__), "mp4totext.db")

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Columns to add
columns = [
    ("sentiment_analysis", "JSON"),
    ("auto_chapters", "JSON"),
    ("entities", "JSON"),
    ("topics", "JSON"),
    ("content_safety", "JSON"),
    ("highlights", "JSON"),
    ("lemur_summary", "TEXT"),
    ("lemur_questions_answers", "JSON"),
    ("lemur_action_items", "JSON"),
    ("lemur_custom_tasks", "JSON"),
    ("assemblyai_features_enabled", "JSON")
]

print("🚀 Starting migration...")
print("=" * 50)

added = 0
skipped = 0

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE transcriptions ADD COLUMN {col_name} {col_type}")
        print(f"✅ Added: {col_name} ({col_type})")
        added += 1
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"⏭️  Skipped: {col_name} (already exists)")
            skipped += 1
        else:
            print(f"❌ Error adding {col_name}: {e}")

conn.commit()
conn.close()

print("=" * 50)
print(f"✅ Migration completed!")
print(f"   Added: {added} columns")
print(f"   Skipped: {skipped} columns")
print(f"   Total: {added + skipped}/{len(columns)} columns")
