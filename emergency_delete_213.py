"""
EMERGENCY: Delete ID #213 using raw SQL DELETE
"""
import sqlite3

# Direct SQLite connection
conn = sqlite3.connect('mp4totext.db')
cursor = conn.cursor()

# Check before
cursor.execute("SELECT id, filename, speakers FROM transcriptions WHERE id = 213")
before = cursor.fetchone()
print(f"ÖNCE: {before}")

# DELETE with raw SQL
cursor.execute("DELETE FROM transcriptions WHERE id = 213")
conn.commit()

# Check after  
cursor.execute("SELECT id, filename, speakers FROM transcriptions WHERE id = 213")
after = cursor.fetchone()

if after is None:
    print("✅ ID #213 BAŞARIYLA SİLİNDİ!")
else:
    print(f"❌ HATA: ID #213 hâlâ var: {after}")

conn.close()
