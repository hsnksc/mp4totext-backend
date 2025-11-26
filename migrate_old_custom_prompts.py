"""
Migrate old custom_prompt and custom_prompt_result to custom_prompt_history format
"""
import sqlite3
import json
from datetime import datetime

def migrate_custom_prompts():
    conn = sqlite3.connect('mp4totext.db')
    cursor = conn.cursor()
    
    # Find all transcriptions with old custom prompts but no history
    cursor.execute("""
        SELECT id, custom_prompt, custom_prompt_result, gemini_metadata
        FROM transcriptions 
        WHERE custom_prompt IS NOT NULL 
        AND (custom_prompt_history IS NULL OR custom_prompt_history = '[]' OR custom_prompt_history = 'null')
    """)
    
    rows = cursor.fetchall()
    print(f"Found {len(rows)} transcriptions to migrate")
    
    migrated = 0
    for row in rows:
        transcription_id, custom_prompt, custom_prompt_result, gemini_metadata_str = row
        
        if not custom_prompt or not custom_prompt_result:
            print(f"  ⏭️  Skipping ID {transcription_id}: Empty prompt or result")
            continue
        
        # Parse gemini_metadata to get model/provider info if available
        model = "Unknown"
        provider = "Unknown"
        credits_used = 0
        
        if gemini_metadata_str:
            try:
                gemini_metadata = json.loads(gemini_metadata_str)
                if "last_custom_prompt" in gemini_metadata:
                    model = gemini_metadata["last_custom_prompt"].get("model", "Unknown")
                    provider = gemini_metadata["last_custom_prompt"].get("provider", "Unknown")
            except:
                pass
        
        # Create history entry
        history_entry = {
            "prompt": custom_prompt,
            "result": custom_prompt_result,
            "model": model,
            "provider": provider,
            "text_source": "enhanced_text",  # Default assumption
            "timestamp": datetime.now().isoformat(),
            "credits_used": credits_used,
            "metadata": {
                "migrated": True,
                "migration_date": datetime.now().isoformat()
            }
        }
        
        history = [history_entry]
        
        # Update the record
        cursor.execute("""
            UPDATE transcriptions 
            SET custom_prompt_history = ?
            WHERE id = ?
        """, (json.dumps(history, ensure_ascii=False), transcription_id))
        
        migrated += 1
        print(f"  ✅ Migrated ID {transcription_id}: {provider}/{model}")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Migration complete! Migrated {migrated} transcriptions")
    print(f"   Old custom prompts are now visible in Custom Prompt History")

if __name__ == "__main__":
    print("🔄 Starting migration of old custom prompts to history format...\n")
    migrate_custom_prompts()
