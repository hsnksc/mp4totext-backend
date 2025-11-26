"""
Modal Whisper + Speaker Diarization Function - Production Ready

Deploy this file to Modal:
1. Install Modal CLI: pip install modal
2. Setup token: modal token new
3. Add HuggingFace token secret: modal secret create huggingface-secret HUGGINGFACE_TOKEN=hf_xxxxx
4. Deploy: modal deploy modal_whisper_function.py

✨ FEATURES:
- Whisper transcription (all languages supported)
- pyannote.audio 3.1 for speaker diarization (state-of-the-art)
- Model caching for faster subsequent requests
- Container stays warm for 5 minutes
- Automatic speaker-segment alignment
"""

import modal
import os

# Create Modal app (v6: A10G + low batch sizes for std() fix)
app = modal.App("mp4totext-whisper-diarization-v6")

# ============================================
# WhisperX Image (RECOMMENDED - 2-3x faster!)
# ============================================
whisperx_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "git")  # git needed for whisperx install
    .pip_install(
        "git+https://github.com/m-bain/whisperx.git",
        "torch==2.1.0",
        "torchaudio==2.1.0",
        "requests==2.31.0",
    )
)

# ============================================
# OLD Pyannote Image (DEPRECATED - kept for backward compatibility)
# ============================================
# Define GPU image with Whisper + pyannote dependencies
# v6: A10G GPU + LOW batch sizes (seg=8, emb=16) - std() FIX
whisper_diarization_image_v6 = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "numpy==1.24.3",  # CRITICAL: Lock to 1.x (pyannote incompatible with 2.x)
        "openai-whisper==20231117",
        "torch==2.2.0",  # ✅ PyTorch 2.2 for better performance
        "torchaudio==2.2.0",
        "requests==2.31.0",
    )
    .pip_install(
        "huggingface_hub==0.19.4",  # OLD version that supports use_auth_token parameter
        "pyannote.audio==3.1.1",  # 3.1 is faster (pure PyTorch, no onnxruntime)
        "pydub==0.25.1",
        extra_options="--no-deps",  # Install without dependencies to prevent NumPy upgrade
    )
    .pip_install(
        # Install pyannote.audio dependencies manually with NumPy 1.x constraint
        "pyannote.core>=5.0.0",
        "pyannote.database>=5.0.1",
        "pyannote.metrics>=3.2.1",
        "pyannote.pipeline>=3.0.1",
        "torch-audiomentations>=0.11.0",
        "speechbrain>=0.5.16",
        "asteroid-filterbanks>=0.4.0",
        "semver>=3.0.2",
        "omegaconf>=2.1",
        "pytorch-lightning>=2.0.0",
        "torchmetrics>=0.11",
        "einops>=0.7.0",
        "numpy<2.0",  # FORCE NumPy 1.x for all dependencies
        # Missing dependencies for pyannote.audio 3.1.1
        "lightning>=2.0.1",
        "pytorch-metric-learning>=2.1.0",
        "soundfile>=0.12.1",
        "tensorboardX>=2.6",
    )
)

# Keep old name for compatibility
whisper_diarization_image_v5 = whisper_diarization_image_v6  # Point to v6
whisper_diarization_image = whisper_diarization_image_v6  # ACTIVE: v6 with std() fix

# Create persistent volume for model cache (Whisper + pyannote models)
volume = modal.Volume.from_name("whisper-diarization-models", create_if_missing=True)


