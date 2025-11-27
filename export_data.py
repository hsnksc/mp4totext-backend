"""
Export SQLite data to JSON for Coolify import
"""
import sqlite3
import json
from datetime import datetime

SQLITE_PATH = "mp4totext.db"
OUTPUT_PATH = "migration_data.json"

def serialize_row(row):
    """Convert sqlite3.Row to dict with JSON-safe values"""
    result = {}
    for key in row.keys():
        value = row[key]
        if isinstance(value, bytes):
            value = value.decode('utf-8', errors='ignore')
        result[key] = value
    return result

def main():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    data = {}
    
    # Export transcriptions
    print("📦 Exporting transcriptions...")
    cur.execute("SELECT * FROM transcriptions")
    data['transcriptions'] = [serialize_row(row) for row in cur.fetchall()]
    print(f"  ✅ {len(data['transcriptions'])} transcriptions")
    
    # Export credit_transactions
    print("📦 Exporting credit_transactions...")
    cur.execute("SELECT * FROM credit_transactions")
    data['credit_transactions'] = [serialize_row(row) for row in cur.fetchall()]
    print(f"  ✅ {len(data['credit_transactions'])} credit_transactions")
    
    conn.close()
    
    # Save to JSON
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Data exported to {OUTPUT_PATH}")
    print(f"   File size: {len(open(OUTPUT_PATH).read()) / 1024:.1f} KB")

if __name__ == "__main__":
    main()
