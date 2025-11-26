import sqlite3
import sys
from pathlib import Path

# Get database path
db_path = Path(__file__).parent / "mp4totext.db"

if not db_path.exists():
    print(f"❌ Database not found: {db_path}")
    sys.exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    print("🔄 Adding AssemblyAI pricing records...")
    
    # Check if records already exist
    cursor.execute("""
        SELECT COUNT(*) FROM credit_pricing_configs 
        WHERE operation_key IN ('assemblyai_speech_understanding_per_minute', 'assemblyai_llm_gateway')
    """)
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"⚠️  Found {existing_count} existing records. Updating...")
        cursor.execute("""
            UPDATE credit_pricing_configs 
            SET cost_per_unit = 1.2, 
                operation_name = 'AssemblyAI Speech Understanding',
                unit_description = 'dakika başı',
                description = 'AssemblyAI sentiment analysis, entity detection, highlights extraction',
                is_active = 1
            WHERE operation_key = 'assemblyai_speech_understanding_per_minute'
        """)
        cursor.execute("""
            UPDATE credit_pricing_configs 
            SET cost_per_unit = 3.0,
                operation_name = 'AssemblyAI LLM Gateway',
                unit_description = 'işlem başı',
                description = 'AssemblyAI LLM Gateway for summary, action items, Q&A',
                is_active = 1
            WHERE operation_key = 'assemblyai_llm_gateway'
        """)
    else:
        print("➕ Inserting new pricing records...")
        cursor.execute("""
            INSERT INTO credit_pricing_configs 
            (operation_key, operation_name, cost_per_unit, unit_description, description, is_active)
            VALUES 
            ('assemblyai_speech_understanding_per_minute', 
             'AssemblyAI Speech Understanding', 
             1.2, 
             'dakika başı', 
             'AssemblyAI sentiment analysis, entity detection, highlights extraction',
             1)
        """)
        cursor.execute("""
            INSERT INTO credit_pricing_configs 
            (operation_key, operation_name, cost_per_unit, unit_description, description, is_active)
            VALUES 
            ('assemblyai_llm_gateway', 
             'AssemblyAI LLM Gateway', 
             3.0, 
             'işlem başı', 
             'AssemblyAI LLM Gateway for summary, action items, Q&A',
             1)
        """)
    
    conn.commit()
    print("✅ Pricing records added/updated successfully!")
    
    # Verify
    cursor.execute("""
        SELECT operation_key, cost_per_unit, is_active 
        FROM credit_pricing_configs 
        WHERE operation_key IN ('assemblyai_speech_understanding_per_minute', 'assemblyai_llm_gateway')
    """)
    
    print("\n📋 Current AssemblyAI Pricing:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} credits (active: {bool(row[2])})")
    
except sqlite3.Error as e:
    print(f"❌ Database error: {e}")
    conn.rollback()
    sys.exit(1)
finally:
    conn.close()
