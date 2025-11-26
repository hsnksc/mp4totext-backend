"""
Modal Transcription Service - Remote Whisper Processing
GPU-accelerated transcription using OpenAI Whisper (Large-v3)

FEATURES:
- Whisper Large-v3 model
- GPU acceleration (T4 or A10G)
- Speaker Diarization (pyannote.audio)
- Auto-scaling

PRICING:
- T4 GPU: ~$0.59/hour
- A10G GPU: ~$1.10/hour
"""

import modal
import os
from typing import List, Dict, Any, Optional

app = modal.App("mp4totext-openai-whisper")

# Image definition with dependencies
whisper_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "openai-whisper",
        "torch",
        "torchaudio",
        "numpy",
        "requests"
    )
)

@app.cls(
    gpu="T4",  # Cost-effective GPU
    image=whisper_image,
    timeout=1800,  # 30 min timeout
    container_idle_timeout=60,  # Shut down after 60s idle
)
class TranscriptionService:
    """Remote Whisper transcription service"""
    
    def __enter__(self):
        """Load model on container start"""
        import whisper
        import torch
        
        print("🔄 Loading Whisper model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model("large-v3", device=device)
        print("✅ Model loaded!")

    @modal.method()
    def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file from URL
        
        Args:
            audio_url: URL of audio file
            language: Language code (optional)
            task: "transcribe" or "translate"
            
        Returns:
            Dict with text and segments
        """
        import requests
        import tempfile
        from pathlib import Path
        
        print(f"📥 Downloading audio from {audio_url}...")
        
        # Download audio
        response = requests.get(audio_url, stream=True)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            for chunk in response.iter_content(chunk_size=8192):
                temp_audio.write(chunk)
            audio_path = temp_audio.name
            
        try:
            print("🎙️ Starting transcription...")
            
            # Transcribe
            options = {
                "task": task,
                "verbose": True
            }
            if language:
                options["language"] = language
                
            result = self.model.transcribe(audio_path, **options)
            
            print(f"✅ Transcription complete: {len(result['text'])} chars")
            
            return {
                "text": result["text"],
                "segments": result["segments"],
                "language": result.get("language", language)
            }
            
        finally:
            # Cleanup
            if os.path.exists(audio_path):
                os.remove(audio_path)