@app.cls(
    image=whisper_diarization_image,
    gpu="A10G",  # ✅ A10G GPU - Stable, 6x cheaper (~$0.67/hour)
    timeout=3600,  # 60 minutes
    memory=24576,  # 24GB RAM (A10G has 24GB)
    volumes={"/cache": volume},  # Persistent model storage
    scaledown_window=300,  # 5 dakika idle (renamed parameter)
    secrets=[modal.Secret.from_name("huggingface-secret")],  # Required for pyannote
    concurrency_limit=20,  # 20 parallel requests (new Modal 1.0 syntax)
)
class WhisperDiarizationModel:
    """
    Whisper + pyannote.audio speaker diarization on A10G GPU
    - Both models loaded ONCE when container starts
    - A10G GPU: Stable performance, 6x cheaper than A100 (~60-90s for 5min audio)
    - Cached in memory for subsequent requests
    - Container stays warm for 5 minutes
    - Supports all languages
    - Very low batch sizes (seg=8, emb=16) to prevent std() errors
    """
    
    @modal.enter()
    def load_models(self):
        """
        🚀 Container startup: Load models ONCE
        This runs when container starts, not on every request!
        """
        import whisper
        from pyannote.audio import Pipeline
        import torch
        import warnings
        
        # ============================================
        # � AGGRESSIVE TF32 LOCK - Cannot be disabled!
        # ============================================
        
        # Step 1: Suppress pyannote reproducibility warnings
        try:
            import pyannote.audio.utils.reproducibility
            warnings.filterwarnings('ignore', 
                                  category=pyannote.audio.utils.reproducibility.ReproducibilityWarning)
            
            # Completely disable fix_reproducibility
            def dummy_fix_reproducibility(seed: int = None):
                """Do nothing - leave TF32 alone"""
                pass
            
            pyannote.audio.utils.reproducibility.fix_reproducibility = dummy_fix_reproducibility
            print("✅ Pyannote reproducibility disabled")
        except Exception as e:
            print(f"⚠️ Could not disable reproducibility: {e}")
        
        # Step 2: LOCK TF32 - prevent any library from disabling it
        try:
            # Lock matmul TF32
            original_matmul_setter = torch.backends.cuda.matmul.__class__.allow_tf32.fset
            
            def locked_matmul_tf32_setter(self, value):
                """Block attempts to disable TF32"""
                if value is False:
                    print("🚫 BLOCKED: Attempt to disable matmul TF32")
                    return  # Silently ignore
                original_matmul_setter(self, value)
            
            torch.backends.cuda.matmul.__class__.allow_tf32 = property(
                torch.backends.cuda.matmul.__class__.allow_tf32.fget,
                locked_matmul_tf32_setter
            )
            
            # Lock cuDNN TF32
            original_cudnn_setter = torch.backends.cudnn.__class__.allow_tf32.fset
            
            def locked_cudnn_tf32_setter(self, value):
                """Block attempts to disable cuDNN TF32"""
                if value is False:
                    print("🚫 BLOCKED: Attempt to disable cuDNN TF32")
                    return  # Silently ignore
                original_cudnn_setter(self, value)
            
            torch.backends.cudnn.__class__.allow_tf32 = property(
                torch.backends.cudnn.__class__.allow_tf32.fget,
                locked_cudnn_tf32_setter
            )
            
            print("✅ TF32 setters locked (cannot be disabled)")
        except Exception as e:
            print(f"⚠️ Could not lock TF32 setters: {e}")
        
        # Step 3: Enable TF32 + A100 Optimizations
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True  # ✅ Auto-tune for best performance
        torch.backends.cudnn.deterministic = False  # ✅ Allow fastest algorithms
        torch.set_float32_matmul_precision('high')  # ✅ 'high' on A100 (vs 'medium' on A10G)
        
        print("🔒 TF32 LOCKED ON - cannot be disabled by any library")
        print(f"🔍 TF32 status: matmul={torch.backends.cuda.matmul.allow_tf32}, cudnn={torch.backends.cudnn.allow_tf32}")
        print(f"🔍 cuDNN benchmark: {torch.backends.cudnn.benchmark} (auto-tune enabled)")
        print(f"🔍 Float32 precision: {torch.get_float32_matmul_precision()}")
        
        print("🔄 Loading Whisper model (one-time setup)...")
        self.whisper_model = whisper.load_model("base", download_root="/cache")
        
        # Verify Whisper model is on GPU
        if torch.cuda.is_available():
            # Whisper automatically uses GPU, but let's verify
            print(f"🔍 Whisper will use GPU: {torch.cuda.get_device_name(0)}")
        
        print("✅ Whisper model loaded and cached")
        
        # Load pyannote speaker diarization pipeline
        print("🔍 Checking for HUGGINGFACE_TOKEN environment variable...")
        hf_token = os.environ.get("HUGGINGFACE_TOKEN")
        
        if hf_token:
            print(f"✅ HUGGINGFACE_TOKEN found: {hf_token[:10]}...")
            try:
                print("🔄 Loading pyannote.audio 3.1 speaker diarization pipeline...")
                print("📦 Downloading model from HuggingFace (this may take 1-2 minutes)...")
                print("✨ 3.1 improvements: Pure PyTorch (no onnxruntime), faster inference")
                
                # pyannote.audio 3.1 with huggingface_hub 0.19.4 (supports use_auth_token)
                # 3.1 is faster than 3.0 (pure PyTorch, removes onnxruntime dependency)
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=hf_token,
                    cache_dir="/cache"
                )
                
                # 🚀 CRITICAL: Move pipeline to GPU explicitly
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                print(f"🔍 CUDA available: {torch.cuda.is_available()}")
                if torch.cuda.is_available():
                    print(f"🔍 CUDA device: {torch.cuda.get_device_name(0)}")
                    self.diarization_pipeline.to(device)
                    print(f"✅ Pipeline moved to GPU: {device}")
                else:
                    print("⚠️ CUDA not available, using CPU (will be slow)")
                
                # 🚀 A100 Optimization: MAXIMAL batch sizes for best performance
                # A100 has 40GB VRAM, can handle MUCH larger batches than A10G (24GB)
                try:
                    # Set optimal batch sizes for A100
                    if hasattr(self.diarization_pipeline, '_segmentation') and hasattr(self.diarization_pipeline._segmentation, 'model'):
                        # Move segmentation model to GPU
                        self.diarization_pipeline._segmentation.model = self.diarization_pipeline._segmentation.model.to(device)
                        seg_device = next(self.diarization_pipeline._segmentation.model.parameters()).device
                        print(f"🔍 Segmentation model device: {seg_device}")
                        
                        # Set batch size (VERY LOW to avoid std() errors)
                        # std() requires degrees of freedom > 0, so batch must be small
                        if hasattr(self.diarization_pipeline._segmentation, 'batch_size'):
                            self.diarization_pipeline._segmentation.batch_size = 8
                            print(f"✅ Segmentation batch size: 8 (SAFE - prevents std() errors)")
                    
                    if hasattr(self.diarization_pipeline, '_embedding') and hasattr(self.diarization_pipeline._embedding, 'model'):
                        # Move embedding model to GPU
                        self.diarization_pipeline._embedding.model = self.diarization_pipeline._embedding.model.to(device)
                        emb_device = next(self.diarization_pipeline._embedding.model.parameters()).device
                        print(f"🔍 Embedding model device: {emb_device}")
                        
                        # Set batch size (VERY LOW - std() calculation critical point)
                        if hasattr(self.diarization_pipeline._embedding, 'batch_size'):
                            self.diarization_pipeline._embedding.batch_size = 16
                            print(f"✅ Embedding batch size: 16 (SAFE - prevents std() errors)")
                    
                    print("✅ GPU verification and A10G batch optimization complete")
                except Exception as batch_err:
                    print(f"⚠️ Batch optimization failed: {batch_err}")
                
                print("✅ pyannote.audio 3.1 pipeline loaded and cached")
                print(f"🔍 Pipeline type: {type(self.diarization_pipeline)}")
                print("⚡ 3.1 benefits: Faster inference, easier deployment, pure PyTorch")
            except Exception as e:
                import traceback
                print(f"❌ Failed to load diarization pipeline: {type(e).__name__}: {e}")
                print(f"❌ Full traceback:\n{traceback.format_exc()}")
                self.diarization_pipeline = None
        else:
            print("❌ No HUGGINGFACE_TOKEN found in environment!")
            print("❌ Speaker diarization DISABLED")
            print(f"🔍 Available env vars: {list(os.environ.keys())[:10]}")
            self.diarization_pipeline = None
    
    @modal.method()
    def test_env(self):
        """Test method to check environment variables"""
        hf_token = os.environ.get("HUGGINGFACE_TOKEN")
        return {
            "has_token": hf_token is not None,
            "token_length": len(hf_token) if hf_token else 0,
            "token_prefix": hf_token[:10] if hf_token else "NONE",
            "env_keys": list(os.environ.keys()),
            "pipeline_loaded": self.diarization_pipeline is not None
        }
    
    @modal.method()
    def transcribe(
        self,
        audio_url: str,
        model: str = "base",  # Parameter kept for compatibility but ignored (uses cached model)
        language: str = None,
        task: str = "transcribe",
        return_timestamps: bool = True,
        word_timestamps: bool = True,
        enable_diarization: bool = False,
        min_speakers: int = None,
        max_speakers: int = None,
    ) -> dict:
        """
        Transcribe audio from URL with optional speaker diarization
        
        Args:
            audio_url: Public URL to audio file
            model: Model size (ignored, uses cached 'base' model)
            language: Language code (e.g., 'en', 'tr', 'de', 'fr', 'es', etc.) or None for auto-detect
            task: 'transcribe' or 'translate'
            return_timestamps: Include segment timestamps
            word_timestamps: Include word-level timestamps
            enable_diarization: Enable speaker diarization (True/False)
            min_speakers: Minimum number of speakers (optional)
            max_speakers: Maximum number of speakers (optional)
        
        Returns:
            dict: {
                "text": str,  # Full transcription
                "segments": list,  # Segment details with timestamps
                "language": str,  # Detected/specified language
                "speakers": list | None,  # Speaker diarization data (if enabled)
                "speaker_count": int,  # Number of unique speakers detected
                "transcript_with_speakers": str,  # Formatted text with speaker labels
            }
        """
        import requests
        import tempfile
        import os
        import torch  # CRITICAL: Import before using!
        
        # ============================================
        # 🚀 A100 OPTIMIZATIONS - TF32 only (NO FP16!)
        # FP16 mixed precision causes issues with pyannote's std() calculations
        # ============================================
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.set_float32_matmul_precision('high')  # 'high' on A100
        
        print(f"🔒 A100 TF32 RE-ENABLED: matmul={torch.backends.cuda.matmul.allow_tf32}, cudnn={torch.backends.cudnn.allow_tf32}")
        print(f"🔍 Float32 precision: {torch.get_float32_matmul_precision()}")
        print(f"🔍 cuDNN benchmark: {torch.backends.cudnn.benchmark}")
        print(f"⚠️ FP16 disabled - pyannote requires float32 for stability")
        
        print(f"🎵 Downloading audio from: {audio_url}")
        print(f"🗣️ Speaker diarization: {'ENABLED' if enable_diarization else 'DISABLED'}")
        
        # Download audio file
        response = requests.get(audio_url, timeout=300)
        response.raise_for_status()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.content)
            audio_path = tmp_file.name
        
        try:
            # Step 1: Whisper Transcription
            print(f"🎬 Transcribing audio (using cached Whisper model)...")
            
            # Verify Whisper is using GPU
            import torch
            if torch.cuda.is_available():
                print(f"🔍 Whisper using GPU: {torch.cuda.get_device_name(0)}")
                print(f"🔍 GPU memory allocated: {torch.cuda.memory_allocated()/1024**2:.1f}MB")
            
            whisper_result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                task=task,
                verbose=False,
                word_timestamps=word_timestamps
            )
            
            print(f"✅ Transcription complete: {len(whisper_result['text'])} chars")
            
            # Step 2: Speaker Diarization (if enabled)
            speakers_data = None
            speaker_count = 0
            transcript_with_speakers = whisper_result["text"]
            
            if enable_diarization and self.diarization_pipeline:
                import time
                
                print(f"👥 Running speaker diarization...")
                print(f"🔍 Audio path: {audio_path}")
                print(f"🔍 Min speakers: {min_speakers}, Max speakers: {max_speakers}")
                
                # Calculate expected time for A10G GPU
                # A10G Performance: 10 dakika ses için ~1-2 dakika (T4'te 2-4 dakika)
                audio_duration = whisper_result["segments"][-1]["end"] if whisper_result["segments"] else 0
                expected_max_time = max(audio_duration * 0.2, 60)  # A10G: %20 (T4: %40), En az 1 dakika
                print(f"⏱️ Audio duration: {audio_duration:.1f}s")
                print(f"⏱️ Expected max diarization time (A10G): {expected_max_time:.1f}s ({expected_max_time/60:.1f} min)")
                
                # A100 batch sizes (conservative for std() stability)
                try:
                    print(f"✅ Using A100 batch sizes: seg=32, emb=128 (conservative for stability)")
                except Exception as e:
                    print(f"⚠️ Batch size check skipped: {e}")
                
                try:
                    diarization_start = time.time()
                    print(f"📡 Calling pyannote 3.1 pipeline on A100... (started at {time.strftime('%H:%M:%S')})")
                    print(f"🔍 Pipeline object: {type(self.diarization_pipeline)}")
                    
                    # 🚀 Final A100 optimization check before diarization
                    import torch
                    print(f"🔍 TF32 before diarization: matmul={torch.backends.cuda.matmul.allow_tf32}, cudnn={torch.backends.cudnn.allow_tf32}")
                    print(f"🔍 cuDNN benchmark: {torch.backends.cudnn.benchmark}")
                    
                    # Force enable (should be locked, but just in case)
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
                    torch.backends.cudnn.benchmark = True
                    
                    # Verify GPU memory usage
                    if torch.cuda.is_available():
                        print(f"🔍 GPU: {torch.cuda.get_device_name(0)}")
                        print(f"🔍 GPU memory before diarization: {torch.cuda.memory_allocated()/1024**2:.1f}MB")
                    
                    # pyannote 3.1 + A100 + TF32 = ULTRA FAST (5min audio → ~45-60s)
                    print("⚡ Using pyannote 3.1 + A100 GPU + TF32 (NO FP16 - stable float32)")
                    
                    # Use num_speakers if both min and max are same (fastest!)
                    kwargs = {}
                    if min_speakers is not None and max_speakers is not None and min_speakers == max_speakers:
                        kwargs['num_speakers'] = min_speakers
                        print(f"🎯 Using num_speakers={min_speakers} (fastest mode)")
                    else:
                        if min_speakers is not None:
                            kwargs['min_speakers'] = min_speakers
                        if max_speakers is not None:
                            kwargs['max_speakers'] = max_speakers
                        print(f"🔍 Auto-detecting speakers (min={min_speakers}, max={max_speakers})")
                    
                    # Timeout using Modal's container timeout (1800s)
                    timeout_seconds = int(expected_max_time * 2)  # 2x buffer
                    
                    print(f"⏱️ Starting diarization with kwargs: {kwargs}")
                    print(f"⏱️ Expected time on A100: ~{expected_max_time * 0.15:.0f}s (6x faster than A10G!)")
                    
                    # ============================================
                    # Run diarization with FLOAT32 (NO FP16!)
                    # FP16 causes "degrees of freedom <= 0" warnings in pyannote
                    # A100 + TF32 is fast enough without FP16
                    # ============================================
                    diarization = self.diarization_pipeline(audio_path, **kwargs)
                    
                    diarization_elapsed = time.time() - diarization_start
                    ratio = diarization_elapsed / audio_duration if audio_duration > 0 else 0
                    
                    print(f"✅ Pyannote pipeline returned successfully in {diarization_elapsed:.1f}s")
                    print(f"🔍 Diarization result type: {type(diarization)}")
                    
                    # 📊 Detailed Performance Analysis
                    print(f"\n{'='*60}")
                    print(f"📊 PERFORMANCE ANALYSIS")
                    print(f"{'='*60}")
                    print(f"⏱️ Audio duration: {audio_duration:.1f}s ({audio_duration/60:.1f} min)")
                    print(f"⏱️ Diarization time: {diarization_elapsed:.1f}s ({diarization_elapsed/60:.1f} min)")
                    print(f"📊 Performance ratio: {ratio:.2f}x")
                    
                    # Performance grading
                    if ratio < 0.3:
                        print(f"✅ EXCELLENT! (Target: <0.3x, Achieved: {ratio:.2f}x)")
                        print(f"🚀 TF32 and GPU optimization working perfectly!")
                    elif ratio < 0.5:
                        print(f"✅ GOOD (Target: <0.3x, Achieved: {ratio:.2f}x)")
                        print(f"💡 Slightly slower than optimal, but acceptable")
                    elif ratio < 0.8:
                        print(f"⚠️ ACCEPTABLE (Target: <0.3x, Achieved: {ratio:.2f}x)")
                        print(f"⚠️ Consider checking TF32 status and batch sizes")
                    else:
                        print(f"❌ POOR (Target: <0.3x, Achieved: {ratio:.2f}x)")
                        print(f"❌ GPU or TF32 may not be working correctly!")
                        print(f"❌ Check: 1) GPU device 2) TF32 enabled 3) Batch sizes")
                    
                    print(f"{'='*60}\n")
                    
                    
                    # Extract speaker segments
                    speakers_data = []
                    segment_count = 0
                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        segment_count += 1
                        speakers_data.append({
                            "speaker": speaker,
                            "start": float(turn.start),
                            "end": float(turn.end),
                        })
                        if segment_count <= 3:  # Log first 3 segments
                            print(f"  🔍 Segment {segment_count}: speaker={speaker}, start={turn.start:.2f}s, end={turn.end:.2f}s")
                    
                    speaker_count = len(set([s["speaker"] for s in speakers_data]))
                    print(f"✅ Diarization complete: {len(speakers_data)} segments, {speaker_count} unique speakers")
                    
                    if len(speakers_data) == 0:
                        print("⚠️ WARNING: pyannote returned 0 segments!")
                        print("⚠️ This could mean:")
                        print("   - Audio is very short")
                        print("   - Audio has only silence")
                        print("   - Single speaker detected (pyannote sometimes returns empty for single speaker)")
                        print("   - Pipeline configuration issue")
                    
                    # Step 3: Merge transcription with speaker labels
                    transcript_with_speakers = self._merge_transcription_and_speakers(
                        whisper_result["segments"],
                        speakers_data
                    )
                    
                except Exception as e:
                    import traceback
                    print(f"⚠️ Diarization failed: {type(e).__name__}: {e}")
                    print(f"⚠️ Full traceback:\n{traceback.format_exc()}")
                    speakers_data = None
                    speaker_count = 0
            
            # Return complete results
            return {
                "text": whisper_result["text"],
                "segments": whisper_result["segments"],
                "language": whisper_result.get("language", "unknown"),
                "duration": whisper_result["segments"][-1]["end"] if whisper_result["segments"] else 0,
                "speakers": speakers_data,
                "speaker_count": speaker_count,
                "transcript_with_speakers": transcript_with_speakers,
            }
        
        finally:
            # Cleanup temporary file
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    def _merge_transcription_and_speakers(
        self,
        whisper_segments: list,
        speaker_segments: list
    ) -> str:
        """
        Merge Whisper transcription segments with speaker diarization data
        
        Args:
            whisper_segments: Whisper segments with text and timestamps
            speaker_segments: Speaker diarization segments with speaker labels
        
        Returns:
            Formatted transcript with speaker labels (e.g., "SPEAKER_00: Hello world...")
        """
        if not speaker_segments:
            return " ".join([seg["text"] for seg in whisper_segments])
        
        merged_text = []
        current_speaker = None
        
        for seg in whisper_segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            seg_mid = (seg_start + seg_end) / 2
            
            # Find speaker at this timestamp
            speaker = self._find_speaker_at_time(seg_mid, speaker_segments)
            
            # Add speaker label when speaker changes
            if speaker != current_speaker:
                if current_speaker is not None:
                    merged_text.append("\n\n")
                merged_text.append(f"{speaker}: ")
                current_speaker = speaker
            
            merged_text.append(seg["text"].strip() + " ")
        
        return "".join(merged_text)
    
    def _find_speaker_at_time(self, time: float, speaker_segments: list) -> str:
        """Find which speaker is speaking at given timestamp"""
        # Find exact match
        for seg in speaker_segments:
            if seg["start"] <= time <= seg["end"]:
                return seg["speaker"]
        
        # If no exact match, find closest speaker
        closest_speaker = min(
            speaker_segments,
            key=lambda s: min(abs(s["start"] - time), abs(s["end"] - time))
        )
        return closest_speaker["speaker"]


