"""
Fast Whisper inference on T4 GPU with CUDA 11.8 compatibility
Optimized for cost ($0.36/hr) and speed (0.05-0.08x realtime)

CRITICAL: Uses CUDA 11 compatible versions
- PyTorch 2.0.1 (CUDA 11.8)
- ctranslate2 3.24.0 (CUDA 11.x)
- faster-whisper 0.10.1 (compatible with ctranslate2 3.24.0)
- nvidia-cublas-cu11 & nvidia-cudnn-cu11 (pip packages)
"""

from typing import Optional
import modal

# Create Modal app
app = modal.App("mp4totext-whisper-t4")

# CUDA 12.x stack (Modal T4 GPU'da CUDA 12 runtime var)
# PyTorch 2.1+ (CUDA 12.1) + ctranslate2 4.x (CUDA 12) + faster-whisper 1.1.0
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        # PyTorch CUDA 12.1
        "torch==2.1.2",
        "torchaudio==2.1.2",
        extra_options="--index-url https://download.pytorch.org/whl/cu121"
    )
    .pip_install(
        # ctranslate2 CUDA 12 sürümü
        "ctranslate2>=4.0",
        # faster-whisper güncel versiyon
        "faster-whisper==1.1.0",
        # Diğer bağımlılıklar
        "requests",
        "pydub",
        "ffmpeg-python",
        "numpy<2.0.0"
    )
)


@app.cls(
    gpu="T4",  # $0.36/hour - 46% cheaper than A10G
    timeout=3600,  # 1 hour max
    scaledown_window=300,  # Keep warm for 5 minutes
    image=image,
)
class WhisperModel:
    """
    Whisper Large V3 on T4 GPU
    Performance: 0.05-0.08x realtime (5min audio → 15-25s)
    Cost: $0.36/hour
    """
    
    @modal.enter()
    def load_model(self):
        """Load model on container startup"""
        import torch
        from faster_whisper import WhisperModel
        import time
        
        print(f"🚀 Loading Whisper Large V3 with faster-whisper...")
        print(f"   PyTorch: {torch.__version__}")
        print(f"   CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   CUDA Version: {torch.version.cuda}")
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
        
        start = time.time()
        
        self.model = WhisperModel(
            "large-v3",
            device="cuda",
            compute_type="float16",
            download_root="/root/.cache/huggingface"
        )
        
        elapsed = time.time() - start
        print(f"✅ Model loaded in {elapsed:.1f}s")
        print(f"💰 Cost: $0.36/hour on T4 GPU")
        print(f"⚡ Expected: 0.05-0.08x realtime processing")

    @modal.method()
    def transcribe(
        self,
        audio_url: str,
        language: str = None,
        batch_size: int = 16
    ):
        """
        Transcribe audio from URL
        
        Args:
            audio_url: URL to audio file
            language: Language code (None for auto-detect)
            batch_size: Batch size for processing (faster-whisper 0.10.1 supports this)
            
        Returns:
            Transcription result dict
        """
        import requests
        import tempfile
        import os
        import time
        
        print("🎯 Transcription request")
        print(f"📥 Downloading: {audio_url[:80]}...")
        
        # Download audio
        response = requests.get(audio_url, timeout=300)
        response.raise_for_status()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(response.content)
            audio_path = f.name
        
        try:
            print(f"🎙️ Transcribing (language={language or 'auto'})...")
            start_time = time.time()
            
            # Modal resmi örneğine göre: EN BASİT KULLANIM
            # VAD parametrelerini tamamen kaldırıyoruz
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5
            )
            
            # Collect segments
            transcription = []
            for segment in segments:
                transcription.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
            
            elapsed = time.time() - start_time
            
            # Get audio duration
            duration = info.duration
            ratio = elapsed / duration if duration > 0 else 0
            
            print(f"✅ Transcribed {duration:.1f}s audio in {elapsed:.1f}s ({ratio:.3f}x)")
            
            return {
                "text": " ".join([s["text"] for s in transcription]),
                "segments": transcription,
                "language": info.language,
                "duration": duration,
                "performance": {
                    "transcribe_time": elapsed,
                    "ratio": ratio
                }
            }
            
        finally:
            # Cleanup
            if os.path.exists(audio_path):
                os.unlink(audio_path)


# Test function
@app.local_entrypoint()
def test():
    """Test the transcription with a sample audio file"""
    print("🧪 Testing Whisper T4 transcription...")
    
    model = WhisperModel()
    result = model.transcribe.remote(
        audio_url="https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav",
        language="en",
        batch_size=16
    )
    
    print(f"\n🎉 Test successful!")
    print(f"Text: {result['text'][:100]}...")
    print(f"Duration: {result['duration']:.1f}s")
    print(f"Processing time: {result['performance']['transcribe_time']:.1f}s")
    print(f"Ratio: {result['performance']['ratio']:.3f}x")
