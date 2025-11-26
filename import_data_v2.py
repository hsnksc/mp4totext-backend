"""
Import migration data into PostgreSQL using raw SQL
Run this inside Coolify container
"""
import json
from app.database import SessionLocal, engine
from sqlalchemy import text

def import_data():
    # Read JSON data
    with open('/app/migration_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db = SessionLocal()
    conn = engine.connect()
    
    # Import transcriptions using raw SQL
    print(f"📦 Importing {len(data['transcriptions'])} transcriptions...")
    success_count = 0
    
    for t in data['transcriptions']:
        try:
            # Check if exists
            result = conn.execute(text("SELECT id FROM transcriptions WHERE id = :id"), {"id": t['id']})
            if result.fetchone():
                continue
            
            # Map old column names to new ones
            # Old: file_url, transcription_text, enhanced_text
            # New: file_path, text, cleaned_text
            
            conn.execute(text("""
                INSERT INTO transcriptions (
                    id, user_id, file_id, filename, file_size, file_path, content_type,
                    language, whisper_model, status, text, cleaned_text,
                    transcription_provider, speaker_count, segments,
                    created_at, updated_at
                ) VALUES (
                    :id, :user_id, :file_id, :filename, :file_size, :file_path, :content_type,
                    :language, :whisper_model, :status, :text, :cleaned_text,
                    :transcription_provider, :speaker_count, :segments,
                    :created_at, :updated_at
                )
            """), {
                "id": t['id'],
                "user_id": t['user_id'],
                "file_id": t.get('file_id') or f"migrated_{t['id']}",
                "filename": t.get('filename') or t.get('original_filename') or 'unknown',
                "file_size": t.get('file_size') or 0,
                "file_path": t.get('file_path') or t.get('file_url') or '',
                "content_type": t.get('content_type') or 'audio/mpeg',
                "language": t.get('language'),
                "whisper_model": t.get('whisper_model') or 'base',
                "status": t.get('status') or 'completed',
                "text": t.get('transcription_text') or t.get('text'),
                "cleaned_text": t.get('enhanced_text') or t.get('cleaned_text'),
                "transcription_provider": t.get('transcription_provider') or 'openai_whisper',
                "speaker_count": t.get('speaker_count') or 0,
                "segments": json.dumps(t.get('speaker_segments')) if t.get('speaker_segments') else None,
                "created_at": t.get('created_at'),
                "updated_at": t.get('updated_at')
            })
            success_count += 1
        except Exception as e:
            print(f"  ❌ Transcription {t['id']}: {e}")
    
    conn.commit()
    print(f"  ✅ {success_count} transcriptions imported")
    
    # Import credit transactions (skip those with non-existent transcription_id)
    print(f"📦 Importing {len(data['credit_transactions'])} credit transactions...")
    success_count = 0
    
    for ct in data['credit_transactions']:
        try:
            # Check if exists
            result = conn.execute(text("SELECT id FROM credit_transactions WHERE id = :id"), {"id": ct['id']})
            if result.fetchone():
                continue
            
            # If has transcription_id, check if transcription exists
            trans_id = ct.get('transcription_id')
            if trans_id:
                result = conn.execute(text("SELECT id FROM transcriptions WHERE id = :id"), {"id": trans_id})
                if not result.fetchone():
                    trans_id = None  # Set to NULL if transcription doesn't exist
            
            conn.execute(text("""
                INSERT INTO credit_transactions (
                    id, user_id, amount, operation_type, description,
                    transcription_id, balance_after, created_at
                ) VALUES (
                    :id, :user_id, :amount, :operation_type, :description,
                    :transcription_id, :balance_after, :created_at
                )
            """), {
                "id": ct['id'],
                "user_id": ct['user_id'],
                "amount": ct['amount'],
                "operation_type": ct['operation_type'],
                "description": ct.get('description'),
                "transcription_id": trans_id,
                "balance_after": ct.get('balance_after'),
                "created_at": ct.get('created_at')
            })
            success_count += 1
        except Exception as e:
            print(f"  ❌ Transaction {ct['id']}: {e}")
    
    conn.commit()
    print(f"  ✅ {success_count} credit transactions imported")
    
    # Update sequences
    print("🔄 Updating sequences...")
    try:
        conn.execute(text("SELECT setval('transcriptions_id_seq', COALESCE((SELECT MAX(id) FROM transcriptions), 1), true)"))
        conn.execute(text("SELECT setval('credit_transactions_id_seq', COALESCE((SELECT MAX(id) FROM credit_transactions), 1), true)"))
        conn.commit()
        print("  ✅ Sequences updated")
    except Exception as e:
        print(f"  ⚠️ Sequence update: {e}")
    
    conn.close()
    db.close()
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    import_data()
