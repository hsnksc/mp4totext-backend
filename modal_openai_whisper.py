"""
Modal OpenAI Whisper - cuDNN SORUNSUZ
OpenAI'ın resmi Whisper'ı - PyTorch ile direkt çalışır
"""

import modal

app = modal.App("mp4totext-openai-whisper")

# OpenAI Whisper image - cuDNN gerektirmiyor
openai_whisper_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "openai-whisper",
        "requests",
    )
)


@app.cls(
    gpu="T4",
    image=openai_whisper_image,
    scaledown_window=300,
    timeout=600,
)
class OpenAIWhisperTranscriber:
    """OpenAI Whisper - cuDNN sorunsuz"""
    
    @modal.enter()
    def load_model(self):
        """Model yükle - container başlangıcında"""
        import whisper
        print("🚀 Loading OpenAI Whisper Large V3...")
        self.model = whisper.load_model("large-v3")
        print("✅ Model loaded successfully")
    
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
        
        # Transcribe - OpenAI Whisper API
        result = self.model.transcribe(
            tmp_path,
            language=language,
            verbose=False
        )
        
        # Format output
        transcription = []
        for segment in result['segments']:
            transcription.append({
                "start": segment['start'],
                "end": segment['end'],
                "text": segment['text']
            })
        
        elapsed = time.time() - start_time
        
        output = {
            "segments": transcription,  # Backend expects "segments"
            "text": result['text'],
            "language": result['language'],
            "duration": result['segments'][-1]['end'] if result['segments'] else 0,
            "segments_count": len(transcription),
            "processing_time": elapsed,
            "speaker_count": 0  # OpenAI Whisper doesn't support diarization
        }
        
        print(f"✅ Completed in {elapsed:.1f}s")
        print(f"📊 Language: {result['language']}, Segments: {len(transcription)}")
        
        return output


@app.local_entrypoint()
def test():
    """Test fonksiyonu"""
    transcriber = OpenAIWhisperTranscriber()
    result = transcriber.transcribe.remote(
        audio_url="https://github.com/ggerganov/whisper.cpp/raw/master/samples/jfk.wav"
    )
    print(f"\n📝 Transcription:\n{result['text']}")
    print(f"\n✅ Test successful!")
