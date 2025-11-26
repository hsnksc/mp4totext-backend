"""
Test audio processor (Whisper + Speaker Recognition)
"""

import sys
import os

# Add backend to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.audio_processor import get_audio_processor
from app.settings import Settings

def test_audio_processor():
    """Test audio processing pipeline"""
    
    print("=" * 60)
    print("  🎵 Audio Processor Test")
    print("=" * 60)
    print()
    
    # Load settings
    settings = Settings()
    
    print("📋 Configuration:")
    print(f"  - Whisper Model: {settings.WHISPER_MODEL_SIZE}")
    print(f"  - Speaker Model: {settings.GLOBAL_MODEL_PATH}")
    print(f"  - Speaker Mapping: {settings.GLOBAL_MAPPING_PATH}")
    print(f"  - Threshold: {settings.GLOBAL_MODEL_THRESHOLD}")
    print()
    
    # Initialize processor
    print("🔧 Initializing audio processor...")
    processor = get_audio_processor(
        whisper_model_size=settings.WHISPER_MODEL_SIZE,
        speaker_model_path=settings.GLOBAL_MODEL_PATH,
        speaker_mapping_path=settings.GLOBAL_MAPPING_PATH,
        speaker_threshold=settings.GLOBAL_MODEL_THRESHOLD
    )
    
    print(f"✅ Audio processor initialized")
    print(f"   - Speaker recognition available: {processor.speaker_enabled}")
    print()
    
    # Check if we have a test audio file
    test_audio = input("📁 Enter path to audio/video file (or press Enter to skip): ").strip()
    
    if test_audio and os.path.exists(test_audio):
        print()
        print(f"🎬 Processing: {test_audio}")
        print("-" * 60)
        
        try:
            result = processor.process_file(test_audio, language=None)
            
            print()
            print("✅ Processing Complete!")
            print("=" * 60)
            print(f"📝 Transcription ({len(result['text'])} chars):")
            print("-" * 60)
            print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
            print()
            print(f"🌍 Language: {result['language']}")
            print(f"👥 Speakers: {result['speaker_count']}")
            if result['speakers']:
                print(f"   Names: {', '.join(result['speakers'])}")
            print()
            print(f"📊 Segments: {len(result['segments'])}")
            
            if result['segments']:
                print()
                print("🔍 First 3 segments:")
                print("-" * 60)
                for i, seg in enumerate(result['segments'][:3], 1):
                    print(f"{i}. [{seg['start']:.2f}s - {seg['end']:.2f}s]")
                    print(f"   Speaker: {seg.get('speaker', 'N/A')} "
                          f"(confidence: {seg.get('speaker_confidence', 0):.2f})")
                    print(f"   Text: {seg['text']}")
                    print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("ℹ️  No audio file provided. Test skipped.")
    
    print()
    print("=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_audio_processor()
