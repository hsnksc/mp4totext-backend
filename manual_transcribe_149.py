"""
Manual transcription test for ID 149
"""
import os
from app.services.audio_processor import get_audio_processor

audio_processor = get_audio_processor()

file_path = r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend\uploads\633daf1b-e9f4-4fc5-8f97-ee478fd944da.mp3"

if not os.path.exists(file_path):
    print(f"❌ File not found: {file_path}")
    exit(1)

print(f"✅ File exists: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB")
print(f"\n🎙️ Starting Whisper transcription (base model)...")

try:
    result = audio_processor.transcribe(
        file_path=file_path,
        model_name="base",
        language=None  # Auto-detect
    )
    
    print(f"\n✅ Transcription complete!")
    print(f"   Text length: {len(result.get('text', ''))} chars")
    print(f"   Duration: {result.get('duration', 0):.2f}s")
    print(f"   Segments: {len(result.get('segments', []))}")
    print(f"\n📝 First 500 chars:")
    print(result.get('text', '')[:500])
    
except Exception as e:
    print(f"\n❌ Transcription failed: {e}")
    import traceback
    traceback.print_exc()
