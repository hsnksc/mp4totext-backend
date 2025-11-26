import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "mp4totext.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("📊 Son AssemblyAI transcription:")
cursor.execute("""
    SELECT 
        id, 
        filename, 
        transcription_provider,
        sentiment_analysis,
        entities,
        highlights,
        lemur_summary,
        assemblyai_features_enabled,
        status
    FROM transcriptions 
    WHERE transcription_provider = 'assemblyai'
    ORDER BY id DESC 
    LIMIT 1
""")

row = cursor.fetchone()
if row:
    print(f"\nID: {row[0]}")
    print(f"Filename: {row[1]}")
    print(f"Provider: {row[2]}")
    print(f"Sentiment Analysis: {row[3]}")
    print(f"Entities: {row[4]}")
    print(f"Highlights: {row[5]}")
    print(f"LeMUR Summary: {row[6]}")
    print(f"Features Enabled: {row[7]}")
    print(f"Status: {row[8]}")
else:
    print("❌ No AssemblyAI transcriptions found")

conn.close()
