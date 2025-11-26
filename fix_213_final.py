"""
Final çözüm: ID #213'ü RAW SQL ile silme
"""
import sqlite3

conn = sqlite3.connect('mp4totext.db')
cursor = conn.cursor()

print("🔍 Transcriptions tablo yapısı:")
columns = cursor.execute("PRAGMA table_info(transcriptions)").fetchall()
for col in columns[:10]:  # İlk 10 kolonu göster
    print(f"  - {col[1]} ({col[2]})")

print("\n" + "="*60)
print("🔍 ID #213 ARANIYOR...")
result = cursor.execute("SELECT id, filename, speakers FROM transcriptions WHERE id = 213").fetchone()

if result:
    print(f"\n⚠️  BULUNDU!")
    print(f"   ID: {result[0]}")
    print(f"   File: {result[1]}")
    print(f"   Speakers: {result[2]}")
    
    print("\n🗑️  SİLİNİYOR...")
    cursor.execute("DELETE FROM transcriptions WHERE id = 213")
    conn.commit()
    
    # Tekrar kontrol
    check = cursor.execute("SELECT id FROM transcriptions WHERE id = 213").fetchone()
    if check is None:
        print("✅ ID #213 BAŞARIYLA SİLİNDİ!")
    else:
        print("❌ SİLME BAŞARISIZ!")
else:
    print("✅ ID #213 zaten yok")

conn.close()
