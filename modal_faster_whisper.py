"""
Modal Faster Whisper - STABLE VERSION
cuDNN sorunları yok, 4x daha hızlı, daha az memory
"""

import modal

app = modal.App("mp4totext-faster-whisper")

# Faster Whisper image - GPU kütüphaneleri otomatik
faster_whisper_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "faster-whisper",
        "requests",
    )
)


@app.cls(
    gpu="T4",
    image=faster_whisper_image,
    scaledown_window=300,
    timeout=600,
)
class FasterWhisperTranscriber:
    """Faster Whisper transcriber - GPU optimized"""
    
    @modal.enter()
    def load_model(self):
        """Model yükle - container başlangıcında (otomatik download)"""
        from faster_whisper import WhisperModel
        print("🚀 Loading Faster Whisper Large V3...")
        self.model = WhisperModel(
            "large-v3",
            device="cuda",
            compute_type="float16"
        )
        print("✅ Model loaded on GPU")
    
    @modal.method()
    def transcribe(self, audio_url: str, language: str = None):
        """
        Transcribe audio
        
        Args:
            audio_url: Audio dosyasının URL'si
            language: Dil kodu (None = auto-detect)
        
        Returns:
            Dict: transcription, segments, duration, language
        """
        import requests
        import tempfile
        import time
        
        print(f"📥 Downloading audio: {audio_url[:80]}...")
        
        # Audio'yu indir
        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()
        
        # Temp file'a kaydet
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        print(f"🎙️ Transcribing (language={language or 'auto'})...")
        start_time = time.time()
        
        # Transcribe - BASIT
        segments, info = self.model.transcribe(
            tmp_path,
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
        
        print(f"✅ Completed in {elapsed:.1f}s")
        print(f"📊 Language: {info.language}, Segments: {len(transcription)}")
        
        return result


@app.local_entrypoint()
def test():
    """Test fonksiyonu"""
    transcriber = FasterWhisperTranscriber()
    result = transcriber.transcribe.remote(
        audio_url="https://upload.wikimedia.org/wikipedia/commons/4/46/1941_Roosevelt_speech_pearlharbor_p1.ogg"
    )
    print(f"\n📝 Transcription:\n{result['text'][:200]}...")
    print(f"\n✅ Test successful!")
