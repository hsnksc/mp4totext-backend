"""
Check ID 230 AssemblyAI features in database
"""

import sqlite3
import json

db_path = "mp4totext.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get transcription 230
cursor.execute("""
    SELECT 
        id,
        status,
        sentiment_analysis,
        auto_chapters,
        entities,
        topics,
        content_safety,
        highlights,
        lemur_summary,
        lemur_action_items
    FROM transcriptions 
    WHERE id = 230
""")

row = cursor.fetchone()

if row:
    print("=" * 80)
    print(f"📋 Transcription ID: {row[0]}")
    print(f"   Status: {row[1]}")
    print("=" * 80)
    
    print("\n🎯 SPEECH UNDERSTANDING FEATURES:")
    print(f"   Sentiment Analysis: {'✅ YES' if row[2] else '❌ NULL'}")
    if row[2]:
        data = json.loads(row[2])
        print(f"      → {len(data) if isinstance(data, list) else 'dict'} results")
    
    print(f"   Chapters: {'✅ YES' if row[3] else '❌ NULL'}")
    if row[3]:
        data = json.loads(row[3])
        print(f"      → {len(data) if isinstance(data, list) else 'dict'} chapters")
    
    print(f"   Entities: {'✅ YES' if row[4] else '❌ NULL'}")
    if row[4]:
        data = json.loads(row[4])
        print(f"      → {len(data) if isinstance(data, list) else 'dict'} entities")
    
    print(f"   Topics: {'✅ YES' if row[5] else '❌ NULL'}")
    if row[5]:
        data = json.loads(row[5])
        print(f"      → {len(data) if isinstance(data, list) else 'dict'} topics")
    
    print(f"   Content Safety: {'✅ YES' if row[6] else '❌ NULL'}")
    if row[6]:
        data = json.loads(row[6])
        print(f"      → {type(data)} data")
    
    print(f"   Highlights: {'✅ YES' if row[7] else '❌ NULL'}")
    if row[7]:
        data = json.loads(row[7])
        print(f"      → {len(data) if isinstance(data, list) else 'dict'} highlights")
    
    print("\n🤖 LEMUR FEATURES:")
    print(f"   Summary: {'✅ YES' if row[8] else '❌ NULL'}")
    if row[8]:
        summary = row[8]
        print(f"      → {len(summary)} chars")
    
    print(f"   Action Items: {'✅ YES' if row[9] else '❌ NULL'}")
    if row[9]:
        data = json.loads(row[9])
        print(f"      → {type(data)} data")
    
    print("\n" + "=" * 80)
    
    # Show sample data
    if row[3]:  # Chapters
        print("\n📖 SAMPLE CHAPTERS:")
        chapters = json.loads(row[3])
        for i, ch in enumerate(chapters[:2], 1):
            print(f"   {i}. {ch.get('headline', 'No headline')}")
            print(f"      Gist: {ch.get('gist', 'No gist')}")
    
    if row[7]:  # Highlights
        print("\n✨ SAMPLE HIGHLIGHTS:")
        highlights = json.loads(row[7])
        for i, hl in enumerate(highlights[:5], 1):
            print(f"   {i}. {hl.get('text', 'No text')} (count: {hl.get('count', 0)})")
    
else:
    print("❌ No transcription found with ID 230")

conn.close()
