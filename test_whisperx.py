#!/usr/bin/env python3
"""Test WhisperX Modal deployment"""

import modal

# Get the WhisperXModel class using from_name (correct Modal SDK method)
WhisperXModel = modal.Cls.from_name("mp4totext-whisperx", "WhisperXModel")

print("🎬 Test başlatılıyor...")
print("📹 Video: YouTube test (18 saniye)")
print("⏱️  Beklenen süre: ~20-30 saniye")
print()

try:
    # Test with short YouTube video
    result = WhisperXModel().transcribe.remote(
        audio_url="https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo - 18 seconds
        language=None,  # Auto-detect
        enable_diarization=True,
        min_speakers=1,
        max_speakers=2,
        batch_size=16
    )
    
    print()
    print("✅ SUCCESS! cuDNN sorunu çözüldü!")
    print()
    print("📊 Sonuç:")
    print(f"  - Segments: {len(result.get('segments', []))}")
    print(f"  - Language: {result.get('language', 'N/A')}")
    
    if result.get('segments'):
        print(f"  - First segment: {result['segments'][0].get('text', '')[:50]}...")
    
except Exception as e:
    print()
    print(f"❌ HATA: {e}")
    print()
    if 'cudnn' in str(e).lower():
        print("🔴 cuDNN hatası devam ediyor!")
        print("🔧 Alternatif çözümler denenmeli:")
        print("   1. LD_LIBRARY_PATH ayarı")
        print("   2. Farklı CUDA base image")
        print("   3. Modal support")
    raise