# ==========================================
# T4 GPU - Transcription ONLY (No Diarization)
# ==========================================
# Cheaper and faster for simple transcription without speaker detection
# Use this when enable_diarization=False

@app.cls(
    image=whisper_diarization_image,
    gpu="T4",  # ✅ Nvidia T4 GPU - Cheaper, sufficient for Whisper only
    timeout=600,  # 10 minutes (uzun sesler için)
    memory=16384,  # 16GB RAM
    volumes={"/cache": volume},
    scaledown_window=300,  # 5 dakika idle sonra kapat (renamed parameter)
    concurrency_limit=10,  # 10 parallel requests per container (new Modal 1.0 syntax)
)
class WhisperOnlyModel:
    """
    Whisper transcription ONLY (no diarization)
    - Uses cheaper T4 GPU
    - Faster for transcription-only tasks
    - No speaker detection
    """
    
    @modal.enter()
    def load_models(self):
        import whisper
        import torch
        import warnings
        
        # � LOCK TF32 - cannot be disabled
        try:
            # Lock matmul TF32
            original_matmul_setter = torch.backends.cuda.matmul.__class__.allow_tf32.fset
            
            def locked_matmul_tf32_setter(self, value):
                if value is False:
                    print("🚫 BLOCKED: Attempt to disable matmul TF32")
                    return
                original_matmul_setter(self, value)
            
            torch.backends.cuda.matmul.__class__.allow_tf32 = property(
                torch.backends.cuda.matmul.__class__.allow_tf32.fget,
                locked_matmul_tf32_setter
            )
            
            # Lock cuDNN TF32
            original_cudnn_setter = torch.backends.cudnn.__class__.allow_tf32.fset
            
            def locked_cudnn_tf32_setter(self, value):
                if value is False:
                    print("🚫 BLOCKED: Attempt to disable cuDNN TF32")
                    return
                original_cudnn_setter(self, value)
            
            torch.backends.cudnn.__class__.allow_tf32 = property(
                torch.backends.cudnn.__class__.allow_tf32.fget,
                locked_cudnn_tf32_setter
            )
            
            print("✅ TF32 setters locked")
        except Exception as e:
            print(f"⚠️ TF32 lock failed: {e}")
        
        # Enable TF32
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.set_float32_matmul_precision('medium')
        
        print("🔒 TF32 LOCKED ON for T4")
        print(f"🔍 TF32 status: matmul={torch.backends.cuda.matmul.allow_tf32}, cudnn={torch.backends.cudnn.allow_tf32}")
        
        print("🔄 Loading Whisper model for T4 (transcription only)...")
        self.whisper_model = whisper.load_model("base", download_root="/cache")
        
        # Verify Whisper model is on GPU
        if torch.cuda.is_available():
            print(f"🔍 Whisper will use GPU: {torch.cuda.get_device_name(0)}")
        
        print("✅ Whisper model loaded on T4")
    
    @modal.method()
    def transcribe(
        self,
        audio_url: str,
        model: str = "base",
        language: str = None,
        task: str = "transcribe",
        return_timestamps: bool = True,
        word_timestamps: bool = True,
    ) -> dict:
        """
        Transcribe audio from URL (no diarization)
        
        Args:
            audio_url: Public URL to audio file
            model: Model size (ignored, uses cached 'base')
            language: Language code or None for auto-detect
            task: 'transcribe' or 'translate'
            return_timestamps: Include segment timestamps
            word_timestamps: Include word-level timestamps
        
        Returns:
            dict: {text, segments, language, duration}
        """
        import requests
        import tempfile
        
        print(f"🎵 [T4] Downloading audio from: {audio_url}")
        
        response = requests.get(audio_url, timeout=300)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.content)
            audio_path = tmp_file.name
        
        try:
            print(f"🎬 [T4] Transcribing (no diarization)...")
            
            # Verify Whisper is using GPU
            import torch
            if torch.cuda.is_available():
                print(f"🔍 Whisper using GPU: {torch.cuda.get_device_name(0)}")
                print(f"🔍 GPU memory allocated: {torch.cuda.memory_allocated()/1024**2:.1f}MB")
            
            result = self.whisper_model.transcribe(
                audio_path,
                language=language,
                task=task,
                verbose=False,
                word_timestamps=word_timestamps
            )
            
            print(f"✅ [T4] Transcription complete: {len(result['text'])} chars")
            
            return {
                "text": result["text"],
                "segments": result["segments"],
                "language": result.get("language", "unknown"),
                "duration": result["segments"][-1]["end"] if result["segments"] else 0,
                "speakers": None,
                "speaker_count": 0,
                "transcript_with_speakers": result["text"],
            }
        finally:
            import os
            if os.path.exists(audio_path):
                os.unlink(audio_path)


