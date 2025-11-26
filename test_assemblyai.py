"""
AssemblyAI Service Test
Tests AssemblyAI transcription with speaker diarization
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.assemblyai_service import get_assemblyai_service
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_assemblyai():
    """Test AssemblyAI service"""
    print("\n" + "="*80)
    print("🧪 ASSEMBLYAI SERVICE TEST")
    print("="*80)
    
    # Get service
    service = get_assemblyai_service()
    
    # Health check
    print("\n1️⃣  Health Check...")
    health = service.health_check()
    print(f"   Status: {health.get('status')}")
    if health.get('features'):
        print(f"   Features: {health['features']}")
    
    if not service.is_enabled():
        print("\n❌ AssemblyAI service not enabled (check ASSEMBLYAI_API_KEY)")
        return
    
    # Test with public audio file
    print("\n2️⃣  Testing Transcription...")
    test_url = "https://assembly.ai/sports_injuries.mp3"
    
    print(f"   Audio URL: {test_url}")
    print(f"   Diarization: Enabled")
    
    try:
        result = service.transcribe_audio(
            audio_url=test_url,
            enable_diarization=True
        )
        
        print("\n✅ Transcription completed!")
        print(f"   Text length: {len(result['text'])} chars")
        print(f"   Language: {result['language']}")
        print(f"   Duration: {result['duration']:.1f}s")
        print(f"   Processing time: {result['processing_time']:.1f}s")
        print(f"   Segments: {result['segments_count']}")
        print(f"   Utterances: {len(result['utterances'])}")
        print(f"   Speakers detected: {result['speaker_count']}")
        
        if result['speakers']:
            print(f"   Speaker labels: {', '.join(result['speakers'])}")
        
        # Show first few utterances
        if result['utterances']:
            print("\n📝 Sample Utterances:")
            for i, utt in enumerate(result['utterances'][:3], 1):
                print(f"   {i}. Speaker {utt['speaker']}: {utt['text'][:80]}...")
        
        # Show text preview
        print(f"\n📄 Transcript Preview:")
        print(f"   {result['text'][:200]}...")
        
        print("\n🎉 AssemblyAI TEST SUCCESSFUL!")
        return True
        
    except Exception as e:
        print(f"\n❌ Transcription failed: {e}")
        return False

if __name__ == "__main__":
    test_assemblyai()
