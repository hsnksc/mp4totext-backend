import sqlite3
import json

conn = sqlite3.connect('mp4totext.db')
cursor = conn.cursor()
cursor.execute('SELECT custom_prompt_history FROM transcriptions WHERE id = 167')
row = cursor.fetchone()
history = json.loads(row[0]) if row[0] else []

print(f'Total entries: {len(history)}\n')

for i, entry in enumerate(history[:2]):
    print(f'Entry #{i+1}:')
    print(f'  Model: {entry.get("model", "N/A")}')
    print(f'  Provider: {entry.get("provider", "N/A")}')
    print(f'  Credits: {entry.get("credits_used", 0)}')
    print(f'  Timestamp: {entry.get("timestamp", "N/A")}')
    print(f'  Prompt: {entry.get("prompt", "N/A")[:50]}...')
    print()
