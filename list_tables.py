import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "mp4totext.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("📋 Database Tables:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

conn.close()
