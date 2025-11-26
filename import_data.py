"""
Import migration data into PostgreSQL
Run this inside Coolify container
"""
import json
import os
from app.database import SessionLocal
from app.models.transcription import Transcription
from app.models.credit_transaction import CreditTransaction

def import_data():
    # Read JSON data - file is in /app/ directory (same as script)
    with open('/app/migration_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    db = SessionLocal()
    
    # Import transcriptions
    print(f"📦 Importing {len(data['transcriptions'])} transcriptions...")
    for t in data['transcriptions']:
        try:
            existing = db.query(Transcription).filter(Transcription.id == t['id']).first()
            if existing:
                continue
            
            transcription = Transcription(
                id=t['id'],
                user_id=t['user_id'],
                filename=t.get('filename'),
                original_filename=t.get('original_filename'),
                file_path=t.get('file_path'),
                file_url=t.get('file_url'),
                duration=t.get('duration'),
                language=t.get('language'),
                whisper_model=t.get('whisper_model'),
                status=t.get('status', 'completed'),
                transcription_text=t.get('transcription_text'),
                enhanced_text=t.get('enhanced_text'),
                transcription_provider=t.get('transcription_provider'),
                created_at=t.get('created_at'),
                updated_at=t.get('updated_at'),
                lecture_notes=t.get('lecture_notes'),
                exam_questions=t.get('exam_questions'),
                translated_text=t.get('translated_text'),
                web_context_enrichment=t.get('web_context_enrichment'),
                custom_prompt_result=t.get('custom_prompt_result'),
                youtube_url=t.get('youtube_url'),
                youtube_title=t.get('youtube_title'),
                youtube_description=t.get('youtube_description'),
                speaker_count=t.get('speaker_count'),
                speaker_segments=t.get('speaker_segments'),
                assemblyai_features_enabled=t.get('assemblyai_features_enabled')
            )
            db.add(transcription)
        except Exception as e:
            print(f"  ❌ Transcription {t['id']}: {e}")
    
    db.commit()
    print("  ✅ Transcriptions imported")
    
    # Import credit transactions
    print(f"📦 Importing {len(data['credit_transactions'])} credit transactions...")
    for ct in data['credit_transactions']:
        try:
            existing = db.query(CreditTransaction).filter(CreditTransaction.id == ct['id']).first()
            if existing:
                continue
            
            transaction = CreditTransaction(
                id=ct['id'],
                user_id=ct['user_id'],
                amount=ct['amount'],
                operation_type=ct['operation_type'],
                description=ct.get('description'),
                transcription_id=ct.get('transcription_id'),
                balance_after=ct.get('balance_after'),
                created_at=ct.get('created_at'),
                metadata=ct.get('metadata')
            )
            db.add(transaction)
        except Exception as e:
            print(f"  ❌ Transaction {ct['id']}: {e}")
    
    db.commit()
    print("  ✅ Credit transactions imported")
    
    # Update sequences
    print("🔄 Updating sequences...")
    from sqlalchemy import text
    db.execute(text("SELECT setval('transcriptions_id_seq', (SELECT MAX(id) FROM transcriptions), true)"))
    db.execute(text("SELECT setval('credit_transactions_id_seq', (SELECT MAX(id) FROM credit_transactions), true)"))
    db.commit()
    print("  ✅ Sequences updated")
    
    db.close()
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    import_data()
