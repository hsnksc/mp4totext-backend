"""
Basit Pyannote Test - Mevcut dosya ile Modal'a gönder

ID 205'teki dosyayı MinIO'ya yükleyip Modal'a test et
"""

import time
import os
from app.database import SessionLocal
from app.models.transcription import Transcription
from app.services.modal_service import get_modal_service
from app.services.storage import get_storage_service

storage_service = get_storage_service()

def test_with_local_file():
    """Yerel dosya ile test"""
    
    print("=" * 70)
    print("🧪 PYANNOTE SIMPLE TEST - Yerel Dosya")
    print("=" * 70)
    
    # Get ID 205
    db = SessionLocal()
    t = db.query(Transcription).filter(Transcription.id == 205).first()
    
    print(f"\n📁 Source File:")
    print(f"   - ID: {t.id}")
    print(f"   - Filename: {t.filename}")
    print(f"   - Duration: {t.duration}s ({t.duration/60:.1f} min)")
    print(f"   - File Path: {t.file_path}")
    
    # Check if file exists
    if not os.path.exists(t.file_path):
        print(f"\n❌ File not found: {t.file_path}")
        db.close()
        return
    
    print(f"   ✅ File exists: {os.path.getsize(t.file_path) / 1024 / 1024:.1f} MB")
    
    # Upload to MinIO
    print(f"\n📦 Uploading to MinIO...")
    try:
        file_id = storage_service.upload_file(
            file_path=t.file_path,
            filename=t.filename,
            user_id=t.user_id
        )
        print(f"   ✅ Uploaded: {file_id}")
        
        # Generate presigned URL
        audio_url = storage_service.get_presigned_url(file_id)
        print(f"   ✅ Presigned URL generated (expires in 1h)")
        print(f"   🔗 URL: {audio_url[:80]}...")
        
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        db.close()
        return
    
    # Test transcription
    print(f"\n🚀 Starting Modal Transcription...")
    print(f"   - Model: base")
    print(f"   - Language: {t.language or 'auto-detect'}")
    print(f"   - Diarization: {t.enable_diarization}")
    print(f"   - Min Speakers: {t.min_speakers}")
    print(f"   - Max Speakers: {t.max_speakers}")
    
    modal_service = get_modal_service()
    start_time = time.time()
    
    try:
        result = modal_service.transcribe_audio(
            audio_url=audio_url,
            model="base",
            language=t.language,
            task="transcribe",
            enable_diarization=t.enable_diarization or False,
            min_speakers=t.min_speakers,
            max_speakers=t.max_speakers
        )
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("✅ TRANSCRIPTION COMPLETED")
        print("=" * 70)
        
        # Performance Analysis
        print(f"\n📊 Performance Metrics:")
        print(f"   - Audio Duration: {t.duration:.1f}s ({t.duration/60:.1f} min)")
        print(f"   - Total Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        print(f"   - Ratio: {elapsed/t.duration:.3f}x")
        
        if 'performance' in result:
            perf = result['performance']
            whisper_time = perf.get('whisper_time', 0)
            diarization_time = perf.get('diarization_time', 0)
            
            print(f"\n📊 Breakdown:")
            print(f"   - Whisper Time: {whisper_time:.1f}s")
            print(f"   - Diarization Time: {diarization_time:.1f}s")
            print(f"   - Overhead: {elapsed - whisper_time - diarization_time:.1f}s")
        
        # Target Comparison
        target_time = 60  # 5min audio → 60s target
        actual_ratio = elapsed / t.duration
        target_ratio = target_time / 300  # 0.2x
        
        print(f"\n🎯 Target Analysis:")
        print(f"   - Current Ratio: {actual_ratio:.3f}x")
        print(f"   - Target Ratio: {target_ratio:.3f}x (5min → 60s)")
        
        if t.duration > 0:
            # Scale to 5-minute audio
            scaled_time = (elapsed / t.duration) * 300
            print(f"   - Scaled to 5min: {scaled_time:.1f}s")
            
            if scaled_time <= 60:
                print(f"   ✅ TARGET MET! ({scaled_time:.1f}s ≤ 60s)")
            else:
                diff = scaled_time - 60
                print(f"   ❌ ABOVE TARGET by {diff:.1f}s ({diff/60*100:.1f}% over)")
                improvement = (scaled_time - 60) / scaled_time * 100
                print(f"   - Need {improvement:.1f}% improvement")
        
        # Transcription quality check
        print(f"\n📝 Result Quality:")
        print(f"   - Language: {result.get('language', 'unknown')}")
        print(f"   - Text Length: {len(result.get('text', ''))} chars")
        print(f"   - Segments: {len(result.get('segments', []))}")
        
        if t.enable_diarization:
            print(f"   - Speakers Detected: {result.get('speaker_count', 0)}")
        
        # Show preview
        text = result.get('text', '')
        if text:
            print(f"\n📄 Preview (first 200 chars):")
            print(f'   "{text[:200]}..."')
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print("❌ TRANSCRIPTION FAILED")
        print("=" * 70)
        print(f"Error: {type(e).__name__}: {e}")
        print(f"Elapsed: {elapsed:.1f}s")
        
        import traceback
        print(f"\nFull traceback:")
        print(traceback.format_exc())
    
    finally:
        # Cleanup
        try:
            storage_service.delete_file(file_id)
            print(f"\n🗑️ MinIO file cleaned up: {file_id}")
        except:
            pass
        
        db.close()

if __name__ == "__main__":
    test_with_local_file()