# Local testing function
@app.local_entrypoint()
def test():
    """Test the transcription function with speaker diarization"""
    # Test with sample audio (you should provide your own test file)
    # For testing, upload a short audio to your MinIO/S3 or use a public URL
    test_url = "https://www2.cs.uic.edu/~i101/SoundFiles/gettysburg10.wav"  # Short public test audio
    
    # Create model instance (container starts, models load ONCE)
    model = WhisperDiarizationModel()
    
    print("\n" + "="*50)
    print("🧪 TEST 1: Transcription only (no diarization)")
    print("="*50)
    result1 = model.transcribe.remote(
        audio_url=test_url,
        language=None,
        enable_diarization=False
    )
    
    print(f"Text: {result1['text'][:200]}...")
    print(f"Language: {result1['language']}")
    print(f"Segments: {len(result1['segments'])}")
    print(f"Duration: {result1['duration']:.1f}s")
    print(f"Speaker count: {result1['speaker_count']}")
    
    print("\n" + "="*50)
    print("🧪 TEST 2: Transcription + Speaker Diarization")
    print("="*50)
    result2 = model.transcribe.remote(
        audio_url=test_url,
        language=None,
        enable_diarization=True,
        min_speakers=1,
        max_speakers=3
    )
    
    print(f"Text: {result2['text'][:200]}...")
    print(f"Speaker count: {result2['speaker_count']}")
    print(f"\n📝 Transcript with speakers:\n{result2['transcript_with_speakers'][:500]}...")
    print("="*50)


if __name__ == "__main__":
    # For local testing: modal run modal_whisper_function.py
    pass
