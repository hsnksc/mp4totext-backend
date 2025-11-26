"""
ID #215 ve #216 Türkçe transcription sorununu kontrol et
"""
import sqlite3

conn = sqlite3.connect('mp4totext.db')
cursor = conn.cursor()

print("🔍 ID #215 ve #216 Detayları:")
print("="*80)

results = cursor.execute("""
    SELECT 
        id,
        filename,
        language,
        transcription_provider,
        SUBSTR(text, 1, 200) as text_preview
    FROM transcriptions 
    WHERE id IN (215, 216)
    ORDER BY id
""").fetchall()

for row in results:
    print(f"\n📄 ID #{row[0]}: {row[1]}")
    print(f"   Dil: {row[2]}")
    print(f"   Provider: {row[3]}")
    print(f"   Text İlk 200 Karakter:")
    print(f"   {row[4]}")
    print("   " + "-"*76)

conn.close()
