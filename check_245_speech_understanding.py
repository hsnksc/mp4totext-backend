import sqlite3
import json
from pathlib import Path

db_path = Path(__file__).parent / "mp4totext.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute("SELECT id, speech_understanding FROM transcriptions WHERE id = 245")
row = cursor.fetchone()

if row:
    print(f"ID: {row[0]}\n")
    if row[1]:
        data = json.loads(row[1])
        print("speech_understanding keys:", list(data.keys()))
        if 'sentiment_analysis' in data:
            print(f"\nsentiment_analysis found in speech_understanding:")
            print(json.dumps(data['sentiment_analysis'][:2] if data['sentiment_analysis'] else None, indent=2))
        else:
            print("\n❌ sentiment_analysis NOT in speech_understanding")
    else:
        print("❌ speech_understanding is NULL")
else:
    print("❌ Not found")

conn.close()
