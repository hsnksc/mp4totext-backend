"""
Modal Worker for MP4toText
Handles transcription processing with ffmpeg, Whisper, and speaker recognition
Supports concurrent processing of multiple jobs
"""

import modal
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Modal App Configuration
app = modal.App("mp4totext-worker")

# Create Modal Image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "ffmpeg",
        "libsndfile1",
        "git"
    )
    .pip_install(
        "fastapi==0.109.0",
        "sqlalchemy==2.0.25",
        "psycopg2-binary==2.9.9",
        "python-multipart==0.0.6",
        "openai-whisper==20231117",
        "torch==2.1.2",
        "torchaudio==2.1.2",
        "pyannote.audio==3.1.1",
        "assemblyai==0.23.1",
        "google-generativeai==0.3.2",
        "boto3==1.34.23",
        "requests==2.31.0",
        "redis==5.0.1",
        "celery==5.3.6",
        "pydantic==2.5.3",
        "pydantic-settings==2.1.0"
    )
)

# Modal Secrets for environment variables
secrets = [
    modal.Secret.from_name("mp4totext-secrets")
]

# Shared volume for temporary files
volume = modal.Volume.from_name("mp4totext-temp", create_if_missing=True)

# Mount local app package
from modal.mount import Mount
mount = Mount.from_local_dir("app", remote_path="/root/app")

@app.function(
    image=image,
    secrets=secrets,
    volumes={"/tmp/modal": volume},
    mounts=[mount],
    timeout=3600,  # 1 hour timeout per job
    cpu=4.0,  # 4 CPU cores
    memory=16384,  # 16GB RAM
    concurrency_limit=25,  # Max 25 concurrent jobs
    keep_warm=2  # Keep 2 containers warm for faster startup
)
def process_transcription_modal(
    file_url: str,
    language: str,
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a transcription job on Modal (Stateless)
    
    Args:
        file_url: URL to download the audio/video file
        language: Target language code (e.g., 'en', 'tr')
        config: Configuration dict with settings
        
    Returns:
        Dict with status, text, segments, duration, and metadata
    """
    import sys
    import time
    import requests
    import tempfile
    import os
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Starting Modal transcription job")
    start_time = time.time()
    
    try:
        # Import dependencies
        from app.services.audio_processor import get_audio_processor
        
        # Download file from storage
        logger.info(f"📥 Downloading file from {file_url}")
        
        # Create temp directory
        temp_dir = Path("/tmp/modal") / f"transcription_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Download file
        filename = file_url.split('/')[-1].split('?')[0] or "input_file"
        local_file_path = temp_dir / filename
        
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        
        with open(local_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✅ File downloaded to {local_file_path}")
        
        # Process audio with ffmpeg
        logger.info("🎵 Processing audio with ffmpeg...")
        audio_processor = get_audio_processor()
        audio_path = audio_processor.convert_to_wav(str(local_file_path))
        
        # Get audio duration
        duration = audio_processor.get_duration(audio_path)
        duration_minutes = duration / 60.0
        
        logger.info(f"⏱️ Audio duration: {duration_minutes:.2f} minutes")
        
        # Transcribe based on provider
        provider = config.get('provider', 'whisper')
        result_data = {}
        
        if provider == 'assemblyai':
            logger.info("🎤 Using AssemblyAI for transcription...")
            import assemblyai as aai
            aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
            
            # Configure AssemblyAI
            aai_config = aai.TranscriptionConfig(
                language_code=language,
                speaker_labels=config.get('speaker_diarization', False)
            )
            
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_path, config=aai_config)
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"AssemblyAI error: {transcript.error}")
            
            result_data = {
                "text": transcript.text,
                "segments": [], # AssemblyAI segments format adaptation needed if used
                "words": transcript.words
            }
            
        else:  # whisper
            logger.info("🎤 Using Whisper for transcription...")
            import whisper
            
            model_size = config.get('model', 'base')
            model = whisper.load_model(model_size)
            
            result = model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                verbose=False
            )
            
            result_data = {
                "text": result['text'],
                "segments": result['segments']
            }
            
            # Speaker diarization if enabled
            if config.get('speaker_diarization', False):
                logger.info("👥 Running speaker diarization...")
                from app.services.speaker_recognition import create_speaker_recognizer
                
                # Use HuggingFace token from secrets
                hf_token = os.getenv("HF_TOKEN")
                if not hf_token:
                    logger.warning("⚠️ HF_TOKEN not found, skipping diarization")
                else:
                    recognizer = create_speaker_recognizer(use_gpu=False) # CPU on Modal for now
                    speakers = recognizer.diarize(audio_path, min_speakers=config.get('min_speakers'), max_speakers=config.get('max_speakers'))
                    result_data["speakers"] = speakers
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return {
            "status": "success",
            "duration": duration,
            "result": result_data,
            "processing_time": time.time() - start_time
        }

    except Exception as e:
        logger.error(f"❌ Modal processing failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
