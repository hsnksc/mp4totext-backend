"""
Fix gemini_mode enum values in database
Convert lowercase ('text', 'note', 'custom') to uppercase ('TEXT', 'NOTE', 'CUSTOM')
"""

import sqlite3
import sys

def fix_gemini_mode_values():
    """Update all gemini_mode values to uppercase"""
    
    db_path = 'mp4totext.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current values
        cursor.execute("SELECT id, gemini_mode FROM transcriptions WHERE gemini_mode IS NOT NULL")
        rows = cursor.fetchall()
        
        print(f"📊 Found {len(rows)} transcriptions with gemini_mode")
        
        # Count by value
        from collections import Counter
        values = [row[1] for row in rows]
        counts = Counter(values)
        print(f"Current values: {dict(counts)}")
        
        # Update to uppercase
        updates = 0
        for old_val, new_val in [('text', 'TEXT'), ('note', 'NOTE'), ('custom', 'CUSTOM')]:
            cursor.execute(
                "UPDATE transcriptions SET gemini_mode = ? WHERE gemini_mode = ?",
                (new_val, old_val)
            )
            count = cursor.rowcount
            if count > 0:
                print(f"✅ Updated {count} rows: '{old_val}' → '{new_val}'")
                updates += count
        
        conn.commit()
        
        # Verify
        cursor.execute("SELECT DISTINCT gemini_mode FROM transcriptions WHERE gemini_mode IS NOT NULL")
        final_values = [row[0] for row in cursor.fetchall()]
        print(f"\n✅ Final values: {final_values}")
        print(f"✅ Total updates: {updates}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Fixing gemini_mode enum values...")
    success = fix_gemini_mode_values()
    sys.exit(0 if success else 1)
