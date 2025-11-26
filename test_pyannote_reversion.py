"""
Test Pyannote Reversion - Modal Service Health Check ve Performance Test

Bu script pyannote'a geri dönüşü test eder:
1. Modal service health check
2. Basit bir test ses dosyası ile transcription
3. Performance metrikleri (Whisper time, Diarization time, Ratio)
"""

import time
from app.services.modal_service import get_modal_service
import requests

def test_pyannote_reversion():
    """Test pyannote reversion"""
    
    print("=" * 70)
    print("🔄 PYANNOTE REVERSION TEST")
    print("=" * 70)
    
    # 1. Modal Service Health Check
    print("\n📋 Step 1: Modal Service Health Check")
    print("-" * 70)
    
    modal_service = get_modal_service()
    print(f"✅ Modal Service initialized")
    print(f"   - App Name: {modal_service.app_name}")
    
    health = modal_service.health_check()
    print(f"\n🏥 Health Check Result:")
    for key, value in health.items():
        print(f"   - {key}: {value}")
    
    if health.get("status") != "healthy":
        print("\n❌ Health check failed! Cannot proceed with test.")
        return
    
    # 2. Test Audio URL (YouTube short video - ~1 min)
    print("\n\n📋 Step 2: Test Transcription")
    print("-" * 70)
    
    # Short English conversation test
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # 3:32 duration
    
    print(f"🎵 Test Audio: {test_url}")
    print(f"⏱️ Expected duration: ~3-4 minutes")
    print(f"🎯 Target performance: <60s for 5min audio (0.2x ratio)")
    print(f"📊 This ~3.5min audio should complete in ~42s (0.2x ratio)")
    
    print("\n🚀 Starting transcription...")
    start_time = time.time()
    
    try:
        result = modal_service.transcribe_audio(
            audio_url=test_url,
            model="base",  # Using base model as per modal_whisper_function.py
            language="en",
            task="transcribe",
            enable_diarization=True,
            min_speakers=1,
            max_speakers=3
        )
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("✅ TRANSCRIPTION COMPLETED")
        print("=" * 70)
        
        # Performance Metrics
        if 'performance' in result:
            perf = result['performance']
            whisper_time = perf.get('whisper_time', 0)
            diarization_time = perf.get('diarization_time', 0)
            audio_duration = perf.get('audio_duration', 0)
            
            print(f"\n📊 Performance Metrics:")
            print(f"   - Audio Duration: {audio_duration:.1f}s ({audio_duration/60:.1f}min)")
            print(f"   - Whisper Time: {whisper_time:.1f}s")
            print(f"   - Diarization Time: {diarization_time:.1f}s")
            print(f"   - Total Time: {elapsed:.1f}s")
            print(f"   - Ratio: {elapsed/audio_duration:.2f}x")
            
            # Target Analysis
            print(f"\n🎯 Target Analysis:")
            print(f"   - Current Ratio: {elapsed/audio_duration:.2f}x")
            print(f"   - Target Ratio: 0.20x (5min → 60s)")
            
            if elapsed/audio_duration <= 0.20:
                print(f"   ✅ TARGET MET! Performance is excellent!")
            elif elapsed/audio_duration <= 0.25:
                print(f"   ⚠️ Close to target (within 25%)")
                improvement_needed = ((elapsed/audio_duration) - 0.20) / 0.20 * 100
                print(f"   - Need {improvement_needed:.1f}% improvement")
            else:
                print(f"   ❌ Below target")
                improvement_needed = ((elapsed/audio_duration) - 0.20) / 0.20 * 100
                print(f"   - Need {improvement_needed:.1f}% improvement")
        
        # Transcription Results
        print(f"\n📝 Transcription Results:")
        print(f"   - Language: {result.get('language', 'unknown')}")
        print(f"   - Text Length: {len(result.get('text', ''))} chars")
        print(f"   - Segments: {len(result.get('segments', []))}")
        
        if 'speakers' in result and result['speakers']:
            print(f"   - Speaker Count: {result.get('speaker_count', 0)}")
        
        # Show first 200 chars of transcription
        text = result.get('text', '')
        if text:
            print(f"\n📄 Transcription Preview (first 200 chars):")
            print(f"   \"{text[:200]}...\"")
        
        print("\n" + "=" * 70)
        print("🎉 PYANNOTE REVERSION TEST SUCCESSFUL!")
        print("=" * 70)
        
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

if __name__ == "__main__":
    test_pyannote_reversion()
