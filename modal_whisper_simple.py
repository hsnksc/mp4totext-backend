"""
Modal Whisper Transcription - SIMPLE VERSION
Modal'ın resmi örneğine göre en basit çalışan versiyon
"""

import modal
import requests
import tempfile
import time

# Modal image: Python 3.11 + PyTorch CUDA 12.1 + faster-whisper
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "torch==2.1.2",
        "torchaudio==2.1.2",
        extra_options="--index-url https://download.pytorch.org/whl/cu121"
    )
    .pip_install(
        "faster-whisper>=1.0.0",
        "requests",
        "numpy<2.0.0"
    )
)

app = modal.App("mp4totext-whisper-simple", image=image)


@app.cls(
    gpu="T4",
    container_idle_timeout=300,
    timeout=600
)
class WhisperTranscriber:
    """Basit Whisper transcription sınıfı"""
    
    @modal.enter()
    def load_model(self):
        """Model yükleme - container başlangıcında bir kez çalışır"""
        print("🚀 Loading Whisper Large V3...")
        from faster_whisper import WhisperModel
        
        self.model = WhisperModel(
            "large-v3",
            device="cuda",
            compute_type="float16"
        )
        print("✅ Model loaded successfully")
    
    @modal.method()
    def transcribe(self, audio_url: str, language: str = None):
        """
        Audio transkripsiyonu
        
        Args:
            audio_url: Audio dosyasının URL'si
            language: Dil kodu (None = auto-detect)
        
        Returns:
            Dict: transcription, segments, duration, language
        """
        print(f"📥 Downloading audio: {audio_url[:80]}...")
        
        # Download audio
        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(response.content)
            audio_path = f.name
        
        print(f"🎙️ Transcribing...")
        start_time = time.time()
        
        # SIMPLE TRANSCRIPTION - Modal örneğindeki gibi
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5
        )
        
        # Collect segments
        transcription = []
        full_text = []
        
        for segment in segments:
            transcription.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
            full_text.append(segment.text)
        
        elapsed = time.time() - start_time
        
        result = {
            "transcription": transcription,
            "text": " ".join(full_text),
            "language": info.language,
            "duration": info.duration,
            "segments_count": len(transcription),
            "processing_time": elapsed
        }
        
        print(f"✅ Transcription completed in {elapsed:.1f}s")
        print(f"📊 Language: {info.language}, Duration: {info.duration:.1f}s")
        print(f"📝 Segments: {len(transcription)}")
        
        return result


@app.function()
def test_transcription():
    """Test fonksiyonu"""
    transcriber = WhisperTranscriber()
    result = transcriber.transcribe.remote(
        audio_url="https://upload.wikimedia.org/wikipedia/commons/4/46/1941_Roosevelt_speech_pearlharbor_p1.ogg"
    )
    print("Test result:", result["text"][:100])
    return result
