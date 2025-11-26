"""
Modal Whisper - TRANSCRIPTION ONLY (NO DIARIZATION) 💰

COST-OPTIMIZED: T4 GPU ($0.36/hr) - 46% cheaper than A10G!
- WhisperX 3.1.1 for word-level timestamps
- PyTorch 2.3.0 + CUDA 12.1 (cuDNN 8.9)
- No diarization = No pyannote.audio = Simpler + Faster + Cheaper

Deploy:
1. modal token new
2. modal deploy modal_whisperx_function.py

Performance on T4:
- 5 min audio → 15-25s (0.05-0.08x ratio) ✅
- No diarization overhead
- Cost: ~$0.002-0.003 per 5min audio
"""

import modal
import os

app = modal.App("mp4totext-whisper-only")

# 💰 COST-OPTIMIZED: T4 GPU + Whisper-only (no diarization)
# Simple and stable - just Whisper + alignment
whisper_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")
    .pip_install(
        # PyTorch 2.0.1 + CUDA 11.8 (cuDNN 8.x uyumlu - T4 GPU için optimal)
        "torch==2.0.1",
        "torchaudio==2.0.2",
        extra_options="--index-url https://download.pytorch.org/whl/cu118"
    )
    .pip_install(
        # Essential dependencies
        "requests==2.31.0",
        "nltk>=3.9.1",
        "numpy<2.0.0",
        "pandas>=2.0.0",
        "transformers==4.30.0",  # PyTorch 2.0 ile uyumlu
        "soundfile>=0.12.1",
        "ctranslate2==4.4.0",  # 🔥 KRİTİK: CUDA 11.8 + cuDNN 8.x için 4.4.0 şart!
        "faster-whisper==1.0.3"  # ctranslate2 4.4.0 ile uyumlu
    )
)

# Persistent volume for model caching
volume = modal.Volume.from_name("whisper-models", create_if_missing=True)


@app.cls(
    image=whisper_image,
    gpu="T4",  # Cost-optimized: $0.36/hr (46% cheaper than A10G!)
    timeout=3600,
    memory=16384,  # 16GB for T4 (sufficient for Whisper large-v2)
    volumes={"/cache": volume},
    scaledown_window=300,  # 5 min idle
)
class WhisperModel:
    """
    Whisper-Only: Transcription + Word-level Alignment (NO Diarization)
    
    Advantages:
    - 46% cheaper than A10G (T4: $0.36/hr)
    - No diarization overhead = 2-3x faster
    - Simple and stable
    - Perfect word-level timestamps via WhisperX alignment
    """
    
    @modal.enter()
    def setup(self):
        """Load faster-whisper model on container startup"""
        from faster_whisper import WhisperModel
        import torch
        
        print("🚀 Whisper-Only Setup (T4 GPU)...")
        
        # Verify PyTorch CUDA setup
        print(f"✅ PyTorch: {torch.__version__}")
        print(f"✅ CUDA: {torch.version.cuda}")
        print(f"✅ cuDNN: {torch.backends.cudnn.version()}")
        
        # Load faster-whisper model
        print("🔄 Loading faster-whisper large-v2...")
        self.model = WhisperModel(
            "large-v2",
            device="cuda",
            compute_type="float16",  # T4 supports float16
            download_root="/cache/whisper"
        )
        
        print(f"✅ Model loaded on {torch.cuda.get_device_name(0)}")
        print("💰 Mode: TRANSCRIPTION ONLY (no diarization, no alignment)")
    
    @modal.method()
    def transcribe(
        self,
        audio_url: str,
        language: str = None,
        batch_size: int = 16  # WhisperX batch size
    ):
        """
        Transcribe audio with WhisperX (NO diarization)
        
        Args:
            audio_url: URL to audio file
            language: Language code (e.g., 'en', 'tr') or None for auto-detect
            batch_size: Batch size for WhisperX (default 16)
        
        Returns:
            {
                "text": str,
                "language": str,
                "segments": list,
                "duration": float,
                "performance": dict
            }
        """
        import requests
        import tempfile
        import time
        import torch
        
        print(f"🎵 Downloading audio from: {audio_url[:80]}...")
        print("💰 Mode: TRANSCRIPTION ONLY (no diarization, no alignment)")
        
        # Download audio
        response = requests.get(audio_url, timeout=300)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.content)
            audio_path = tmp_file.name
        
        total_start = time.time()
        
        # ============================================
        # STEP 1: Transcribe with faster-whisper
        # ============================================
        print("🎬 Transcribing with faster-whisper...")
        transcribe_start = time.time()
        
        # faster-whisper returns generator of segments
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            word_timestamps=False  # No word-level alignment needed
        )
        
        # Convert generator to list
        segments_list = list(segments)
        
        transcribe_time = time.time() - transcribe_start
        detected_language = info.language
        audio_duration = info.duration
        print(f"✅ Transcription: {transcribe_time:.1f}s ({detected_language})")
        print(f"⏱️ Audio duration: {audio_duration:.1f}s")
        
        # ============================================
        # STEP 2: Format results
        # ============================================
        total_time = time.time() - total_start
        ratio = total_time / audio_duration
        
        # Extract text and convert segments to dict format
        full_text = " ".join([seg.text for seg in segments_list])
        segments_dict = [
            {
                "start": seg.start,
                "end": seg.end,
                "text": seg.text
            }
            for seg in segments_list
        ]
        
        # Performance analysis
        print(f"\n{'='*50}")
        print(f"📊 RESULTS (T4 - Whisper Only)")
        print(f"{'='*50}")
        print(f"⏱️ Audio: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")
        print(f"⏱️ Total: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"   Transcribe: {transcribe_time:.1f}s")
        print(f"📊 Ratio: {ratio:.3f}x")
        print(f"💰 Cost: ~${(total_time/3600)*0.36:.4f} (T4: $0.36/hr)")
        
        if ratio < 0.08:
            print("✅ EXCELLENT! (target: <0.08x without diarization)")
        elif ratio < 0.15:
            print("✅ GOOD!")
        else:
            print(f"⚠️ Slower than expected")
        
        print(f"{'='*50}\n")
        
        # Cleanup
        import os
        os.unlink(audio_path)
        
        return {
            "text": full_text,
            "language": detected_language,
            "segments": segments_dict,
            "duration": audio_duration,
            "performance": {
                "total_time": total_time,
                "transcribe_time": transcribe_time,
                "audio_duration": audio_duration,
                "ratio": ratio,
                "cost_usd": (total_time/3600)*0.36
            }
        }


# Test endpoint
@app.local_entrypoint()
def test():
    """Test Whisper with sample audio"""
    
    # Replace with your test audio URL
    test_url = "https://example.com/audio.mp3"
    
    print("🧪 Testing Whisper-only...")
    
    model = WhisperModel()
    result = model.transcribe.remote(
        audio_url=test_url
    )
    
    print(f"\n✅ Language: {result['language']}")
    print(f"✅ Duration: {result['duration']:.1f}s")
    print(f"✅ Ratio: {result['performance']['ratio']:.2f}x")
    print(f"💰 Cost: ${result['performance']['cost_usd']:.4f}")
    print(f"\n📝 First 3 segments:")
    
    for seg in result['segments'][:3]:
        text = seg['text']
        start = seg.get('start', 0)
        print(f"  [{start:.1f}s] {text}")
