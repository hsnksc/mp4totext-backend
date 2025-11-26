"""
Fix ID 230 - Set empty list to NULL for content_safety
"""
import sqlite3

db_path = "mp4totext.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔧 Fixing transcription #230...")

# Update empty arrays to NULL
cursor.execute("""
    UPDATE transcriptions 
    SET content_safety = NULL
    WHERE id = 230 AND content_safety = '[]'
""")

rows_affected = cursor.rowcount
conn.commit()
conn.close()

print(f"✅ Fixed {rows_affected} row(s)")
print("🔄 Şimdi FastAPI'yi yeniden başlatın (python run.py)")
