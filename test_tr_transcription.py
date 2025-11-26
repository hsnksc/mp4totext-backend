"""
ID #217 için manual AssemblyAI test - Türkçe (tr) dil kodu ile
"""
from app.services.assemblyai_service import get_assemblyai_service
from app.services.storage import get_storage_service
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.transcription import Transcription

# Database session
db = SessionLocal()

try:
    # Get transcription #217
    trans = db.query(Transcription).filter(Transcription.id == 217).first()
    
    if not trans:
        print("❌ Transcription #217 bulunamadı!")
        exit(1)
    
    print(f"📄 ID #217: {trans.filename}")
    print(f"   Current Language: {trans.language}")
    print(f"   Current Provider: {trans.transcription_provider}")
    print(f"   Current Text: {trans.text[:100]}")
    print()
    
    # Initialize services
    assemblyai_service = get_assemblyai_service()
    storage_service = get_storage_service()
    
    # Generate presigned MinIO URL
    from pathlib import Path
    
    print(f"   File path (DB): {trans.file_path}")
    
    # Get local file path
    local_path = Path(trans.file_path)
    
    if not local_path.exists():
        print(f"❌ Lokal dosya bulunamadı: {local_path}")
        exit(1)
    
    print(f"   Local file exists: {local_path}")
    
    # Upload to MinIO and get presigned URL
    minio_url = storage_service.upload_to_minio(str(local_path))
    
    if not minio_url:
        print("❌ MinIO upload failed!")
        exit(1)
    
    print(f"🌐 MinIO URL: {minio_url[:80]}...")
    print()
    print("🚀 AssemblyAI'yı Türkçe (tr) dil kodu ile çağırıyorum...")
    print()
    
    # Transcribe with Turkish language code
    result = assemblyai_service.transcribe_audio(
        audio_url=minio_url,
        language="tr",  # Turkish language code
        enable_diarization=True
    )
    
    print()
    print("="*80)
    print("✅ SONUÇ:")
    print("="*80)
    print(f"📝 Metin: {result['text']}")
    print()
    print(f"🌍 Dil: {result.get('language', 'unknown')}")
    print(f"👥 Konuşmacı Sayısı: {result.get('speaker_count', 0)}")
    print(f"📊 Segment Sayısı: {len(result.get('segments', []))}")
    print(f"⏱️ İşlem Süresi: {result.get('processing_time', 0):.1f}s")
    
    # Update database
    trans.text = result["text"]
    trans.detected_language = result.get("language", "tr")
    trans.transcription_provider = "assemblyai"
    trans.language = "tr"
    db.commit()
    
    print()
    print("✅ Database güncellendi!")
    
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
