import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "mp4totext.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("📋 credit_pricing_configs table schema:")
cursor.execute("PRAGMA table_info(credit_pricing_configs)")
for row in cursor.fetchall():
    print(f"  {row[1]}: {row[2]} {'NOT NULL' if row[3] else 'NULL'}")

print("\n📊 Current records:")
cursor.execute("SELECT * FROM credit_pricing_configs ORDER BY operation_key")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
