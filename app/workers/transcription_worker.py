"""
Transcription background worker
Processes audio files with Whisper + Speaker Recognition
"""

import os
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Celery imports
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from app.celery_config import celery_app

# Export app for celery CLI: celery -A app.workers.transcription_worker worker
app = celery_app

# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.settings import get_settings
from app.models.transcription import Transcription, TranscriptionStatus

# Services - lazy imports for heavy dependencies
from app.services.storage import FileStorageService
from app.services.gemini_service import get_gemini_service
from app.services.credit_service import get_credit_service, CreditPricing
from app.models.credit_transaction import OperationType

# Audio processor - lazy import
def get_audio_processor_lazy():
    from app.services.audio_processor import get_audio_processor
    return get_audio_processor()

# Speaker recognition - lazy import  
def create_speaker_recognizer_lazy(*args, **kwargs):
    from app.services.speaker_recognition import create_speaker_recognizer
    return create_speaker_recognizer(*args, **kwargs)

# WebSocket (optional)
try:
    from app.websocket import get_ws_manager
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

logger = logging.getLogger(__name__)
settings = get_settings()

# Create database session factory for workers
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def merge_speaker_info_with_segments(segments: list, speakers: list) -> list:
    """
    Merge speaker diarization info with Whisper segments
    
    Args:
        segments: Whisper segments with timestamps
        speakers: Speaker diarization data [{speaker, start, end}, ...]
        
    Returns:
        Updated segments with speaker info
    """
    if not speakers or not segments:
        return segments
    
    # Create a copy to avoid modifying original
    updated_segments = []
    
    for segment in segments:
        segment_copy = segment.copy()
        segment_start = segment.get('start', 0)
        segment_end = segment.get('end', 0)
        segment_mid = (segment_start + segment_end) / 2
        
        # Find speaker with most overlap with this segment
        best_speaker = None
        max_overlap = 0
        
        for speaker_info in speakers:
            speaker_start = speaker_info['start']
            speaker_end = speaker_info['end']
            
            # Calculate overlap
            overlap_start = max(segment_start, speaker_start)
            overlap_end = min(segment_end, speaker_end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = speaker_info['speaker']
        
        # Add speaker to segment
        segment_copy['speaker'] = best_speaker
        updated_segments.append(segment_copy)
    
    return updated_segments


class TranscriptionTask(Task):
    """Base task for transcription with automatic retry"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 1}  # 🚨 Only 1 retry to save AssemblyAI costs
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes max
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=TranscriptionTask,
    name="app.workers.process_transcription",
    time_limit=900,  # 15 minutes hard timeout (kills task)
    soft_time_limit=840,  # 14 minutes soft timeout (raises exception)
)
def process_transcription_task(self, transcription_id: int) -> Dict[str, Any]:
    """
    Process transcription task in background
    
    Args:
        transcription_id: ID of transcription to process
        
    Returns:
        Result dictionary with status and data
    """
    # Wait a moment for commit to propagate
    time.sleep(0.2)
    
    db: Session = SessionLocal()
    
    try:
        logger.info(f"🎬 Starting transcription task: {transcription_id}")
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Initializing...'}
        )
        
        # Get transcription from database (with fresh query)
        db.expire_all()  # Force fresh query
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        
        if not transcription:
            raise ValueError(f"Transcription not found: {transcription_id}")
        
        # Update status to processing
        transcription.status = TranscriptionStatus.PROCESSING
        transcription.progress = 0
        transcription.started_at = datetime.utcnow()
        db.commit()
        
        # Update progress: 10%
        transcription.progress = 10
        db.commit()
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Loading file...'}
        )
        
        # Get file path from storage
        storage = FileStorageService()
        file_path = storage.get_file_path(transcription.file_id)
        
        if not file_path or not file_path.exists():
            raise FileNotFoundError(f"File not found: {transcription.file_id}")
        
        logger.info(f"📁 Processing file: {file_path}")
        
        # Update progress: 20%
        transcription.progress = 20
        db.commit()
        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Loading models...'}
        )
        
        # =========================================================================
        # TRANSCRIPTION PROVIDER SELECTION
        # Priority:
        #   1. AssemblyAI (if diarization enabled and USE_ASSEMBLYAI=true)
        #   2. Modal OpenAI Whisper (if USE_MODAL=true, no diarization)
        #   3. Replicate / RunPod (fallback)
        # =========================================================================
        
        # Check cloud transcription settings
        use_assemblyai = settings.USE_ASSEMBLYAI and transcription.enable_diarization
        use_modal = settings.USE_MODAL and not transcription.enable_diarization
        use_replicate = settings.USE_REPLICATE
        use_runpod = settings.USE_RUNPOD
        
        if use_assemblyai:
            # Use AssemblyAI for transcription with speaker diarization
            logger.info("☁️ Using AssemblyAI for transcription (with diarization)")
            transcription.progress = 30
            db.commit()
            self.update_state(
                state='PROGRESS',
                meta={'current': 30, 'total': 100, 'status': 'Transcribing with AssemblyAI...'}
            )
            
            from app.services.assemblyai_service import get_assemblyai_service
            from app.services.storage import get_storage_service
            
            assemblyai_service = get_assemblyai_service()
            storage_service = get_storage_service()
            
            # Language handling for AssemblyAI
            # Note: Language will be auto-detected by Whisper in AssemblyAI service
            language_param = transcription.language
            if language_param in ['unknown', None, '', 'auto-detected']:
                language_param = None  # Let Whisper detect language
                logger.info(f"🌍 Language unknown, will use Whisper auto-detection")
            else:
                logger.info(f"🌍 Using specified language: {language_param}")
            
            # Upload to MinIO
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"📦 File size: {file_size_mb:.1f}MB, uploading to MinIO...")
            
            audio_url = storage_service.upload_to_minio(str(file_path))
            
            if not audio_url:
                raise ValueError(
                    f"Failed to upload file to MinIO. "
                    f"Make sure ngrok tunnel is running! See NGROK_SETUP.md"
                )
            
            logger.info(f"✅ File uploaded, using URL for AssemblyAI")
            
            start_time = time.time()
            
            # 🎯 SPEECH UNDERSTANDING: Configure features based on user selection
            from app.services.assemblyai.config import (
                TranscriptionFeatures,
                SpeechUnderstandingConfig,
                LLMGatewayConfig,
            )
            
            # Check if user requested advanced features
            assemblyai_features = transcription.assemblyai_features_enabled or {}
            
            # 🔥 FIX: Read detailed feature config from dictionary (not boolean)
            speech_understanding_config = assemblyai_features.get('speech_understanding', {})
            llm_gateway_config = assemblyai_features.get('llm_gateway', {})
            
            # Handle backward compatibility: old format was boolean True, new format is dictionary
            if speech_understanding_config == True:
                speech_understanding_config = {
                    'sentiment_analysis': True,
                    'auto_chapters': True,
                    'entity_detection': True,
                    'auto_highlights': True,
                    'speaker_labels': True
                }
            if llm_gateway_config == True:
                llm_gateway_config = {
                    'enabled': True,
                    'generate_summary': True,
                    'enable_qa': True,
                    'extract_action_items': True
                }
            
            # Base features (always enabled for AssemblyAI)
            features = TranscriptionFeatures(
                speech_understanding=SpeechUnderstandingConfig(
                    speaker_labels=True,  # Always enable diarization
                    sentiment_analysis=speech_understanding_config.get('sentiment_analysis', False),
                    auto_chapters=speech_understanding_config.get('auto_chapters', False),
                    entity_detection=speech_understanding_config.get('entity_detection', False),
                    iab_categories=False,  # Keep disabled (expensive)
                    content_safety=False,  # Keep disabled
                    auto_highlights=speech_understanding_config.get('auto_highlights', False),
                    redact_pii=False,
                ),
                llm_gateway=LLMGatewayConfig(
                    enabled=llm_gateway_config.get('enabled', False),
                    generate_summary=llm_gateway_config.get('generate_summary', False),
                    enable_qa=llm_gateway_config.get('enable_qa', False),
                    extract_action_items=llm_gateway_config.get('extract_action_items', False),
                ),
            )
            
            # Log enabled features
            enabled_features = []
            if speech_understanding_config.get('sentiment_analysis'):
                enabled_features.append("sentiment")
            if speech_understanding_config.get('auto_chapters'):
                enabled_features.append("chapters")
            if speech_understanding_config.get('entity_detection'):
                enabled_features.append("entities")
            if speech_understanding_config.get('auto_highlights'):
                enabled_features.append("highlights")
            
            if enabled_features:
                logger.info(f"🎯 Speech Understanding enabled: {', '.join(enabled_features)}")
            if llm_gateway_config.get('enabled'):
                logger.info("🤖 LLM Gateway enabled: summary, Q&A, action_items")
            if not enabled_features and not llm_gateway_config.get('enabled'):
                logger.info("📝 Basic transcription with diarization only")
            
            try:
                # Call AssemblyAI with full Speech Understanding + LeMUR features
                result = assemblyai_service.transcribe_audio(
                    audio_url=audio_url,
                    language=language_param,
                    enable_diarization=True,
                    auto_detect_language=True,  # 🔥 Enable Whisper language detection
                    features=features           # 🎯 NEW: Speech Understanding + LeMUR
                )
            except Exception as assemblyai_error:
                processing_time = time.time() - start_time
                logger.error(f"❌ AssemblyAI transcription failed after {processing_time:.1f}s")
                logger.error(f"❌ Error: {str(assemblyai_error)}")
                raise
            
            processing_time = time.time() - start_time
            logger.info(f"✅ AssemblyAI transcription completed in {processing_time:.1f}s")
            
            # Update transcription with basic results
            transcription.text = result["text"]
            transcription.processing_time = processing_time
            transcription.text_length = len(result["text"])
            transcription.detected_language = result.get("language", "unknown")
            transcription.speaker_count = result.get("speaker_count", 0)
            transcription.transcription_provider = "assemblyai"
            
            # 🔥 FIX: Use utterances (speaker-grouped sentences) instead of word-level segments
            # Utterances are better for UI display - shows complete sentences per speaker
            transcription.speakers_json = result.get("speakers", [])
            transcription.segments = result.get("utterances", [])  # Use utterances, not segments!
            
            # 🎯 NEW: Save Speech Understanding results
            speech_understanding = result.get("speech_understanding", {})
            if speech_understanding:
                transcription.sentiment_analysis = speech_understanding.get("sentiment_analysis")
                transcription.auto_chapters = speech_understanding.get("chapters")
                transcription.entities = speech_understanding.get("entities")
                transcription.topics = speech_understanding.get("topics")
                transcription.content_safety = speech_understanding.get("content_safety")
                transcription.highlights = speech_understanding.get("highlights")
                logger.info(f"🎯 Speech Understanding saved: {len(speech_understanding)} features")
            
            # 🤖 NEW: Save LLM Gateway results (mapped to legacy fields for UI)
            llm_results = result.get("llm_gateway") or result.get("lemur", {})
            if llm_results:
                summary_obj = llm_results.get("summary")
                if summary_obj:
                    transcription.lemur_summary = summary_obj.get("text", "")
                    logger.info(f"📝 LLM summary saved ({len(transcription.lemur_summary)} chars)")
                transcription.lemur_questions_answers = llm_results.get("questions_and_answers")
                transcription.lemur_action_items = llm_results.get("action_items")
                transcription.lemur_custom_tasks = llm_results.get("custom_tasks")
                
            # 📊 Save enabled features configuration
            transcription.assemblyai_features_enabled = features.to_dict()
            
            if result.get("utterances"):
                logger.info(f"👥 Detected {result['speaker_count']} speakers with {len(result['utterances'])} utterances")
            
        elif use_modal:
            # Use Modal for transcription (best for large files, serverless GPU)
            logger.info("☁️ Using Modal for transcription")
            transcription.progress = 30
            db.commit()
            self.update_state(
                state='PROGRESS',
                meta={'current': 30, 'total': 100, 'status': 'Transcribing with Modal...'}
            )
            
            from app.services.modal_service import get_modal_service
            from app.services.storage import get_storage_service
            
            modal_service = get_modal_service()
            storage_service = get_storage_service()
            whisper_model = transcription.whisper_model or "large-v3"
            
            # Language handling
            language_param = transcription.language
            if language_param in ['unknown', None, '']:
                language_param = None
            
            # Check file size - always upload to MinIO for Modal
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"📦 File size: {file_size_mb:.1f}MB, uploading to MinIO...")
            
            audio_url = storage_service.upload_to_minio(str(file_path))
            
            if not audio_url:
                raise ValueError(
                    f"Failed to upload file to MinIO. "
                    f"Make sure ngrok tunnel is running! See NGROK_SETUP.md"
                )
            
            logger.info(f"✅ File uploaded, using URL for Modal")
            
            start_time = time.time()
            
            # Calculate expected processing time (T4 GPU with batching optimization)
            estimated_duration = transcription.duration or 60  # Use transcription duration or fallback to 1 min
            expected_time = max(estimated_duration * 0.08, 15)  # T4: ~0.05-0.08x ratio
            
            logger.info(f"⏱️ Expected processing time: {expected_time:.0f}s (audio: {estimated_duration:.1f}s)")
            logger.info(f"📝 Mode: Transcription-only (no diarization)")
            logger.info(f"💰 T4 GPU: $0.36/hour with dynamic batching")
            logger.info(f"🚀 New Modal app: mp4totext-whisper-t4")
            
            try:
                # Call Modal with optimized T4 Whisper transcription (GPU only)
                result = modal_service.transcribe_audio(
                    audio_url=audio_url,
                    language=language_param
                )
            except Exception as modal_error:
                processing_time = time.time() - start_time
                logger.error(f"❌ Modal transcription failed after {processing_time:.1f}s")
                logger.error(f"❌ Error: {str(modal_error)}")
                
                # Check if timeout
                if processing_time > expected_time * 2:
                    logger.error(f"⚠️ TIMEOUT: Processing took {processing_time:.1f}s (expected <{expected_time:.0f}s)")
                    logger.error(f"⚠️ This suggests Modal container is hanging!")
                    raise ValueError(f"Modal transcription timeout: {processing_time:.1f}s exceeded expected {expected_time:.0f}s")
                raise
            
            processing_time = time.time() - start_time
            
            logger.info(f"✅ Modal transcription completed in {processing_time:.1f}s")
            
            # Performance analysis
            if processing_time > expected_time * 1.5:
                logger.warning(f"⚠️ SLOW: Processing took {processing_time:.1f}s (expected ~{expected_time:.0f}s)")
                logger.warning(f"⚠️ Audio: {estimated_duration:.1f}s, Ratio: {processing_time/estimated_duration:.2f}x")
            else:
                logger.info(f"✅ Performance OK: {processing_time:.1f}s for {estimated_duration:.1f}s audio")
            logger.info(f"🔍 Modal result keys: {list(result.keys())}")
            logger.info(f"🔍 Speaker count in result: {result.get('speaker_count', 'NOT FOUND')}")
            logger.info(f"🔍 Speakers in result: {result.get('speakers', 'NOT FOUND')}")
            
            # Update transcription with results
            transcription.transcript = result["text"]
            transcription.processing_time = processing_time
            transcription.text_length = len(result["text"])
            transcription.detected_language = result.get("language", "unknown")
            transcription.speaker_count = result.get("speaker_count", 0)
            
            # Merge speaker info with segments if diarization was enabled
            segments = result.get("segments", [])
            if transcription.enable_diarization and result.get("speakers"):
                transcription.speakers_json = result["speakers"]
                transcription.transcript_with_speakers = result["transcript_with_speakers"]
                logger.info(f"👥 Detected {result['speaker_count']} speakers")
                
                logger.info("🔄 Merging speaker info with segments...")
                segments = merge_speaker_info_with_segments(segments, result["speakers"])
                logger.info(f"✅ Merged speaker info into {len(segments)} segments")
            
            transcription.segments = segments
            
        elif use_replicate:
            # Use Replicate for transcription (native URL support)
            logger.info("☁️ Using Replicate for transcription")
            transcription.progress = 30
            db.commit()
            self.update_state(
                state='PROGRESS',
                meta={'current': 30, 'total': 100, 'status': 'Transcribing with Replicate...'}
            )
            
            from app.services.replicate_service import get_replicate_service
            from app.services.storage import get_storage_service
            
            replicate_service = get_replicate_service()
            storage_service = get_storage_service()
            whisper_model = transcription.whisper_model or "large-v3"
            
            # Language handling
            language_param = transcription.language
            if language_param in ['unknown', None, '']:
                language_param = None
            
            # Check file size - always upload to MinIO for Replicate
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"📦 File size: {file_size_mb:.1f}MB, uploading to MinIO...")
            
            audio_url = storage_service.upload_to_minio(str(file_path))
            
            if not audio_url:
                raise ValueError(
                    f"Failed to upload file to MinIO. "
                    f"Make sure ngrok tunnel is running! See NGROK_SETUP.md"
                )
            
            logger.info(f"✅ File uploaded, using URL for Replicate")
            
            start_time = time.time()
            result = replicate_service.transcribe_audio(
                audio_url=audio_url,
                language=language_param,
                model=whisper_model,
                task="transcribe"
            )
            processing_time = time.time() - start_time
            
            # Update transcription with results
            transcription.transcript = result["text"]
            transcription.processing_time = processing_time
            transcription.text_length = len(result["text"])
            transcription.detected_language = result.get("language", "unknown")
            transcription.speaker_count = result.get("speaker_count", 0)
            transcription.speakers = result.get("speakers", None)
            
            # Merge speaker info with segments if diarization was enabled
            segments = result["segments"]
            if transcription.enable_diarization and result.get("speakers"):
                logger.info("🔄 Merging speaker info with segments...")
                segments = merge_speaker_info_with_segments(segments, result["speakers"])
                logger.info(f"✅ Merged speaker info into {len(segments)} segments")
            
            transcription.segments = segments
            
        elif use_runpod:
            # Use RunPod Serverless for transcription
            logger.info("☁️ Using RunPod Serverless for transcription")
            transcription.progress = 30
            db.commit()
            self.update_state(
                state='PROGRESS',
                meta={'current': 30, 'total': 100, 'status': 'Transcribing with RunPod...'}
            )
            
            from app.services.runpod_service import get_runpod_service
            
            runpod_service = get_runpod_service()
            whisper_model = transcription.whisper_model or "large-v3"
            
            # Fix: RunPod doesn't accept 'unknown' as language code
            language_param = transcription.language
            if language_param in ['unknown', None, '']:
                language_param = None
            
            # Check file size - RunPod worker doesn't support audio_url parameter
            # For files >10MB, fall back to Local transcription instead
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            if file_size_mb > 10:
                logger.warning(
                    f"⚠️ File too large for RunPod base64 ({file_size_mb:.1f}MB > 10MB). "
                    f"Falling back to Local transcription..."
                )
                # Switch to Local processing for large files
                transcription.transcription_provider = "Local"
                db.commit()
                
                # Re-run with Local provider
                return self._process_local_transcription(
                    transcription, file_path, db
                )
            
            start_time = time.time()
            result = runpod_service.transcribe_audio(
                audio_path=str(file_path) if not audio_url else None,
                audio_url=audio_url,
                language=language_param,
                model=whisper_model,
                task="transcribe"
            )
            processing_time = time.time() - start_time
            
            logger.info(f"✅ RunPod transcription completed in {processing_time:.1f}s")
            
        else:
            # Use Local Faster-Whisper
            logger.info("🖥️ Using Local Faster-Whisper for transcription")
            
            whisper_model = transcription.whisper_model or settings.FASTER_WHISPER_MODEL
            use_faster_whisper = settings.USE_FASTER_WHISPER
            logger.info(f"🎙️ Using Whisper model: {whisper_model} (Faster-Whisper: {use_faster_whisper})")
            
            processor = get_audio_processor(
                whisper_model_size=whisper_model,
                use_faster_whisper=use_faster_whisper
            )
            
            transcription.progress = 30
            db.commit()
            self.update_state(
                state='PROGRESS',
                meta={'current': 30, 'total': 100, 'status': 'Transcribing audio...'}
            )
            
            start_time = time.time()
            result = processor.process_file(
                str(file_path),
                language=transcription.language
            )
            processing_time = time.time() - start_time
        
        # =========================================================================
        # SPEAKER DIARIZATION - Handled by Modal/Replicate (pyannote.audio 3.1)
        # =========================================================================
        # Old Resemblyzer/Silero fallback removed - diarization now done on GPU
        # If Modal/Replicate doesn't return speakers, we accept 0 count (no fallback)
        
        # Update progress: 70%
        transcription.progress = 70
        db.commit()
        self.update_state(
            state='PROGRESS',
            meta={'current': 70, 'total': 100, 'status': 'Saving results...'}
        )
        
        # Update transcription with results (if not already set by Modal)
        if not transcription.text:
            transcription.text = result["text"]
        if not transcription.language:
            transcription.language = result["language"]
        
        # Fix: RunPod output doesn't include speaker_count (only Local does)
        # Use get() with default to prevent KeyError
        if not hasattr(transcription, 'speaker_count') or transcription.speaker_count == 0:
            transcription.speaker_count = result.get("speaker_count", 0)
        if not transcription.speakers:
            transcription.speakers = result.get("speakers", None)
        
        # Only set segments if not already set (e.g., by Modal with merged speaker info)
        if not transcription.segments:
            transcription.segments = result["segments"]
        
        transcription.processing_time = processing_time
        
        # 🔥 CRITICAL FIX: Calculate duration from segments
        # Without this, credit deduction was always using fallback (60 seconds)
        if result.get("segments") and len(result["segments"]) > 0:
            # Get the end time of the last segment
            last_segment = result["segments"][-1]
            transcription.duration = int(last_segment.get("end", 0))
            logger.info(f"⏱️ Audio duration calculated from segments: {transcription.duration} seconds ({transcription.duration/60:.1f} minutes)")
        else:
            # Fallback: try to get duration from audio file metadata
            try:
                import subprocess
                cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                       '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)]
                duration_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                transcription.duration = int(float(duration_output.decode().strip()))
                logger.info(f"⏱️ Audio duration from ffprobe: {transcription.duration} seconds")
            except Exception as e:
                logger.warning(f"⚠️ Could not determine audio duration: {e}. Using 60s fallback.")
                transcription.duration = 60  # 1 minute fallback
        
        # 🔥 CRITICAL: Commit duration immediately to prevent loss
        db.commit()
        logger.info(f"✅ Duration saved to database: {transcription.duration}s")
        
        # =========================================================================
        # MANDATORY STEP: Clean transcript with Together AI (Llama-2-13B)
        # This happens BEFORE any AI enhancement (Gemini/OpenAI/Groq)
        # Removes filler words, fixes grammar without changing meaning
        # =========================================================================
        logger.info("🧹 Starting transcript cleaning...")
        transcription.progress = 75
        db.commit()
        self.update_state(
            state='PROGRESS',
            meta={'current': 75, 'total': 100, 'status': 'Cleaning transcript...'}
        )
        
        # Try Together AI first (cheaper, faster)
        from app.services.together_service import get_together_service
        together_service = get_together_service()
        
        cleaning_result = None
        if together_service.is_enabled() and result["text"]:
            logger.info("🔄 Trying Together AI...")
            cleaning_result = together_service.clean_transcript(
                raw_text=result["text"],
                language=result.get("language", "auto")
            )
            
            # If Together AI failed (503 or other error), try OpenAI as fallback
            if cleaning_result.get("error") and "service unavailable" in cleaning_result.get("error", "").lower():
                logger.warning("⚠️ Together AI unavailable, falling back to OpenAI...")
                from app.services.openai_cleaner_service import get_openai_cleaner
                openai_cleaner = get_openai_cleaner()
                
                if openai_cleaner.is_enabled():
                    cleaning_result = openai_cleaner.clean_transcript(
                        raw_text=result["text"],
                        language=result.get("language", "auto")
                    )
        
        # Use cleaning result or fallback to original text
        if cleaning_result:
            transcription.cleaned_text = cleaning_result.get("cleaned_text", result["text"])
            
            if cleaning_result.get("changes_made"):
                logger.info(f"✅ Transcript cleaned: {cleaning_result['original_length']} → {cleaning_result['cleaned_length']} chars")
            else:
                logger.info("ℹ️  No cleaning changes made (or cleaning unavailable)")
        else:
            # No cleaning service available - use original text
            transcription.cleaned_text = result["text"]
            logger.warning("⚠️ No cleaning service configured - using raw transcript")
        
        db.commit()
        
        # Gemini AI Enhancement (if requested)
        # Always run STANDARD enhancement if Gemini is enabled during upload
        # NOW USES CLEANED TEXT instead of raw Whisper output
        if transcription.use_gemini_enhancement and transcription.cleaned_text:
            try:
                # 🔧 FIX 1: Extract user-selected provider and model
                ai_provider = transcription.ai_provider or "gemini"  # Default to gemini if not set
                ai_model = transcription.ai_model  # User's selected model or None (use default)
                
                logger.info(f"🤖 User selected provider: {ai_provider}, model: {ai_model}")
                logger.info(f"🤖 Starting AI enhancement (STANDARD mode) using {ai_provider.upper()}...")
                
                transcription.progress = 80
                db.commit()
                self.update_state(
                    state='PROGRESS',
                    meta={'current': 80, 'total': 100, 'status': f'Enhancing with {ai_provider.upper()}...'}
                )
                
                # 🔧 FIX 2: Validate model exists and is active in database
                if ai_model:
                    from app.models.ai_model_pricing import AIModelPricing
                    db_model = db.query(AIModelPricing).filter_by(
                        model_key=ai_model,
                        provider=ai_provider,  # ← CRITICAL: Must match provider!
                        is_active=True
                    ).first()
                    
                    if not db_model:
                        error_msg = f"Model '{ai_model}' is not active for provider '{ai_provider}' or not found in database"
                        logger.error(f"❌ {error_msg}")
                        # Query available models for this provider
                        available_models = db.query(AIModelPricing).filter_by(
                            provider=ai_provider,
                            is_active=True
                        ).all()
                        logger.info(f"   Available models for {ai_provider}: {[m.model_key for m in available_models]}")
                        raise Exception(error_msg)
                    
                    logger.info(f"✅ Model validated: {ai_model}")
                    logger.info(f"   Provider: {db_model.provider}")
                    logger.info(f"   Credit multiplier: {db_model.credit_multiplier}")
                
                # 🔧 FIX 3: Create service instance with user selection
                import asyncio
                from app.services.gemini_service import GeminiService
                gemini = GeminiService(preferred_provider=ai_provider, preferred_model=ai_model)
                
                # 🔧 FIX 4: Validate service is configured
                if not gemini.is_enabled():
                    error_msg = f"Provider '{ai_provider}' is not configured. Check API key in settings."
                    logger.error(f"❌ {error_msg}")
                    raise Exception(error_msg)
                
                logger.info(f"✅ Service initialized: {ai_provider} with model {ai_model or 'default'}")
                
                if gemini and gemini.is_enabled():
                    transcription.gemini_status = "processing"
                    transcription.progress = 82
                    db.commit()
                    self.update_state(
                        state='PROGRESS',
                        meta={'current': 82, 'total': 100, 'status': 'Metin AI ile işleniyor...'}
                    )
                    
                    language = result.get("language", "tr")
                    
                    # ALWAYS run standard text enhancement during upload
                    # Lecture notes and custom prompts will be post-processing features
                    logger.info("✨ Running standard text enhancement...")
                    
                    # Create new event loop for Celery worker thread (avoid event loop conflicts)
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # NEW 2-STEP WEB SEARCH FLOW:
                    # 1. AI generates optimized search query FROM CLEANED TEXT
                    # 2. Tavily searches with that query
                    # 3. AI synthesizes results with CLEANED TEXT
                    # 4. Store synthesis in web_context_enrichment field
                    
                    web_context_enrichment = None
                    web_metadata = {}
                    
                    # Use CLEANED TEXT for all AI operations (web search and enhancement)
                    text_for_ai = transcription.cleaned_text
                    
                    # Only perform web search if explicitly enabled by user
                    if transcription.enable_web_search:
                        try:
                            logger.info("🔍 Step 1: AI generating optimized search query...")
                            transcription.progress = 85
                            db.commit()
                            self.update_state(
                                state='PROGRESS',
                                meta={'current': 85, 'total': 100, 'status': 'Web araması için sorgu oluşturuluyor...'}
                            )
                            
                            ai_search_query = loop.run_until_complete(
                                gemini.generate_search_query(text_for_ai, language)
                            )
                            logger.info(f"✅ AI generated search query ({len(ai_search_query)} chars):")
                            logger.info(f"   📝 Full query: {ai_search_query}")
                            
                            logger.info("🌐 Step 2: Searching web with Tavily...")
                            transcription.progress = 88
                            db.commit()
                            self.update_state(
                                state='PROGRESS',
                                meta={'current': 88, 'total': 100, 'status': 'Web araması yapılıyor...'}
                            )
                            
                            from app.services.web_search_service import get_web_search_service
                            web_service = get_web_search_service()
                            web_results = loop.run_until_complete(
                                web_service.search_context(ai_search_query, language, max_results=3)
                            )
                            
                            if web_results.get("success"):
                                logger.info(f"✅ Tavily found {web_results.get('num_results', 0)} results")
                                
                                logger.info("🔗 Step 3: AI synthesizing web context with CLEANED transcript...")
                                transcription.progress = 92
                                db.commit()
                                self.update_state(
                                    state='PROGRESS',
                                    meta={'current': 92, 'total': 100, 'status': 'Web sonuçları birleştiriliyor...'}
                                )
                                
                                web_context_enrichment = loop.run_until_complete(
                                    gemini.synthesize_web_context(text_for_ai, web_results, language)
                                )
                                logger.info(f"✅ Web context synthesized ({len(web_context_enrichment)} chars)")
                                
                                web_metadata = {
                                    "ai_generated_query": ai_search_query,
                                    "tavily_results_count": web_results.get("num_results", 0),
                                    "web_answer": web_results.get("answer", ""),
                                    "synthesized_length": len(web_context_enrichment)
                                }
                            else:
                                logger.warning("⚠️ Web search failed, skipping synthesis")
                                
                        except Exception as web_error:
                            logger.error(f"❌ Web search/synthesis failed: {web_error}")
                            web_context_enrichment = None
                    else:
                        logger.info("ℹ️ Web search disabled by user, skipping Tavily lookup")
                    
                    # Run standard text enhancement using CLEANED TEXT (not raw Whisper output)
                    transcription.progress = 90
                    db.commit()
                    self.update_state(
                        state='PROGRESS',
                        meta={'current': 90, 'total': 100, 'status': 'AI işlemleri tamamlanıyor...'}
                    )
                    
                    enhancement_result = loop.run_until_complete(
                        gemini.enhance_text(text_for_ai, language, include_summary=True, enable_web_search=False)
                    )
                    
                    # 🔧 FIX: Check if enhancement actually failed (error in result)
                    if enhancement_result.get("error") or enhancement_result.get("safety_blocked"):
                        # Enhancement failed, treat as error
                        error_msg = enhancement_result.get("error", "Safety blocked by AI provider")
                        raise Exception(f"Enhancement failed: {error_msg}")
                    
                    transcription.enhanced_text = enhancement_result["enhanced_text"]
                    transcription.summary = enhancement_result.get("summary", "")
                    transcription.web_context_enrichment = web_context_enrichment  # NEW FIELD
                    transcription.gemini_status = "completed"
                    transcription.gemini_improvements = enhancement_result.get("improvements", [])
                    transcription.gemini_metadata = {
                        "original_length": enhancement_result.get("original_length"),
                        "enhanced_length": enhancement_result.get("enhanced_length"),
                        "word_count": enhancement_result.get("word_count"),
                        "processing_mode": "standard_upload",
                        "provider": enhancement_result.get("provider", "unknown"),  # "openai" or "gemini"
                        "model_used": enhancement_result.get("model_used", ""),
                        **web_metadata  # Include web search metadata
                    }
                    transcription.progress = 95
                    db.commit()
                    logger.info(f"✅ Standard text enhancement completed using {enhancement_result.get('provider', 'unknown').upper()}")
                    
                else:
                    transcription.gemini_status = "disabled"
                    logger.warning("⚠️ Gemini service not available (API key not configured)")
                
                # 💰 DEDUCT CREDITS - Only after successful enhancement
                # Moved inside try block to prevent charging on errors
                if transcription.gemini_status == "completed":
                    try:
                        credit_service = get_credit_service(db)
                        # Get model key AND provider from transcription (set during upload)
                        ai_model_key = transcription.ai_model or "gemini-2.5-flash"
                        ai_provider_key = transcription.ai_provider or "gemini"
                        
                        # 🆕 CHARACTER-BASED PRICING for ALL PROVIDERS
                        # All providers (Gemini, OpenAI, Together AI, Groq) now use cost_per_1k_chars
                        original_text = transcription.text or ""
                        ai_enhancement_cost = credit_service.calculate_text_based_cost(
                            text=original_text,
                            model_key=ai_model_key,
                            provider=ai_provider_key
                        )
                        logger.info(f"📝 Character-based pricing ({ai_provider_key.upper()}): {len(original_text)} chars → {ai_enhancement_cost} credits")
                        
                        credit_service.deduct_credits(
                            user_id=transcription.user_id,
                            amount=ai_enhancement_cost,
                            operation_type=OperationType.AI_ENHANCEMENT,
                            description=f"AI Enhancement: {transcription.original_filename}",
                            transcription_id=transcription.id,
                            metadata={
                                "provider": enhancement_result.get("provider", "unknown"),
                                "model_used": enhancement_result.get("model_used", ""),
                                "model_key": ai_model_key,
                                "original_length": enhancement_result.get("original_length"),
                                "enhanced_length": enhancement_result.get("enhanced_length"),
                                "web_search_enabled": transcription.enable_web_search,
                                "web_context_added": bool(web_context_enrichment),
                                "pricing_type": "character_based",
                                "character_count": len(transcription.text or "")
                            }
                        )
                        logger.info(f"💰 {ai_enhancement_cost} credits deducted for AI enhancement (model: {ai_model_key}, provider: {ai_provider_key})")
                    except Exception as credit_error:
                        logger.error(f"❌ AI enhancement credit deduction failed: {credit_error}")
                        # Don't fail the operation - enhancement already completed
                    
            except Exception as gemini_error:
                # 🔧 FIX 5: Enhanced error logging
                logger.error(f"❌ AI enhancement failed: {gemini_error}")
                logger.error(f"   Provider: {ai_provider}")
                logger.error(f"   Model: {ai_model}")
                logger.error(f"   Error type: {type(gemini_error).__name__}")
                
                # 🔧 FIX 6: Extract error code if available
                error_code = "unknown"
                error_str = str(gemini_error)
                if hasattr(gemini_error, "status_code"):
                    error_code = str(gemini_error.status_code)
                elif "404" in error_str:
                    error_code = "404"
                elif "422" in error_str:
                    error_code = "422"
                elif "401" in error_str or "authentication" in error_str.lower():
                    error_code = "401"
                elif "rate_limit" in error_str.lower() or "429" in error_str:
                    error_code = "429"
                
                logger.error(f"   Error code: {error_code}")
                
                # 🔧 FIX 7: Update transcription with error details
                transcription.gemini_status = "failed"
                transcription.enhanced_text = transcription.cleaned_text  # Fallback to cleaned text
                
                # User-friendly error message with fallback info
                model_display_name = ai_model if ai_model else "selected AI model"
                if error_code == "404":
                    transcription.summary = (
                        f"⚠️ AI model '{model_display_name}' is not available. "
                        f"Text has been cleaned with standard AI processing. No credits charged for AI enhancement."
                    )
                elif error_code == "422":
                    transcription.summary = (
                        f"⚠️ Text too long for model '{model_display_name}'. "
                        f"Text has been cleaned with standard AI processing. No credits charged for AI enhancement."
                    )
                elif error_code == "401":
                    transcription.summary = (
                        f"⚠️ API authentication failed for '{model_display_name}'. "
                        f"Text has been cleaned with standard AI processing. No credits charged for AI enhancement."
                    )
                elif error_code == "429":
                    transcription.summary = (
                        f"⚠️ Rate limit exceeded for '{model_display_name}'. "
                        f"Text has been cleaned with standard AI processing. No credits charged for AI enhancement."
                    )
                else:
                    transcription.summary = (
                        f"⚠️ AI enhancement with '{model_display_name}' failed. "
                        f"Text has been cleaned with standard AI processing. No credits charged for AI enhancement."
                    )
                
                # Don't overwrite existing error_message
                if not transcription.error_message:
                    transcription.error_message = f"AI Enhancement error: {error_str[:500]}"
                
                db.commit()
                logger.warning(f"⚠️ Falling back to cleaned text (no enhancement applied)")
                # Don't fail the whole task, just skip enhancement
        
        # ============================================================================
        # CREDIT DEDUCTION - Charge based on actual duration
        # ============================================================================
        try:
            credit_service = get_credit_service(db)
            actual_duration = transcription.duration or 60  # Fallback to 1 minute if not set
            
            # Calculate actual cost based on real duration using service's pricing instance
            credit_cost = credit_service.pricing.calculate_transcription_cost(
                duration_seconds=actual_duration,
                enable_diarization=transcription.enable_diarization,
                is_youtube=False,  # Will be True for YouTube endpoint
                transcription_provider=transcription.transcription_provider or "openai_whisper"
            )
            
            # Deduct base transcription credits
            credit_service.deduct_credits(
                user_id=transcription.user_id,
                amount=credit_cost,
                operation_type=OperationType.TRANSCRIPTION,
                description=f"Transcription: {transcription.original_filename} ({int(actual_duration/60)}min)",
                transcription_id=transcription.id,
                metadata={
                    "duration_seconds": actual_duration,
                    "whisper_model": transcription.whisper_model,
                    "speaker_recognition": transcription.use_speaker_recognition,
                    "speaker_count": result.get("speaker_count", 0)
                }
            )
            
            logger.info(
                f"💰 Credits deducted: user={transcription.user_id}, "
                f"amount={credit_cost}, duration={int(actual_duration/60)}min"
            )
            
            # 🎯 NEW: Deduct AssemblyAI Speech Understanding credits (if enabled)
            # Use language-aware pricing
            assemblyai_features = transcription.assemblyai_features_enabled or {}
            if assemblyai_features.get('speech_understanding') and transcription.transcription_provider == "assemblyai":
                # Get config from stored features
                config_dict = assemblyai_features.get('speech_understanding', {})
                detected_language = transcription.language or 'unknown'
                
                # Calculate cost based on language and enabled features
                # English variants (en, en_au, en_uk, en_us): Full features
                # Other languages: Only Entity Detection (0.03/60 cr/min)
                english_variants = {'en', 'en_au', 'en_uk', 'en_us'}
                is_english = detected_language in english_variants
                
                # Base cost (transcription + diarization)
                base_cost = 1.2 * (actual_duration / 60)
                # 🎯 NEW PRICING: Each feature = 0.3 cr/min (Total 1.2 cr/min for all 4 features)
                # - English: All 4 features = 4 × 0.3 = 1.2 cr/min
                # - Other languages: Only Entity Detection = 1 × 0.3 = 0.3 cr/min
                FEATURE_COST_PER_MIN = 0.3  # Each feature costs 0.3 credits per minute
                
                extra_cost = 0.0
                charged_features = []
                
                # Language-specific features
                if config_dict.get('sentiment_analysis') and is_english:
                    extra_cost += FEATURE_COST_PER_MIN * (actual_duration / 60)
                    charged_features.append("Sentiment Analysis (0.3 cr/min)")
                
                if config_dict.get('auto_chapters') and is_english:
                    extra_cost += FEATURE_COST_PER_MIN * (actual_duration / 60)
                    charged_features.append("Auto Chapters (0.3 cr/min)")
                
                if config_dict.get('entity_detection'):
                    extra_cost += FEATURE_COST_PER_MIN * (actual_duration / 60)
                    charged_features.append("Entity Detection (0.3 cr/min)")
                
                if config_dict.get('auto_highlights') and is_english:
                    extra_cost += FEATURE_COST_PER_MIN * (actual_duration / 60)
                    charged_features.append("Auto Highlights (0.3 cr/min)")
                
                speech_understanding_cost = extra_cost
                
                logger.info(f"💰 Speech Understanding cost breakdown:")
                logger.info(f"   Language: {detected_language} (English: {is_english})")
                logger.info(f"   Features charged: {', '.join(charged_features) if charged_features else 'None'}")
                logger.info(f"   Total: {speech_understanding_cost:.2f} cr")
                
                if speech_understanding_cost > 0:
                    credit_service.deduct_credits(
                        user_id=transcription.user_id,
                        amount=speech_understanding_cost,
                        operation_type=OperationType.TRANSCRIPTION,
                        description=f"AssemblyAI Speech Understanding: {transcription.original_filename}",
                        transcription_id=transcription.id,
                        metadata={
                            "feature": "speech_understanding",
                            "duration_minutes": actual_duration / 60,
                            "language": detected_language,
                            "is_english": is_english,
                            "features_charged": {
                                "sentiment": config_dict.get('sentiment_analysis') and is_english,
                                "chapters": config_dict.get('auto_chapters') and is_english,
                                "entity": config_dict.get('entity_detection'),
                                "key_phrases": config_dict.get('auto_highlights') and is_english
                            }
                        }
                    )
                    logger.info(f"💰 Speech Understanding credits deducted: {speech_understanding_cost:.2f} (language: {detected_language}, english: {is_english})")
                else:
                    logger.info(f"⏭️ No Speech Understanding credits charged (no features enabled or non-English language)")
            
            # 🤖 NEW: Deduct AssemblyAI LLM Gateway credits (if enabled)
            # Check both new format (llm_gateway) and old format (lemur.enabled)
            llm_gateway_enabled = (
                assemblyai_features.get('llm_gateway', {}).get('enabled', False) or
                assemblyai_features.get('lemur', {}).get('enabled', False)
            )
            
            if llm_gateway_enabled and transcription.transcription_provider == "assemblyai":
                llm_gateway_cost = credit_service.pricing.ASSEMBLYAI_LLM_GATEWAY
                credit_service.deduct_credits(
                    user_id=transcription.user_id,
                    amount=llm_gateway_cost,
                    operation_type=OperationType.TRANSCRIPTION,
                    description=f"AssemblyAI LLM Gateway: {transcription.original_filename}",
                    transcription_id=transcription.id,
                    metadata={
                        "feature": "llm_gateway",
                        "fixed_cost": llm_gateway_cost
                    }
                )
                logger.info(f"💰 LLM Gateway credits deducted: {llm_gateway_cost}")
        except Exception as credit_error:
            logger.error(f"❌ Credit deduction failed: {credit_error}", exc_info=True)
            # Don't fail the task - transcription already completed
            transcription.error_message = f"Credit deduction failed: {str(credit_error)}"
        
        # Mark as completed
        transcription.status = TranscriptionStatus.COMPLETED
        transcription.progress = 100
        transcription.completed_at = datetime.utcnow()
        # Clear error message only if there was no gemini error
        if transcription.gemini_status != "failed":
            transcription.error_message = None
        
        db.commit()
        db.refresh(transcription)
        
        logger.info(f"✅ Transcription {transcription_id} completed in {processing_time:.2f}s")
        
        # Update progress: 100%
        self.update_state(
            state='SUCCESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Completed',
                'result': {
                    'id': transcription.id,
                    'text_length': len(result["text"]),
                    'language': result["language"],
                    'speaker_count': result.get("speaker_count", 0),
                    'processing_time': processing_time
                }
            }
        )
        
        # ============================================================================
        # VISION PROCESSING - If document is attached, trigger Vision task
        # ============================================================================
        if transcription.has_document and transcription.document_file_id:
            logger.info(f"📄 Document attached, triggering Vision processing...")
            try:
                # Queue Vision task
                vision_task = process_vision_task.delay(transcription_id)
                logger.info(f"🖼️ Vision task queued: {vision_task.id}")
            except Exception as vision_error:
                logger.warning(f"⚠️ Vision task dispatch failed: {vision_error}")
                # Don't fail the main task - transcription is already complete
        
        return {
            'status': 'success',
            'transcription_id': transcription_id,
            'processing_time': processing_time,
            'text_length': len(result["text"]),
            'speaker_count': result.get("speaker_count", 0),
            'has_document': transcription.has_document
        }
        
    except FileNotFoundError as e:
        logger.error(f"❌ File not found - marking as FAILED: {e}")
        
        # Update transcription status to failed (no retry for missing files)
        try:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()
            
            if transcription:
                transcription.status = TranscriptionStatus.FAILED
                transcription.error_message = f"File not found: {str(e)}. The uploaded file may have been deleted or is missing from storage."
                transcription.completed_at = datetime.utcnow()
                transcription.file_id = None  # Clear file reference
                transcription.file_path = None
                db.commit()
                logger.info(f"✅ Transcription #{transcription_id} marked as FAILED (file missing)")
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")
        
        # DON'T re-raise - prevent retry for missing files
        return {
            'status': 'failed',
            'transcription_id': transcription_id,
            'error': f"File not found: {str(e)}"
        }
    
    except SoftTimeLimitExceeded:
        logger.error(f"⚠️ SOFT TIMEOUT: Task exceeded 14 minutes - Transcription #{transcription_id}")
        
        # Refund credits before marking as failed
        try:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()
            
            if transcription and transcription.user_id:
                # Refund credits
                credit_service = CreditService(db)
                if transcription.cost_credits and transcription.cost_credits > 0:
                    credit_service.refund_credits(
                        user_id=transcription.user_id,
                        amount=transcription.cost_credits,
                        description=f"Refund for timeout on transcription #{transcription_id}",
                        transcription_id=transcription_id
                    )
                    logger.info(f"💰 Refunded {transcription.cost_credits} credits to user {transcription.user_id}")
                
                transcription.status = TranscriptionStatus.FAILED
                transcription.error_message = "Processing timeout: Task exceeded 14 minutes. This may indicate Modal GPU hanging. Credits have been refunded."
                transcription.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"✅ Transcription #{transcription_id} marked as FAILED (timeout)")
        except Exception as db_error:
            logger.error(f"Failed to handle timeout: {db_error}")
        
        # DON'T re-raise - prevent retry
        return {
            'status': 'failed',
            'transcription_id': transcription_id,
            'error': 'Task timeout - Credits refunded'
        }
        
    except Exception as e:
        logger.error(f"❌ Transcription task failed: {e}", exc_info=True)
        
        # Update transcription status to failed
        try:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()
            
            if transcription:
                transcription.status = TranscriptionStatus.FAILED
                transcription.error_message = str(e)
                transcription.completed_at = datetime.utcnow()
                transcription.retry_count = self.request.retries
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")
        
        # Re-raise for Celery retry logic (don't delete file on retry)
        raise
        
    finally:
        # Cleanup: Only delete file if task completed successfully (not on retry)
        # Check if we're NOT retrying by checking the current task state
        try:
            task_state = self.request.retries if hasattr(self, 'request') else 0
            max_retries = self.max_retries
            
            # Only delete file if:
            # 1. Task succeeded, OR
            # 2. Task failed permanently (exhausted all retries)
            should_delete = False
            
            if 'transcription' in locals() and transcription:
                # Delete if completed successfully
                if transcription.status in ['COMPLETED', 'FAILED']:
                    should_delete = True
            
            # Also delete if we've exhausted all retries
            if task_state >= max_retries:
                should_delete = True
            
            if should_delete and 'file_path' in locals() and file_path and file_path.exists():
                logger.info(f"🗑️ Deleting uploaded file: {file_path}")
                os.remove(file_path)
                logger.info("✅ File deleted successfully")
            elif 'file_path' in locals() and file_path and file_path.exists():
                logger.info(f"⏸️ Keeping file for potential retry (attempt {task_state + 1}/{max_retries + 1})")
        except Exception as cleanup_error:
            logger.warning(f"⚠️ Failed to handle file cleanup: {cleanup_error}")
        
        db.close()


# =============================================================================
# IMAGE GENERATION TASK
# =============================================================================

@celery_app.task(
    name="app.workers.generate_transcript_images",
    bind=True,
    max_retries=2,
    default_retry_delay=60
)
def generate_transcript_images(
    self,
    transcription_id: int,
    user_id: int,
    num_images: int = 1,
    style: str = "professional",
    model_type: str = "sdxl",
    custom_prompt: str = None,
    custom_instructions: str = None,
    seed: int = None
):
    """
    Background task: Transkript'ten görsel oluştur
    
    Args:
        transcription_id: Transcription ID
        user_id: User ID
        num_images: Number of images (1-4)
        style: Image style
        model_type: Model (sdxl/flux)
        custom_prompt: Custom Stable Diffusion prompt
        custom_instructions: Custom instructions for prompt generation
        seed: Random seed
    """
    logger.info("=" * 80)
    logger.info(f"🎨 IMAGE GENERATION TASK START")
    logger.info(f"   Transcription ID: {transcription_id}")
    logger.info(f"   User ID: {user_id}")
    logger.info(f"   Num Images: {num_images}")
    logger.info(f"   Style: {style}")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        # 1. Get transcription
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id,
            Transcription.user_id == user_id
        ).first()
        
        if not transcription:
            logger.error(f"❌ Transcription {transcription_id} not found or access denied")
            return {
                "status": "error",
                "message": "Transcription not found"
            }
        
        if not transcription.text:
            logger.error(f"❌ Transcription {transcription_id} has no text")
            return {
                "status": "error",
                "message": "Transcription text is empty"
            }
        
        logger.info(f"✅ Found transcription: {transcription.filename}")
        
        # 2. Generate images
        from app.services.image_generator import get_image_generator
        
        image_gen = get_image_generator()
        
        result = image_gen.generate_images_from_transcript_sync(
            transcript_text=transcription.text,
            num_images=num_images,
            style=style,
            model_type=model_type,
            custom_prompt=custom_prompt,
            custom_instructions=custom_instructions,
            seed=seed
        )
        
        logger.info(f"✅ Generated {len(result['images'])} image(s)")
        
        # Filter out None/failed images
        valid_images = [img for img in result["images"] if img is not None]
        if not valid_images:
            logger.error("❌ All images failed to generate")
            return {
                "status": "error",
                "message": "All images failed to generate. Prompt may have been rejected.",
                "transcription_id": transcription_id
            }
        
        logger.info(f"✅ {len(valid_images)}/{len(result['images'])} images valid")
        
        # 3. Upload to MinIO
        from app.services.storage import get_storage_service
        from app.models.generated_image import GeneratedImage
        import time
        
        storage = get_storage_service()
        image_urls = []
        
        # ✅ Her görsel için UNIQUE timestamp (cache busting için)
        base_timestamp = int(time.time())
        
        for i, image_bytes in enumerate(valid_images):
            # Her görsel için farklı timestamp: base + i
            unique_timestamp = base_timestamp + i
            filename = f"generated_{transcription_id}_{unique_timestamp}_{i}_{style}.png"
            
            logger.info(f"📤 Uploading image {i+1}/{len(valid_images)}: {filename}")
            
            url = storage.upload_file_bytes(
                file_bytes=image_bytes,
                filename=filename,
                content_type="image/png"
            )
            
            # 4. Save to database
            generated_image = GeneratedImage(
                transcription_id=transcription_id,
                user_id=user_id,
                prompt=result["prompt"],
                style=style,
                seed=seed,
                image_url=url,
                filename=filename,
                file_size=len(image_bytes)
            )
            db.add(generated_image)
            image_urls.append(url)
            
            logger.info(f"✅ Image {i+1} uploaded: {url}")
        
        db.commit()
        
        # 5. Kredi düş - Her görsel için 1 kredi
        from app.services.credit_service import get_credit_service
        
        try:
            credits_service = get_credit_service(db)
            # Model-based credit pricing: SDXL=1, FLUX=2, IMAGEN=4 per image
            credit_multipliers = {
                "sdxl": 1.0,
                "flux": 2.0,
                "imagen": 4.0
            }
            model_lower = model_type.lower()
            credit_per_image = credit_multipliers.get(model_lower, 1.0)
            required_credits = float(num_images) * credit_per_image
            
            credits_service.deduct_credits(
                user_id=user_id,
                amount=required_credits,
                operation_type=OperationType.IMAGE_GENERATION,
                description=f"Generated {num_images} image(s) with {model_type.upper()} - {style} style ({credit_per_image} credits/image)",
                transcription_id=transcription_id,
                metadata={
                    "num_images": num_images,
                    "model_type": model_type,
                    "credit_per_image": credit_per_image,
                    "style": style,
                    "prompt_length": len(result["prompt"]),
                    "seed": seed,
                    "background": True
                }
            )
            logger.info(f"💰 Deducted {required_credits} credits from user {user_id}")
        except Exception as credit_error:
            logger.error(f"❌ Failed to deduct credits: {credit_error}")
            # Don't fail the task - images are already generated
        
        logger.info("=" * 80)
        logger.info(f"✅ IMAGE GENERATION COMPLETE")
        logger.info(f"   Generated: {len(image_urls)} image(s)")
        logger.info(f"   Prompt: {result['prompt'][:100]}...")
        logger.info("=" * 80)
        
        return {
            "status": "success",
            "transcription_id": transcription_id,
            "images": image_urls,
            "count": len(image_urls),
            "prompt": result["prompt"]
        }
        
    except Exception as e:
        logger.error(f"❌ Image generation task error: {e}", exc_info=True)
        db.rollback()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)
        
        logger.error(f"❌ Max retries reached, task failed permanently")
        
        return {
            "status": "error",
            "message": str(e),
            "transcription_id": transcription_id
        }
        
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1, default_retry_delay=120, queue='high')
def generate_video_task(
    self,
    video_id: int,
    transcription_id: int,
    user_id: int,
    style: str = "professional",
    model_type: str = "sdxl",
    voice: str = "alloy",
    custom_prompt: str = None
):
    """
    Background task for video generation from transcript
    
    Pipeline:
    1. Segment transcript → Gemini 2.5 Pro (or use custom_prompt)
    2. Generate images → Modal SDXL/FLUX
    3. Generate speech → OpenAI TTS
    4. Assemble video → FFmpeg
    5. Upload to MinIO
    """
    db = SessionLocal()
    
    try:
        logger.info(f"🎬 VIDEO GENERATION TASK START: video_id={video_id}")
        
        # 1. Get video and transcription records
        from app.models.generated_video import GeneratedVideo
        from app.models.user import User
        
        video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
        if not video:
            raise ValueError(f"Video record not found: {video_id}")
        
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        if not transcription:
            raise ValueError(f"Transcription not found: {transcription_id}")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        # 2. Import services
        from app.services.video_generator import get_video_generator_service
        from app.services.video_assembly import get_video_assembly_service
        from app.services.image_generator import get_image_generator
        from app.services.storage import get_storage_service
        from app.services.credit_service import get_credit_service
        import tempfile
        from pathlib import Path
        import math
        
        video_gen = get_video_generator_service()
        video_asm = get_video_assembly_service()
        image_gen = get_image_generator()
        storage = get_storage_service()
        credits_service = get_credit_service(db)
        
        # Check FFmpeg
        if not video_asm.check_ffmpeg_installed():
            raise RuntimeError("FFmpeg not installed")
        
        # 2.5. CREDIT CHECK - BEFORE PROCESSING!
        logger.info("💰 Checking credits before video generation...")
        
        # Estimate segment count
        if custom_prompt and len(custom_prompt.strip()) > 0:
            words = len(custom_prompt.strip().split())
            estimated_segments = math.ceil(words / 150)  # 150 words per segment
            logger.info(f"📊 Custom prompt: {words} words → ~{estimated_segments} segments")
        else:
            words = len(transcription.text.split())
            estimated_segments = math.ceil(words / 150)
            estimated_segments = max(1, min(estimated_segments, 20))  # Cap between 1-20
            logger.info(f"📊 Transcript: {words} words → ~{estimated_segments} segments")
        
        # Calculate required credits
        model_lower = model_type.lower()
        credit_multipliers = {
            "sdxl": 1.0,
            "flux": 2.0,
            "imagen": 4.0
        }
        image_credit_per_segment = credit_multipliers.get(model_lower, 1.0)
        estimated_cost = image_credit_per_segment * estimated_segments * 2  # ×2 for image+audio
        
        logger.info(f"💵 Estimated cost: {image_credit_per_segment} cr/img × {estimated_segments} segments × 2 = {estimated_cost} credits")
        logger.info(f"💰 User balance: {user.credits} credits")
        
        # Check if user has enough credits
        if user.credits < estimated_cost:
            error_msg = f"Insufficient credits. Required: {estimated_cost}, Available: {user.credits}"
            logger.error(f"❌ {error_msg}")
            video.status = "failed"
            video.error_message = error_msg
            db.commit()
            raise InsufficientCreditsError(error_msg)
        
        logger.info(f"✅ Credit check passed: {user.credits} >= {estimated_cost}")
        
        # 3. Segment transcript or use custom prompt
        logger.info("📝 Segmenting transcript or processing custom prompt...")
        video.status = "processing"
        video.progress = 5
        db.commit()
        
        # If custom_prompt provided, use it instead of transcript
        if custom_prompt and len(custom_prompt.strip()) > 0:
            logger.info(f"🎨 Using CUSTOM PROMPT for video: {custom_prompt[:100]}...")
            logger.info(f"📊 Custom prompt length: {len(custom_prompt)} characters")
            
            # Split custom prompt into ~60 second segments for TTS
            # Average speaking rate: ~150 words per minute = ~2.5 words per second
            # So ~150 words = 60 seconds
            words = custom_prompt.strip().split()
            words_per_segment = 150  # ~60 seconds of speech
            
            segments = []
            for i in range(0, len(words), words_per_segment):
                segment_words = words[i:i + words_per_segment]
                segment_text = ' '.join(segment_words)
                
                # DEBUG: Log first segment text
                if i == 0:
                    logger.info(f"🔍 First segment text (first 200 chars): {segment_text[:200]}...")
                
                segments.append({
                    "text": segment_text,  # This will be used for TTS
                    "visual_description": segment_text,  # This will be used for image generation
                    "start_time": i / 2.5,  # Estimated time based on word count
                    "end_time": (i + len(segment_words)) / 2.5,
                    "duration": len(segment_words) / 2.5
                })
            
            logger.info(f"✅ Split custom prompt into {len(segments)} segments (~{words_per_segment} words each)")
            logger.info(f"📝 Total words in custom prompt: {len(words)}")
        else:
            # Use transcript and segment it with AI
            logger.info("📝 Using transcript with AI segmentation...")
            segments = video_gen.segment_transcript_for_video(
                transcript_text=transcription.text,
                target_duration_seconds=60
            )
        
        logger.info(f"✅ Created {len(segments)} segments")
        video.progress = 15
        db.commit()
        
        # 4. BATCH IMAGE GENERATION - Use Modal batch API for speed + quality!
        model_name = model_type.upper()
        logger.info(f"🎨 Generating {len(segments)} HIGH QUALITY images using {model_name}...")
        
        import time as time_module
        from typing import List
        
        # Prepare all prompts and seeds
        all_prompts = []
        all_seeds = []
        for idx, segment in enumerate(segments):
            image_prompt = segment.get("visual_description", segment["text"][:500])
            all_prompts.append(image_prompt)
            all_seeds.append(hash(segment["text"]) % 1000000)
        
        # Try batch generation with retry
        max_retries = 2
        segment_images = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🚀 Batch generating {len(all_prompts)} images with {model_name} (attempt {attempt + 1}/{max_retries})...")
                
                # Use appropriate model service - ALL support batch now!
                if model_type.lower() == "flux":
                    # FLUX: Use batch API on H100 (optimized for throughput)
                    logger.info(f"   Using FLUX batch API on H100...")
                    segment_images = image_gen.modal_flux.generate_batch_sync(
                        prompts=all_prompts,
                        seeds=all_seeds
                    )
                elif model_type.lower() == "imagen":
                    # IMAGEN: Use Replicate Imagen-4 (photorealistic, cinematic)
                    logger.info(f"   Using Replicate Imagen-4 (photorealistic)...")
                    segment_images = image_gen.replicate_imagen.generate_batch_sync(
                        prompts=all_prompts,
                        seeds=all_seeds,
                        aspect_ratio="16:9"  # Video format
                    )
                else:
                    # SDXL: Use batch API on A10G
                    segment_images = image_gen.modal_sd.generate_batch_sync(
                        prompts=all_prompts,
                        seeds=all_seeds,
                        high_quality=True  # 50 steps for high quality!
                    )
                
                logger.info(f"✅ Batch generation complete! {len(segment_images)} images generated")
                
                # Update progress incrementally as if images came in one by one (for UX)
                for i in range(len(segment_images)):
                    image_progress = 15 + int(((i + 1) / len(segments)) * 40)
                    video.progress = image_progress
                    db.commit()
                    if i < len(segment_images) - 1:
                        time_module.sleep(0.5)  # Small delay for progress animation
                
                break  # Success!
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 30
                    logger.warning(f"⚠️ Batch generation failed (attempt {attempt+1}/{max_retries}), retrying in {wait_time}s...")
                    logger.warning(f"   Error: {e}")
                    time_module.sleep(wait_time)
                else:
                    logger.error(f"❌ Batch generation failed after {max_retries} attempts: {e}")
                    raise
        
        if not segment_images or len(segment_images) != len(segments):
            raise ValueError(f"Batch generation returned {len(segment_images) if segment_images else 0} images, expected {len(segments)}")
        
        logger.info(f"✅ All {len(segments)} HIGH QUALITY images generated!")
        video.progress = 55
        db.commit()
        
        # 5. PARALLEL TTS GENERATION (OPTIMIZATION)
        logger.info(f"🎤 Generating {len(segments)} speech files in parallel...")
        
        # DEBUG: Log first segment text that will be sent to TTS
        if len(segments) > 0:
            first_text = segments[0].get("text", "")
            logger.info(f"🔍 TTS will process first segment text (first 200 chars): {first_text[:200]}...")
        
        video.progress = 60
        db.commit()
        
        audio_bytes_list = video_gen.generate_speech_batch(
            segments=segments,
            voice=voice,
            model="tts-1",
            max_workers=5  # 5 concurrent TTS requests
        )
        
        logger.info(f"✅ All {len(audio_bytes_list)} speech files generated!")
        video.progress = 70
        db.commit()
        
        # 6. PARALLEL VIDEO SEGMENT CREATION (OPTIMIZATION)
        logger.info(f"🎬 Creating {len(segments)} video segments in parallel...")
        
        temp_dir = Path(tempfile.gettempdir()) / f"video_{video_id}"
        temp_dir.mkdir(exist_ok=True)
        
        # Prepare batch data for parallel processing
        segments_batch_data = []
        for idx, (segment, image_bytes, audio_bytes) in enumerate(zip(segments, segment_images, audio_bytes_list)):
            if audio_bytes is None:
                logger.warning(f"⚠️ Segment {idx+1} has no audio, skipping...")
                continue
            
            segments_batch_data.append({
                "image_bytes": image_bytes,
                "audio_bytes": audio_bytes,
                "output_path": str(temp_dir / f"segment_{idx:03d}.mp4"),
                "segment_num": idx + 1,
                "text": segment["text"]
            })
        
        # Process all segments in parallel (4 workers = 4 concurrent FFmpeg processes)
        segment_results = video_asm.create_video_segment_batch(
            segments_data=segments_batch_data,
            max_workers=4  # 4 concurrent video encoding processes
        )
        
        logger.info(f"✅ All video segments created!")
        video.progress = 85
        db.commit()
        
        # Collect successful segments
        segment_data = []
        temp_video_segments = []
        
        for result in segment_results:
            if result["status"] == "success":
                temp_video_segments.append(result["output_path"])
                segment_data.append({
                    "segment_num": result["segment_num"],
                    "text": result["text"],
                    "duration": result["duration"],
                    "visual_description": segments[result["segment_num"]-1].get("visual_description", "")
                })
            else:
                logger.error(f"❌ Segment {result['segment_num']} failed: {result.get('error', 'Unknown error')}")
                segment_data.append({
                    "segment_num": result["segment_num"],
                    "text": result["text"],
                    "error": result.get("error", "Unknown error")
                })
        
        # 7. Concatenate all video segments
        logger.info(f"🎬 Concatenating {len(temp_video_segments)} video segments...")
        video.progress = 90
        db.commit()
        
        if not temp_video_segments:
            raise RuntimeError("No video segments were created")
        
        final_video_path = str(temp_dir / "final_video.mp4")
        video_asm.concatenate_videos(
            video_paths=temp_video_segments,
            output_path=final_video_path
        )
        
        total_duration = video_asm.get_video_duration(final_video_path)
        logger.info(f"✅ Final video created: {total_duration:.1f}s")
        
        # 6. Upload to MinIO
        logger.info("📤 Uploading video to storage...")
        video.progress = 90
        db.commit()
        
        with open(final_video_path, "rb") as f:
            video_bytes = f.read()
        
        video_url = storage.upload_file_bytes(
            file_bytes=video_bytes,
            filename=video.filename,
            content_type="video/mp4"
        )
        
        logger.info(f"✅ Video uploaded: {video.filename}")
        
        # 7. Update database
        video.url = video_url
        video.duration = total_duration
        video.status = "completed"
        video.progress = 100
        video.segments = segment_data
        video.completed_at = datetime.utcnow()
        db.commit()
        
        # 8. Deduct credits (actual cost based on real segment count)
        logger.info("💰 Deducting credits based on actual segments used...")
        
        # Video formula: (image_credit × num_segments × 2) 
        # Why ×2? Video requires higher quality + TTS generation
        num_segments = len(segments)
        actual_cost = image_credit_per_segment * num_segments * 2
        
        logger.info(f"💵 Final cost: {image_credit_per_segment} cr/img × {num_segments} segments × 2 = {actual_cost} credits")
        
        # Deduct credits (this should succeed because we checked at the start)
        try:
            credits_service.deduct_credits(
                user_id=user_id,
                amount=actual_cost,
                operation_type=OperationType.VIDEO_GENERATION,
                description=f"Generated video with {model_type.upper()} - {num_segments} segments ({image_credit_per_segment}×{num_segments}×2 = {actual_cost} credits)",
                transcription_id=transcription_id,  # ✅ CRITICAL: Pass as parameter, not just metadata!
                metadata={
                    "video_id": video_id,
                    "transcription_id": transcription_id,
                    "segments": num_segments,
                    "model_type": model_type,
                    "image_credit_per_segment": image_credit_per_segment,
                    "duration": total_duration,
                    "style": style,
                    "voice": voice
                }
            )
            logger.info(f"✅ Deducted {actual_cost} credits from user {user_id}")
        except InsufficientCreditsError as e:
            # This should NOT happen because we checked at the start
            # But if segment count grew unexpectedly, handle it gracefully
            logger.error(f"❌ Credit deduction failed unexpectedly: {e}")
            logger.error(f"⚠️ Estimated {estimated_cost} but actual cost was {actual_cost}")
            video.status = "failed"
            video.error_message = f"Credit deduction failed: {str(e)}"
            db.commit()
            raise
        
        # 9. Cleanup temp files
        logger.info("🧹 Cleaning up temp files...")
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")
        
        logger.info(f"✅ VIDEO GENERATION COMPLETE: video_id={video_id}")
        
        return {
            "status": "success",
            "video_id": video_id,
            "duration": total_duration,
            "segments": len(segments),
            "url": video_url
        }
        
    except Exception as e:
        logger.error(f"❌ Video generation task error: {e}", exc_info=True)
        db.rollback()
        
        # Update video status
        try:
            video = db.query(GeneratedVideo).filter(GeneratedVideo.id == video_id).first()
            if video:
                video.status = "failed"
                video.error_message = str(e)
                db.commit()
        except:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)
        
        logger.error(f"❌ Max retries reached, video generation failed permanently")
        
        return {
            "status": "error",
            "message": str(e),
            "video_id": video_id
        }
        
    finally:
        db.close()


# ============================================================================
# VISION API TASK - Document Analysis (NotebookLM-style)
# ============================================================================

@celery_app.task(
    bind=True,
    base=TranscriptionTask,
    name="app.workers.process_vision",
    time_limit=600,  # 10 minutes hard timeout
    soft_time_limit=540,  # 9 minutes soft timeout
)
def process_vision_task(self, transcription_id: int) -> Dict[str, Any]:
    """
    Process document with Vision API (Gemini)
    
    This task handles:
    - PDF document analysis (multi-page)
    - Image analysis (OCR, content extraction)
    - Combined analysis with audio transcription
    
    Args:
        transcription_id: ID of transcription with document
        
    Returns:
        Result dictionary with status and data
    """
    # ProcessingMode and VisionStatus are now simple strings, no enum import needed
    from app.services.vision_service import get_vision_service
    import asyncio
    
    db: Session = SessionLocal()
    start_time = time.time()
    
    try:
        logger.info(f"🖼️ Starting Vision task: transcription_id={transcription_id}")
        
        # Get transcription
        transcription = db.query(Transcription).filter(
            Transcription.id == transcription_id
        ).first()
        
        if not transcription:
            raise ValueError(f"Transcription not found: {transcription_id}")
        
        if not transcription.has_document:
            logger.warning(f"⚠️ No document attached to transcription {transcription_id}")
            return {"status": "skipped", "reason": "No document attached"}
        
        # Update status (using string instead of enum)
        transcription.vision_status = "processing"
        db.commit()
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Loading document...'}
        )
        
        # Get document file
        storage = FileStorageService()
        doc_path = storage.get_file_path(transcription.document_file_id)
        
        if not doc_path or not doc_path.exists():
            raise FileNotFoundError(f"Document file not found: {transcription.document_file_id}")
        
        logger.info(f"📄 Processing document: {transcription.document_filename} ({doc_path})")
        
        # Read document content
        with open(doc_path, 'rb') as f:
            doc_data = f.read()
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': 'Analyzing document with Vision API...'}
        )
        
        # Initialize Vision service
        vision_service = get_vision_service(
            provider=transcription.vision_provider or "gemini",
            model=transcription.vision_model
        )
        
        # Analyze document
        doc_result = asyncio.run(vision_service.analyze_document(
            file_data=doc_data,
            content_type=transcription.document_content_type,
            filename=transcription.document_filename
        ))
        
        if "error" in doc_result:
            raise Exception(f"Vision API error: {doc_result['error']}")
        
        logger.info(f"✅ Document analyzed: {doc_result.get('page_count', 1)} pages")
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 60, 'total': 100, 'status': 'Processing results...'}
        )
        
        # Save document analysis results
        transcription.document_text = doc_result.get("extracted_text", "")
        transcription.document_summary = doc_result.get("summary", "")
        transcription.document_key_points = doc_result.get("key_points", [])
        transcription.document_topics = doc_result.get("topics", [])  # Add topics from Vision API
        transcription.document_analysis = doc_result
        transcription.document_metadata = {
            "page_count": doc_result.get("page_count", 1),
            "total_pages": doc_result.get("total_pages", 1),
            "language": doc_result.get("language", "unknown"),
            "document_type": doc_result.get("document_type", "unknown")
        }
        transcription.vision_processing_time = doc_result.get("processing_time", time.time() - start_time)
        transcription.vision_model = doc_result.get("model", transcription.vision_model)
        
        db.commit()
        
        # Check if combined analysis is needed
        # processing_mode is now a String, not enum
        if transcription.processing_mode == "combined" and transcription.text:
            self.update_state(
                state='PROGRESS',
                meta={'current': 70, 'total': 100, 'status': 'Creating combined analysis...'}
            )
            
            logger.info("🔗 Creating combined analysis (audio + document)...")
            
            # Get audio transcription text
            audio_text = transcription.text or transcription.cleaned_text or ""
            
            # Create combined analysis
            combined_result = asyncio.run(vision_service.create_combined_analysis(
                audio_text=audio_text,
                document_text=transcription.document_text,
                document_analysis=doc_result
            ))
            
            if "error" not in combined_result:
                transcription.combined_summary = combined_result.get("combined_summary", "")
                transcription.combined_insights = combined_result.get("key_insights", [])
                transcription.combined_analysis = combined_result
                transcription.combined_key_topics = combined_result.get("study_guide", {}).get("main_topics", [])
                
                logger.info("✅ Combined analysis created successfully")
            else:
                logger.warning(f"⚠️ Combined analysis failed: {combined_result.get('error')}")
        
        # Calculate and deduct credits
        self.update_state(
            state='PROGRESS',
            meta={'current': 90, 'total': 100, 'status': 'Finalizing...'}
        )
        
        credit_service = get_credit_service(db)
        page_count = doc_result.get("page_count", 1)
        
        # Calculate credit cost
        if transcription.document_content_type == "application/pdf":
            vision_credits = page_count * 0.5  # 0.5 credits per page
        else:
            vision_credits = 0.3  # Single image
        
        # Add combined analysis cost if applicable
        # processing_mode is now a String, not enum
        if transcription.processing_mode == "combined" and transcription.combined_analysis:
            vision_credits += 2.0  # Combined analysis cost
        
        # Deduct credits
        try:
            credit_service.deduct_credits(
                user_id=transcription.user_id,
                amount=vision_credits,
                operation_type=OperationType.AI_ENHANCEMENT,  # Use AI enhancement type for now
                description=f"Vision: {transcription.document_filename} ({page_count} pages)",
                transcription_id=transcription_id,
                metadata={
                    "vision_provider": transcription.vision_provider,
                    "page_count": page_count,
                    "processing_mode": transcription.processing_mode or "unknown"  # processing_mode is now a String, not enum
                }
            )
            logger.info(f"💰 Deducted {vision_credits} credits for Vision processing")
        except Exception as credit_error:
            logger.error(f"❌ Credit deduction failed: {credit_error}")
        
        # Update status to completed
        transcription.vision_status = "completed"
        
        # If this was document_only mode, also update main status
        if transcription.processing_mode == "document_only":
            transcription.status = TranscriptionStatus.COMPLETED
            transcription.completed_at = datetime.utcnow()
        
        db.commit()
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Vision task completed: transcription_id={transcription_id}, time={processing_time:.1f}s")
        
        return {
            "status": "success",
            "transcription_id": transcription_id,
            "page_count": page_count,
            "processing_time": processing_time,
            "has_combined_analysis": transcription.combined_analysis is not None
        }
        
    except SoftTimeLimitExceeded:
        logger.error(f"⏰ Vision task timed out: {transcription_id}")
        transcription.vision_status = "failed"
        transcription.vision_error = "Processing timed out"
        db.commit()
        raise
        
    except Exception as e:
        logger.error(f"❌ Vision task failed: {e}", exc_info=True)
        
        try:
            transcription = db.query(Transcription).filter(
                Transcription.id == transcription_id
            ).first()
            if transcription:
                transcription.vision_status = "failed"
                transcription.vision_error = str(e)
                db.commit()
        except:
            pass
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"🔄 Retrying vision task... (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)
        
        return {
            "status": "error",
            "message": str(e),
            "transcription_id": transcription_id
        }
        
    finally:
        db.close()

