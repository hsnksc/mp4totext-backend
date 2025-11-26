"""
Transcription API endpoints
File upload, transcription creation, status checking
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import json
import logging
import time
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus, SpeakerModelType, GeminiMode
from app.models.credit_transaction import OperationType
from app.schemas.transcription import (
    FileUploadResponse,
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionListResponse,
    CostEstimationRequest,
    CostEstimationResponse
)
from app.auth.utils import get_current_active_user
from app.services.storage import get_storage_service
from app.services.audio_processor import get_audio_processor
from app.services.credit_service import get_credit_service, CreditPricing, InsufficientCreditsError
from app.settings import get_settings
from app.websocket import get_ws_manager

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/transcriptions", tags=["Transcriptions"])

# Import Celery task (will be available after Celery is running)
try:
    from app.workers.transcription_worker import process_transcription_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("⚠️ Celery not available. Using synchronous processing.")


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage_service)
) -> FileUploadResponse:
    """
    Upload audio/video file
    
    - **file**: Audio or video file (MP3, MP4, WAV, etc.)
    
    Supported formats:
    - Audio: MP3, WAV, M4A, FLAC, OGG
    - Video: MP4, AVI, MOV, MKV, WEBM
    """
    # Validate file type
    allowed_types = [
        "audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a",
        "audio/flac", "audio/ogg", "audio/x-m4a",
        "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska",
        "video/webm", "application/octet-stream"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Supported: MP3, MP4, WAV, M4A, FLAC, OGG, AVI, MOV, MKV, WEBM"
        )
    
    # Check file size (max 500MB)
    max_size = 500 * 1024 * 1024  # 500MB
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file_size / 1024 / 1024:.1f}MB. Max: 500MB"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    # Save file
    try:
        file_id, file_path = storage.save_file(file.file, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )
    
    return FileUploadResponse(
        file_id=file_id,
        filename=file.filename,
        file_size=file_size,
        content_type=file.content_type,
        message=f"File uploaded successfully: {file.filename}"
    )


@router.post("/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    file: UploadFile = File(...),
    whisper_model: str = Form("tiny"),
    transcription_provider: str = Form("openai_whisper"),  # "openai_whisper" or "assemblyai"
    enable_diarization: bool = Form(False),
    min_speakers: int | None = Form(None),
    max_speakers: int | None = Form(None),
    use_gemini_enhancement: bool = Form(False),
    ai_provider: str = Form("gemini"),  # "gemini" or "openai"
    ai_model: str | None = Form(None),  # AI model name (optional, uses default if not specified)
    gemini_mode: str = Form("text"),
    custom_prompt: str | None = Form(None),
    enable_web_search: bool = Form(False),  # Enable Tavily web search (optional)
    enable_assemblyai_speech_understanding: bool = Form(False),  # NEW: Enable AssemblyAI Speech Understanding
    enable_assemblyai_llm_gateway: bool = Form(False),  # NEW: Enable AssemblyAI LLM Gateway with LeMUR
    language: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage_service)
) -> TranscriptionResponse:
    """
    Create transcription job with direct file upload
    
    - **file**: Audio or video file
    - **whisper_model**: Whisper model size (tiny, base, small, medium, large)
    - **language**: Language code (tr, en, de, etc.) or null for auto-detect
    - **enable_diarization**: Enable speaker diarization with pyannote.audio 3.1
    - **min_speakers**: Minimum expected speakers (optional)
    - **max_speakers**: Maximum expected speakers (optional)
    - **use_gemini_enhancement**: Enhance text with AI
    - **ai_provider**: AI provider to use (gemini, openai) - default: gemini
    - **gemini_mode**: Processing mode (text, note, custom)
    - **custom_prompt**: Custom prompt (required if gemini_mode=custom)
    """
    # Validate file type
    allowed_types = [
        "audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/m4a",
        "audio/flac", "audio/ogg", "audio/x-m4a",
        "video/mp4", "video/x-msvideo", "video/quicktime", "video/x-matroska",
        "video/webm", "application/octet-stream"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    # Check file size (max 500MB)
    max_size = 500 * 1024 * 1024
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large: {file_size / 1024 / 1024:.1f}MB. Max: 500MB"
        )
    
    # Reset file pointer and save file
    await file.seek(0)
    try:
        file_id, file_path = storage.save_file(file.file, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )
    
    filename = file.filename
    
    # Validate gemini_mode
    from app.models.transcription import GeminiMode
    try:
        gemini_mode_enum = GeminiMode[gemini_mode.upper()]
    except KeyError:
        gemini_mode_enum = GeminiMode.TEXT
        logger.warning(f"Invalid gemini_mode: {gemini_mode}, using default: text")
    
    # Validate custom_prompt if gemini_mode is CUSTOM
    if gemini_mode_enum == GeminiMode.CUSTOM and not custom_prompt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom_prompt is required when gemini_mode is 'custom'"
        )
    
    # ============================================================================
    # CREDIT CHECK - Estimate cost before processing
    # ============================================================================
    credit_service = get_credit_service(db)
    
    # Estimate duration based on file size (rough estimate: 128kbps audio)
    # Audio: ~960 KB/min (128kbps), Video: ~7-15 MB/min
    is_video = file.content_type.startswith('video/')
    estimated_minutes = file_size / (10 * 1024 * 1024) if is_video else file_size / (960 * 1024)
    estimated_duration = max(1, int(estimated_minutes * 60))  # At least 1 second
    
    # Calculate required credits using service's pricing instance
    required_credits = credit_service.pricing.calculate_transcription_cost(
        duration_seconds=estimated_duration,
        enable_diarization=enable_diarization,
        is_youtube=False,
        transcription_provider=transcription_provider
    )
    
    # Add AssemblyAI Speech Understanding cost (per minute)
    if enable_assemblyai_speech_understanding and transcription_provider == "assemblyai":
        speech_understanding_cost = (estimated_duration / 60) * credit_service.pricing.ASSEMBLYAI_SPEECH_UNDERSTANDING_PER_MINUTE
        required_credits += speech_understanding_cost
        logger.info(f"💰 Adding Speech Understanding cost: {speech_understanding_cost:.2f} credits")
    
    # Add AssemblyAI LLM Gateway cost (fixed)
    if enable_assemblyai_llm_gateway and transcription_provider == "assemblyai":
        required_credits += credit_service.pricing.ASSEMBLYAI_LLM_GATEWAY
        logger.info(f"💰 Adding LLM Gateway cost: {credit_service.pricing.ASSEMBLYAI_LLM_GATEWAY} credits")
    
    # Check if user has enough credits
    user_balance = credit_service.get_balance(current_user.id)
    if user_balance < required_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Insufficient credits",
                "required": required_credits,
                "available": user_balance,
                "message": f"You need {required_credits} credits but only have {user_balance}. "
                           f"Estimated duration: {int(estimated_duration/60)} minutes."
            }
        )
    
    logger.info(
        f"💰 Credit check passed: user={current_user.id}, "
        f"required={required_credits}, balance={user_balance}, "
        f"estimated_duration={int(estimated_duration/60)}min"
    )
    
    # 🔍 DEBUG: Log all incoming parameters
    logger.info(f"=" * 80)
    logger.info(f"🎯 NEW TRANSCRIPTION REQUEST")
    logger.info(f"   User: {current_user.username} (ID: {current_user.id})")
    logger.info(f"   File: {file.filename}")
    logger.info(f"   Provider: {transcription_provider}")
    logger.info(f"   🔍 enable_assemblyai_speech_understanding: {enable_assemblyai_speech_understanding} (type: {type(enable_assemblyai_speech_understanding)})")
    logger.info(f"   🤖 enable_assemblyai_llm_gateway: {enable_assemblyai_llm_gateway} (type: {type(enable_assemblyai_llm_gateway)})")
    logger.info(f"=" * 80)
    
    # Create transcription job with proper AssemblyAI config
    assemblyai_features = {}
    if enable_assemblyai_speech_understanding:
        # Store detailed Speech Understanding config (will be populated by worker)
        assemblyai_features['speech_understanding'] = {
            'sentiment_analysis': True,
            'auto_chapters': True,
            'entity_detection': True,
            'auto_highlights': True,
            'speaker_labels': True  # Always enabled with diarization
        }
        logger.info(f"✅ Speech Understanding ENABLED - added to assemblyai_features")
    if enable_assemblyai_llm_gateway:
        assemblyai_features['llm_gateway'] = {
            'enabled': True,
            'generate_summary': True
        }
        logger.info(f"✅ LLM Gateway ENABLED - added to assemblyai_features")
    
    logger.info(f"📦 Final assemblyai_features dict: {assemblyai_features}")
    
    transcription = Transcription(
        user_id=current_user.id,
        file_id=file_id,
        filename=filename,
        original_filename=file.filename,
        file_size=file_size,
        file_path=str(file_path),
        content_type=file.content_type,
        language=language,
        whisper_model=whisper_model,
        transcription_provider=transcription_provider,  # "openai_whisper" or "assemblyai"
        enable_diarization=enable_diarization,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        use_gemini_enhancement=use_gemini_enhancement,
        ai_provider=ai_provider,  # "gemini" or "openai"
        ai_model=ai_model,  # Model name
        enable_web_search=enable_web_search,  # Enable Tavily web search
        assemblyai_features_enabled=assemblyai_features if assemblyai_features else None,  # NEW: Track enabled features
        gemini_mode=gemini_mode_enum,
        custom_prompt=custom_prompt,
        status=TranscriptionStatus.PENDING
    )
    
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    # Trigger Celery task for async processing (if available)
    if CELERY_AVAILABLE:
        try:
            task = process_transcription_task.delay(transcription.id)
            logger.info(
                "🚀 Celery task started: %s for transcription %s",
                task.id,
                transcription.id,
            )
        except Exception as celery_error:
            logger.error(
                "Celery dispatch failed for transcription %s: %s",
                transcription.id,
                celery_error,
                exc_info=True,
            )
            if settings.is_development:
                logger.warning(
                    "Falling back to synchronous processing for transcription %s",
                    transcription.id,
                )
                process_transcription_task.apply(args=(transcription.id,))
            else:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Background processing service unavailable. Please try again later.",
                )
    else:
        logger.warning(f"⚠️ Celery not available. Use POST /api/v1/transcriptions/{transcription.id}/process for sync processing")
    
    return transcription


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> TranscriptionResponse:
    """
    Get transcription by ID
    
    Returns transcription status and result
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # Parse JSON fields if they're strings (SQLite stores JSON as TEXT)
    if transcription.custom_prompt_history and isinstance(transcription.custom_prompt_history, str):
        import json
        try:
            transcription.custom_prompt_history = json.loads(transcription.custom_prompt_history)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse custom_prompt_history for transcription {transcription_id}")
            transcription.custom_prompt_history = []
    
    return transcription


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> TranscriptionListResponse:
    """
    List user's transcriptions
    
    Supports pagination
    """
    # Count total
    total = db.query(Transcription).filter(
        Transcription.user_id == current_user.id
    ).count()
    
    # Get page
    skip = (page - 1) * page_size
    transcriptions = db.query(Transcription).filter(
        Transcription.user_id == current_user.id
    ).order_by(Transcription.created_at.desc()).offset(skip).limit(page_size).all()
    
    # Parse JSON fields if they're strings (SQLite stores JSON as TEXT)
    for transcription in transcriptions:
        if transcription.custom_prompt_history and isinstance(transcription.custom_prompt_history, str):
            import json
            try:
                transcription.custom_prompt_history = json.loads(transcription.custom_prompt_history)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse custom_prompt_history for transcription {transcription.id}")
                transcription.custom_prompt_history = []
    
    return TranscriptionListResponse(
        items=transcriptions,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage_service)
) -> None:
    """
    Delete transcription
    
    Removes transcription record and associated file
    """
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # Delete file from storage
    storage.delete_file(transcription.file_id)
    
    # Delete from database
    db.delete(transcription)
    db.commit()


@router.post("/{transcription_id}/generate-lecture-notes", response_model=TranscriptionResponse)
async def generate_lecture_notes(
    transcription_id: int,
    ai_provider: str = Form("gemini"),
    ai_model: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> TranscriptionResponse:
    """
    Generate lecture notes from ENHANCED transcription text (AI output)
    
    Converts AI-enhanced text to comprehensive academic lecture notes
    with headings, key concepts, context, and references.
    
    If enhanced_text is not available, falls back to original transcription text.
    
    Args:
        ai_provider: AI provider to use (gemini, openai, groq, together)
        ai_model: AI model to use (e.g., gemini-2.5-flash, gpt-4o-mini, llama-3.1-405b-instruct-turbo)
    """
    
    # CREDIT CHECK - Lecture Notes Operation with Model-Based Pricing
    # Default to gemini-2.5-flash if no model specified
    selected_model = ai_model or "gemini-2.5-flash"
    selected_provider = ai_provider or "gemini"
    
    credit_service = get_credit_service(db)
    required_credits = credit_service.calculate_operation_cost("lecture_notes", selected_model, selected_provider)
    user_balance = credit_service.get_balance(current_user.id)
    
    if not credit_service.check_sufficient_credits(current_user.id, required_credits):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Insufficient credits",
                "required": required_credits,
                "available": user_balance,
                "model": selected_model,
                "provider": selected_provider,
                "message": f"Lecture Notes generation with {selected_model} ({selected_provider}) requires {required_credits} credits. You have {user_balance} credits. Please purchase more credits to continue."
            }
        )
    
    logger.info(f"💰 Credit check passed: {user_balance} credits available (required: {required_credits} for {selected_model} on {selected_provider})")
    
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # Use enhanced_text if available, then cleaned_text, otherwise use original text
    # Priority: enhanced_text (best) > cleaned_text (fillers removed) > text (raw Whisper)
    source_text = (
        transcription.enhanced_text or 
        transcription.cleaned_text or 
        transcription.text
    )
    
    if not source_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text available for lecture notes generation. Wait for transcription to complete."
        )
    
    # Import Gemini service
    from app.services.gemini_service import GeminiService
    
    # Use user-selected provider and model
    gemini = GeminiService(preferred_provider=ai_provider, preferred_model=ai_model)
    language = transcription.language or "auto"
    
    try:
        # Determine which text source was used
        text_source = (
            "enhanced" if transcription.enhanced_text else
            "cleaned" if transcription.cleaned_text else
            "original"
        )
        logger.info(f"📝 Converting to lecture notes (using {text_source} text, length: {len(source_text)} chars)")
        
        # Generate lecture notes from best available text (enhanced > cleaned > original)
        notes_result = await gemini.convert_to_lecture_notes(
            source_text, 
            language,
            enable_web_search=True
        )
        
        # Update transcription - lecture_notes should be string (Markdown text), not dict
        import json
        transcription.lecture_notes = notes_result.get("lecture_notes", "")  # Extract the actual notes text
        
        # Update gemini_metadata (JSON column accepts dict directly)
        current_meta = transcription.gemini_metadata or {}
        text_source_used = (
            "enhanced_text" if transcription.enhanced_text else
            "cleaned_text" if transcription.cleaned_text else
            "original_text"
        )
        transcription.gemini_metadata = {
            **current_meta,
            **{k: v for k, v in notes_result.items() if k != "lecture_notes"},  # All metadata except the actual notes
            "lecture_notes_source": text_source_used,
            "lecture_notes_provider": ai_provider,
            "lecture_notes_model": ai_model
        }
        db.commit()
        db.refresh(transcription)
        
        # DEDUCT CREDITS - Lecture Notes completed successfully
        try:
            credit_service.deduct_credits(
                user_id=current_user.id,
                amount=required_credits,
                operation_type=OperationType.LECTURE_NOTES,
                description=f"Lecture Notes: {transcription.original_filename}",
                transcription_id=transcription.id,
                metadata={
                    "source_text_length": len(source_text),
                    "notes_length": len(transcription.lecture_notes or ""),
                    "text_source": text_source_used,
                    "provider": ai_provider,
                    "model": ai_model,
                    "title": notes_result.get("title", "Untitled")
                }
            )
            logger.info(f"💰 {required_credits} credits deducted for lecture notes generation")
        except Exception as credit_error:
            logger.error(f"❌ Credit deduction failed: {credit_error}")
            # Don't fail the operation - lecture notes already generated
        
        logger.info(f"✅ Lecture notes generated successfully: {notes_result.get('title', 'Untitled')}")
        
        return TranscriptionResponse.from_orm(transcription)
        
    except Exception as e:
        logger.error(f"Lecture notes generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lecture notes: {str(e)}"
        )


@router.post("/{transcription_id}/apply-custom-prompt", response_model=TranscriptionResponse)
async def apply_custom_prompt(
    transcription_id: int,
    custom_prompt: str = Form(..., description="Custom instructions for AI"),
    ai_provider: str = Form("gemini"),
    ai_model: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> TranscriptionResponse:
    """
    Apply custom prompt to ENHANCED transcription text (AI output)
    
    Processes AI-enhanced text with user-defined custom instructions.
    
    Args:
        ai_provider: AI provider to use (gemini, openai, groq, together)
        ai_model: AI model to use (e.g., gemini-2.5-flash, gpt-4o-mini, llama-3.1-405b-instruct-turbo)
        custom_prompt: Custom instructions for AI processing
    
    If enhanced_text is not available, falls back to original transcription text.
    """
    logger.info(f"📥 Custom prompt request - provider={ai_provider}, model={ai_model}")
    
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # Use enhanced_text if available, then cleaned_text, otherwise use original text
    # Priority: enhanced_text (best) > cleaned_text (fillers removed) > text (raw Whisper)
    source_text = (
        transcription.enhanced_text or 
        transcription.cleaned_text or 
        transcription.text
    )
    
    if not source_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text available for custom prompt. Wait for transcription to complete."
        )
    
    if not custom_prompt or not custom_prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Custom prompt cannot be empty"
        )
    
    # ============================================================================
    # CREDIT CHECK - Custom Prompt Operation with Model-Based Pricing
    # ============================================================================
    selected_model = ai_model or "gemini-2.5-flash"
    selected_provider = ai_provider or "gemini"
    
    credit_service = get_credit_service(db)
    required_credits = credit_service.calculate_operation_cost("custom_prompt", selected_model, selected_provider)
    user_balance = credit_service.get_balance(current_user.id)
    
    if not credit_service.check_sufficient_credits(current_user.id, required_credits):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Insufficient credits",
                "required": required_credits,
                "available": user_balance,
                "model": selected_model,
                "provider": selected_provider,
                "message": f"Custom Prompt with {selected_model} ({selected_provider}) requires {required_credits} credits but you only have {user_balance}."
            }
        )
    
    # Import Gemini service
    from app.services.gemini_service import GeminiService
    
    # Use user-selected provider and model
    gemini = GeminiService(preferred_provider=ai_provider, preferred_model=ai_model)
    language = transcription.language or "auto"
    
    try:
        # Determine which text source was used
        text_source = (
            "enhanced" if transcription.enhanced_text else
            "cleaned" if transcription.cleaned_text else
            "original"
        )
        logger.info(f"🎨 Processing custom prompt on {text_source} text (length: {len(source_text)} chars)")
        
        # Apply custom prompt to best available text (enhanced > cleaned > original)
        custom_result = await gemini.enhance_with_custom_prompt(
            source_text, 
            custom_prompt, 
            language
        )
        
        # Update transcription - add to custom_prompt_history (preserve old results)
        import json
        from datetime import datetime
        
        # Backward compatibility: Keep last result in old fields too
        transcription.custom_prompt = custom_prompt
        transcription.custom_prompt_result = custom_result.get("processed_text", "")
        
        # Add to history (newest first)
        text_source_used = (
            "enhanced_text" if transcription.enhanced_text else
            "cleaned_text" if transcription.cleaned_text else
            "original_text"
        )
        
        new_entry = {
            "prompt": custom_prompt,
            "result": custom_result.get("processed_text", ""),
            "model": ai_model or selected_model,
            "provider": ai_provider or selected_provider,
            "text_source": text_source_used,
            "timestamp": datetime.now().isoformat(),
            "credits_used": required_credits,
            "metadata": {k: v for k, v in custom_result.items() if k not in ["processed_text"]}
        }
        
        # Get existing history or create new list
        history = transcription.custom_prompt_history or []
        if isinstance(history, str):
            history = json.loads(history)
        
        # Add new entry at the beginning (newest first)
        history.insert(0, new_entry)
        
        # Keep only last 10 entries to avoid DB bloat
        history = history[:10]
        
        # SQLite stores JSON as TEXT, so we need to serialize manually
        transcription.custom_prompt_history = json.dumps(history, ensure_ascii=False)
        
        # Update gemini_metadata (JSON column accepts dict directly)
        current_meta = transcription.gemini_metadata or {}
        transcription.gemini_metadata = {
            **current_meta,
            "custom_prompt_count": len(history),
            "last_custom_prompt": {
                "provider": ai_provider,
                "model": ai_model,
                "timestamp": new_entry["timestamp"]
            }
        }
        db.commit()
        db.refresh(transcription)
        
        # ============================================================================
        # DEDUCT CREDITS - Custom Prompt completed successfully
        # ============================================================================
        try:
            credit_service.deduct_credits(
                user_id=current_user.id,
                amount=required_credits,
                operation_type=OperationType.CUSTOM_PROMPT,
                description=f"Custom Prompt: {transcription.original_filename}",
                transcription_id=transcription.id,
                metadata={
                    "prompt_length": len(custom_prompt),
                    "output_length": len(custom_result.get("processed_text", "")),
                    "provider": ai_provider,
                    "model": ai_model
                }
            )
            logger.info(f"💰 {required_credits} credits deducted for custom prompt")
        except Exception as credit_error:
            logger.error(f"❌ Credit deduction failed: {credit_error}")
            # Don't fail the operation - prompt already processed
        
        logger.info(f"✅ Custom prompt applied successfully (output length: {len(custom_result['processed_text'])} chars)")
        
        # Parse JSON fields if they're strings (SQLite stores JSON as TEXT)
        if transcription.custom_prompt_history and isinstance(transcription.custom_prompt_history, str):
            try:
                transcription.custom_prompt_history = json.loads(transcription.custom_prompt_history)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse custom_prompt_history for transcription {transcription_id}")
                transcription.custom_prompt_history = []
        
        return TranscriptionResponse.from_orm(transcription)
        
    except Exception as e:
        logger.error(f"Custom prompt application failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply custom prompt: {str(e)}"
        )


@router.post("/{transcription_id}/process", response_model=TranscriptionResponse)
async def process_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage_service)
) -> TranscriptionResponse:
    """
    Process transcription (Whisper + Speaker Recognition)
    
    **Note**: This is a synchronous endpoint. For production, use Celery async processing.
    """
    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription not found: {transcription_id}"
        )
    
    # Check if already processed
    if transcription.status == TranscriptionStatus.COMPLETED:
        return transcription
    
    # Update status to processing
    transcription.status = TranscriptionStatus.PROCESSING
    transcription.started_at = datetime.utcnow()
    db.commit()
    
    # WebSocket: Emit processing started
    ws_manager = get_ws_manager()
    await ws_manager.emit_progress(transcription_id, 10, 'processing', 'Loading file...')
    
    try:
        # Get file path
        file_path = storage.get_file_path(transcription.file_id)
        if not file_path or not file_path.exists():
            raise FileNotFoundError(f"File not found: {transcription.file_id}")
        
        logger.info(f"🎬 Processing transcription {transcription_id}: {file_path}")
        start_time = time.time()
        
        # WebSocket: Models loading
        await ws_manager.emit_progress(transcription_id, 30, 'processing', 'Loading AI models...')
        
        # Get settings
        settings = get_settings()
        
        # Initialize audio processor
        processor = get_audio_processor(
            whisper_model_size=settings.WHISPER_MODEL_SIZE,
            speaker_model_path=settings.GLOBAL_MODEL_PATH if transcription.use_speaker_recognition else None,
            speaker_mapping_path=settings.GLOBAL_MAPPING_PATH if transcription.use_speaker_recognition else None,
            speaker_threshold=settings.GLOBAL_MODEL_THRESHOLD
        )
        
        # WebSocket: Transcribing
        await ws_manager.emit_progress(transcription_id, 50, 'processing', 'Transcribing audio...')
        
        # Process audio
        result = processor.process_file(
            str(file_path),
            language=transcription.language
        )
        
        # WebSocket: Saving results
        await ws_manager.emit_progress(transcription_id, 90, 'processing', 'Saving results...')
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update transcription with results
        transcription.text = result["text"]
        transcription.language = result["language"]
        transcription.speaker_count = result["speaker_count"]
        transcription.speakers = result["speakers"]
        transcription.segments = result["segments"]
        transcription.processing_time = processing_time
        transcription.status = TranscriptionStatus.COMPLETED
        transcription.completed_at = datetime.utcnow()
        transcription.error_message = None
        
        db.commit()
        db.refresh(transcription)
        
        logger.info(f"✅ Transcription {transcription_id} completed in {processing_time:.2f}s")
        
        # WebSocket: Completed
        await ws_manager.emit_completed(transcription_id, {
            'text_length': len(result["text"]),
            'language': result["language"],
            'speaker_count': result["speaker_count"],
            'processing_time': processing_time
        })
        
        return transcription
        
    except Exception as e:
        logger.error(f"❌ Transcription {transcription_id} failed: {e}", exc_info=True)
        
        # WebSocket: Error
        await ws_manager.emit_error(transcription_id, str(e))
        
        # Update status to failed
        transcription.status = TranscriptionStatus.FAILED
        transcription.error_message = str(e)
        transcription.completed_at = datetime.utcnow()
        
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.post("/{transcription_id}/enhance", response_model=TranscriptionResponse)
async def enhance_transcription(
    transcription_id: int,
    include_summary: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> TranscriptionResponse:
    """
    Enhance transcription text using Gemini AI
    
    - **transcription_id**: ID of the transcription to enhance
    - **include_summary**: Whether to generate a summary (default: True)
    
    This endpoint:
    1. Takes the raw transcription text
    2. Uses Gemini AI to fix punctuation, spelling, formatting
    3. Optionally generates a summary
    4. Updates the transcription with enhanced text
    5. Sends real-time progress via WebSocket
    """
    from app.services.gemini_service import get_gemini_service
    
    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    # Check if transcription is completed
    if transcription.status != TranscriptionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcription must be completed first (current status: {transcription.status.value})"
        )
    
    # Check if text exists
    if not transcription.text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transcription text available to enhance"
        )
    
    # Get Gemini service
    gemini = get_gemini_service()
    
    if not gemini.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini AI service is not available. Please configure GEMINI_API_KEY."
        )
    
    # Get WebSocket manager
    ws_manager = get_ws_manager()
    
    try:
        logger.info(f"🎨 Starting Gemini enhancement for transcription {transcription_id}")
        
        # Update status
        transcription.gemini_status = "processing"
        db.commit()
        
        # WebSocket: Enhancement started
        await ws_manager.emit_progress(
            transcription_id,
            0,
            'enhancing',
            '🎨 Starting AI text enhancement...'
        )
        
        # Stage 1: Preparing (20%)
        await ws_manager.emit_progress(
            transcription_id,
            20,
            'enhancing',
            '📝 Analyzing transcription text...'
        )
        
        # Stage 2: Calling Gemini (50%)
        await ws_manager.emit_progress(
            transcription_id,
            50,
            'enhancing',
            '🤖 AI processing in progress...'
        )
        
        start_time = time.time()
        
        # Call Gemini AI
        result = await gemini.enhance_text(
            text=transcription.text,
            language=transcription.language or "tr",
            include_summary=include_summary
        )
        
        enhancement_time = time.time() - start_time
        
        # Stage 3: Saving results (80%)
        await ws_manager.emit_progress(
            transcription_id,
            80,
            'enhancing',
            '💾 Saving enhanced text...'
        )
        
        # Update transcription with enhanced data
        transcription.enhanced_text = result["enhanced_text"]
        transcription.summary = result.get("summary", "")
        transcription.gemini_status = "completed"
        transcription.gemini_improvements = result.get("improvements", [])
        transcription.gemini_metadata = {
            "model_used": result.get("model_used"),
            "original_length": result.get("original_length"),
            "enhanced_length": result.get("enhanced_length"),
            "word_count": result.get("word_count"),
            "enhancement_time": enhancement_time,
            "language": result.get("language")
        }
        
        db.commit()
        
        # Stage 4: Complete (100%)
        await ws_manager.emit_completed(transcription_id, {
            'enhanced': True,
            'summary_generated': bool(result.get("summary")),
            'improvements_count': len(result.get("improvements", [])),
            'enhancement_time': enhancement_time
        })
        
        logger.info(f"✅ Enhancement completed for transcription {transcription_id}")
        logger.info(f"   Enhancement time: {enhancement_time:.2f}s")
        logger.info(f"   Improvements: {len(result.get('improvements', []))}")
        
        return transcription
        
    except Exception as e:
        logger.error(f"❌ Enhancement failed for transcription {transcription_id}: {e}")
        
        # Update status to failed
        transcription.gemini_status = "failed"
        transcription.error_message = f"Enhancement failed: {str(e)}"
        db.commit()
        
        # WebSocket: Error
        await ws_manager.emit_error(transcription_id, f"Enhancement failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text enhancement failed: {str(e)}"
        )


@router.post("/{transcription_id}/generate-exam-questions", response_model=TranscriptionResponse)
async def generate_exam_questions(
    transcription_id: int,
    num_questions: int = Form(5),
    ai_provider: str = Form("gemini"),
    ai_model: str | None = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate exam questions from transcription using AI
    
    **Post-processing endpoint** - transcription must be completed first
    
    Args:
        ai_provider: AI provider to use (gemini, openai, groq, together)
        ai_model: AI model to use (e.g., gemini-2.5-flash, gpt-4o-mini, llama-3.1-405b-instruct-turbo)
        num_questions: Number of questions to generate (1-50)
    """
    from app.services.gemini_service import GeminiService
    import json
    
    # CREDIT CHECK - Exam Questions Operation with Model-Based Pricing
    selected_model = ai_model or "gemini-2.5-flash"
    selected_provider = ai_provider or "gemini"
    
    credit_service = get_credit_service(db)
    required_credits = credit_service.calculate_operation_cost("exam_questions", selected_model, selected_provider)
    user_balance = credit_service.get_balance(current_user.id)
    
    if not credit_service.check_sufficient_credits(current_user.id, required_credits):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Insufficient credits",
                "required": required_credits,
                "available": user_balance,
                "model": selected_model,
                "provider": selected_provider,
                "message": f"Exam Questions generation with {selected_model} ({selected_provider}) requires {required_credits} credits. You have {user_balance} credits. Please purchase more credits to continue."
            }
        )
    
    logger.info(f"💰 Credit check passed: {user_balance} credits available (required: {required_credits} for {selected_model})")
    logger.info(f"🎓 Generating {num_questions} exam questions for transcription {transcription_id}")
    
    # Get transcription
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    # Validate status
    if transcription.status != TranscriptionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcription must be completed first. Current status: {transcription.status}"
        )
    
    # Use enhanced_text if available, then cleaned_text, otherwise use original text
    # Priority: enhanced_text (best) > cleaned_text (fillers removed) > text (raw Whisper)
    source_text = (
        transcription.enhanced_text or 
        transcription.cleaned_text or 
        transcription.text
    )
    
    if not source_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transcription text available"
        )
    
    try:
        # Get AI service with user-selected provider and model
        gemini_service = GeminiService(preferred_provider=ai_provider, preferred_model=ai_model)
        
        if not gemini_service.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is not available"
            )
        
        # Determine which text source was used
        text_source = (
            "enhanced" if transcription.enhanced_text else
            "cleaned" if transcription.cleaned_text else
            "original"
        )
        logger.info(f"📝 Generating exam questions from {text_source} text (length: {len(source_text)} chars)")
        
        start_time = time.time()
        
        # Generate exam questions from best available text
        result = await gemini_service.generate_exam_questions(
            text=source_text,
            language=transcription.language or "tr",
            num_questions=num_questions
        )
        
        generation_time = time.time() - start_time
        
        # Check for safety filter blocking
        if result.get("safety_blocked"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Content was blocked by AI safety filters. Try with different text."
            )
        
        # Save to database as JSON string with metadata
        exam_data = {
            **result,
            "provider": ai_provider,
            "model": ai_model,
            "generation_time": generation_time
        }
        transcription.exam_questions = json.dumps(exam_data, ensure_ascii=False)
        db.commit()
        db.refresh(transcription)
        
        # DEDUCT CREDITS - Exam Questions completed successfully
        try:
            credit_service.deduct_credits(
                user_id=current_user.id,
                amount=required_credits,
                operation_type=OperationType.EXAM_QUESTIONS,
                description=f"Exam Questions: {transcription.original_filename} ({num_questions} questions)",
                transcription_id=transcription.id,
                metadata={
                    "source_text_length": len(source_text),
                    "num_questions": num_questions,
                    "questions_generated": len(result.get('questions', [])),
                    "text_source": text_source,
                    "provider": ai_provider,
                    "model": ai_model,
                    "generation_time": generation_time
                }
            )
            logger.info(f"💰 {required_credits} credits deducted for exam questions generation")
        except Exception as credit_error:
            logger.error(f"❌ Credit deduction failed: {credit_error}")
            # Don't fail the operation - exam questions already generated
        
        logger.info(f"✅ Generated {len(result.get('questions', []))} exam questions")
        logger.info(f"   Generation time: {generation_time:.2f}s")
        
        return transcription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Exam question generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Exam question generation failed: {str(e)}"
        )


@router.post("/{transcription_id}/translate", response_model=TranscriptionResponse)
async def translate_transcription(
    transcription_id: int,
    target_language: str,
    ai_provider: str | None = None,
    ai_model: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Translate transcription text to target language using AI
    
    Supported languages: en, tr, de, fr, es, it, pt, ru, ar, zh, ja, ko
    
    Args:
        ai_provider: AI provider to use (gemini, openai, groq, together)
        ai_model: AI model to use (e.g., gemini-2.5-flash, gemini-2.5-pro, gpt-4o-mini)
    """
    from app.services.gemini_service import get_gemini_service
    
    # CREDIT CHECK - Translation Operation with Character-Based Pricing
    selected_model = ai_model or "gemini-2.5-flash"
    selected_provider = ai_provider or "gemini"
    
    # Get transcription first to calculate character-based cost
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcription not found"
        )
    
    # Validate status
    if transcription.status != TranscriptionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcription must be completed first. Current status: {transcription.status}"
        )
    
    # Use enhanced_text if available, otherwise use original text
    source_text = transcription.enhanced_text or transcription.text
    
    if not source_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text available for translation"
        )
    
    # Calculate character-based cost (1000 chars = X credits based on model)
    credit_service = get_credit_service(db)
    required_credits = credit_service.calculate_text_based_cost(
        text=source_text,
        model_key=selected_model,
        provider=selected_provider
    )
    user_balance = credit_service.get_balance(current_user.id)
    
    if not credit_service.check_sufficient_credits(current_user.id, required_credits):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "Insufficient credits",
                "required": required_credits,
                "available": user_balance,
                "model": selected_model,
                "provider": selected_provider,
                "message": f"Translation with {selected_model} ({selected_provider}) requires {required_credits} credits. You have {user_balance} credits. Please purchase more credits to continue."
            }
        )
    
    logger.info(f"💰 Credit check passed: {user_balance} credits available (required: {required_credits} for {selected_model})")
    logger.info(f"🌐 Translating transcription {transcription_id} to {target_language} ({len(source_text)} chars)")
    
    try:
        # Get Gemini service
        gemini_service = get_gemini_service()
        
        if not gemini_service.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini AI service is not available"
            )
        
        start_time = time.time()
        
        # Translate text
        result = await gemini_service.translate_text(
            text=source_text,
            target_language=target_language
        )
        
        translation_time = time.time() - start_time
        
        # Check for safety filter blocking
        if result.get("safety_blocked"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Content was blocked by Gemini safety filters"
            )
        
        # Load existing translations or create new dict
        import json
        translations = {}
        if transcription.translated_text:
            try:
                # Handle both JSON string and dict
                if isinstance(transcription.translated_text, str):
                    translations = json.loads(transcription.translated_text)
                else:
                    translations = transcription.translated_text
            except:
                translations = {}
        
        # Add new translation with explicit UTF-8 encoding
        translations[target_language] = result["translated_text"]
        
        # Save as JSON string to ensure proper encoding
        transcription.translated_text = json.dumps(translations, ensure_ascii=False)
        db.commit()
        db.refresh(transcription)
        
        # DEDUCT CREDITS - Translation completed successfully (Character-based pricing)
        try:
            text_source = "enhanced" if transcription.enhanced_text else "original"
            credit_service.deduct_credits(
                user_id=current_user.id,
                amount=required_credits,
                operation_type=OperationType.TRANSLATION,
                description=f"Translation to {target_language}: {transcription.original_filename}",
                transcription_id=transcription.id,
                metadata={
                    "character_count": len(source_text),
                    "source_text_length": len(source_text),
                    "translated_text_length": len(result["translated_text"]),
                    "target_language": target_language,
                    "text_source": text_source,
                    "translation_time": translation_time,
                    "total_translations": len(translations),
                    "model_key": selected_model,
                    "provider": selected_provider,
                    "pricing_type": "character_based"
                }
            )
            logger.info(f"💰 {required_credits} credits deducted for translation ({len(source_text)} chars with {selected_model})")
        except Exception as credit_error:
            logger.error(f"❌ Credit deduction failed: {credit_error}")
            # Don't fail the operation - translation already completed
        
        logger.info(f"✅ Translation to {target_language} completed")
        logger.info(f"   Translation time: {translation_time:.2f}s")
        logger.info(f"   Total translations: {len(translations)}")
        
        return transcription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Translation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}"
        )


@router.post("/youtube", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription_from_youtube(
    youtube_url: str = Form(...),
    whisper_model: str = Form("tiny"),
    transcription_provider: str = Form("openai_whisper"),  # "openai_whisper" or "assemblyai"
    enable_diarization: bool = Form(False),
    min_speakers: int | None = Form(None),
    max_speakers: int | None = Form(None),
    use_gemini_enhancement: bool = Form(False),
    ai_provider: str = Form("gemini"),  # "gemini" or "openai"
    ai_model: str | None = Form(None),  # AI model name
    gemini_mode: str = Form("text"),
    custom_prompt: str | None = Form(None),
    enable_web_search: bool = Form(False),  # Enable Tavily web search (optional)
    enable_assemblyai_speech_understanding: bool = Form(False),  # NEW: Enable AssemblyAI Speech Understanding
    enable_assemblyai_llm_gateway: bool = Form(False),  # NEW: Enable AssemblyAI LLM Gateway with LeMUR
    language: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    storage = Depends(get_storage_service)
) -> TranscriptionResponse:
    """
    Create transcription from YouTube video
    
    - **youtube_url**: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)
    - **whisper_model**: Whisper model size (tiny, base, small, medium, large)
    - **language**: Language code (tr, en, de, etc.) or null for auto-detect
    - **enable_diarization**: Enable speaker diarization with pyannote.audio 3.1
    - **min_speakers**: Minimum expected speakers (optional)
    - **max_speakers**: Maximum expected speakers (optional)
    - **use_gemini_enhancement**: Enhance text with AI
    - **ai_provider**: AI provider (gemini, openai) - default: gemini
    - **gemini_mode**: Processing mode (text, note, custom)
    - **custom_prompt**: Custom prompt (required if gemini_mode=custom)
    """
    from app.services.youtube_service import get_youtube_service
    
    youtube_service = get_youtube_service()
    temp_file = None
    
    try:
        # Validate YouTube URL
        if not youtube_url or not ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid YouTube URL. Please provide a valid YouTube video link."
            )
        
        logger.info(f"🎬 Starting YouTube transcription: {youtube_url}")
        
        # Extract video info
        try:
            video_info = youtube_service.extract_video_info(youtube_url)
            logger.info(f"📹 Video: {video_info['title']} ({video_info['duration']}s)")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to access YouTube video: {str(e)}"
            )
        
        # Download audio from YouTube
        try:
            temp_file = youtube_service.download_audio(youtube_url)
            logger.info(f"✅ Audio downloaded: {temp_file}")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download YouTube audio: {str(e)}"
            )
        
        # Save to storage
        with open(temp_file, 'rb') as f:
            file_id, file_path = storage.save_file(f, f"{video_info['title']}.mp3")
        
        # Get file size before cleanup
        file_size = temp_file.stat().st_size if temp_file.exists() else 0
        
        # Clean up temp file
        youtube_service.cleanup_file(temp_file)
        
        # Validate gemini mode
        try:
            gemini_mode_enum = GeminiMode[gemini_mode.upper()]
        except KeyError:
            gemini_mode_enum = GeminiMode.TEXT
            logger.warning(f"Invalid gemini_mode: {gemini_mode}, using default: TEXT")
        
        # 🔍 DEBUG: Log all incoming parameters
        logger.info(f"=" * 80)
        logger.info(f"🎯 NEW YOUTUBE TRANSCRIPTION REQUEST")
        logger.info(f"   User: {current_user.username} (ID: {current_user.id})")
        logger.info(f"   YouTube URL: {youtube_url}")
        logger.info(f"   Provider: {transcription_provider}")
        logger.info(f"   🔍 enable_assemblyai_speech_understanding: {enable_assemblyai_speech_understanding} (type: {type(enable_assemblyai_speech_understanding)})")
        logger.info(f"   🤖 enable_assemblyai_llm_gateway: {enable_assemblyai_llm_gateway} (type: {type(enable_assemblyai_llm_gateway)})")
        logger.info(f"=" * 80)
        
        # Create AssemblyAI features config
        assemblyai_features = {}
        if enable_assemblyai_speech_understanding:
            assemblyai_features['speech_understanding'] = {
                'sentiment_analysis': True,
                'auto_chapters': True,
                'entity_detection': True,
                'auto_highlights': True,
                'speaker_labels': True
            }
            logger.info(f"✅ Speech Understanding ENABLED - added to assemblyai_features")
        if enable_assemblyai_llm_gateway:
            assemblyai_features['llm_gateway'] = {
                'enabled': True,
                'generate_summary': True
            }
            logger.info(f"✅ LLM Gateway ENABLED - added to assemblyai_features")
        
        logger.info(f"📦 Final assemblyai_features dict: {assemblyai_features}")
        
        # Create transcription record
        transcription = Transcription(
            user_id=current_user.id,
            filename=f"{video_info['title']}.mp3",
            file_id=file_id,
            file_path=str(file_path),
            file_size=file_size,
            content_type="audio/mpeg",
            whisper_model=whisper_model,
            transcription_provider=transcription_provider,  # "openai_whisper" or "assemblyai"
            language=language,
            enable_diarization=enable_diarization,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            use_gemini_enhancement=use_gemini_enhancement,
            ai_provider=ai_provider,  # "gemini" or "openai"
            ai_model=ai_model,  # Model name
            enable_web_search=enable_web_search,  # Enable Tavily web search
            assemblyai_features_enabled=assemblyai_features if assemblyai_features else None,  # NEW: Track enabled features
            gemini_mode=gemini_mode_enum,
            custom_prompt=custom_prompt,
            status=TranscriptionStatus.PENDING,
            youtube_url=youtube_url,
            youtube_title=video_info['title'],
            youtube_duration=video_info['duration']
        )
        
        db.add(transcription)
        db.commit()
        db.refresh(transcription)
        
        logger.info(f"✅ Transcription record created: ID={transcription.id}")
        
        # Queue transcription task
        if CELERY_AVAILABLE:
            task = process_transcription_task.apply_async(
                args=[transcription.id],
                countdown=1
            )
            transcription.celery_task_id = task.id
            db.commit()
            logger.info(f"🚀 Celery task queued: {task.id}")
        else:
            logger.warning("⚠️ Celery not available, task will be processed synchronously")
        
        return transcription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ YouTube transcription failed: {e}", exc_info=True)
        
        # Cleanup temp file on error
        if temp_file:
            youtube_service.cleanup_file(temp_file)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTube transcription failed: {str(e)}"
        )


@router.post("/estimate-cost", response_model=CostEstimationResponse)
async def estimate_transcription_cost(
    request: CostEstimationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> CostEstimationResponse:
    """
    Estimate credit cost for transcription before processing
    
    - **duration_seconds**: Audio duration in seconds
    - **use_speaker_recognition**: Enable speaker recognition
    - **use_gemini_enhancement**: Enhance with AI
    - **ai_provider**: AI provider (gemini, openai, groq, together)
    - **ai_model**: AI model key (optional, uses default if not provided)
    - **gemini_mode**: AI processing mode (text, note, custom)
    - **enable_web_search**: Enable web search enrichment
    - **is_youtube**: Is YouTube video transcription
    """
    try:
        # Create credit service instance
        credit_service = get_credit_service(db)
        
        # Get user's current balance
        user_credits = credit_service.get_balance(current_user.id)
        
        # Calculate transcription base cost
        transcription_cost = credit_service.pricing.calculate_transcription_cost(
            duration_seconds=request.duration_seconds,
            enable_diarization=request.enable_diarization,
            is_youtube=request.is_youtube,
            transcription_provider=request.transcription_provider
        )
        
        # Initialize cost breakdown
        minutes = request.duration_seconds / 60.0
        
        if request.transcription_provider == "assemblyai" or request.enable_diarization:
            # AssemblyAI: 2.0 kredi/dakika (includes diarization)
            cost_breakdown = {
                "transcription_assemblyai": round(2.0 * minutes, 2)
            }
        else:
            # OpenAI Whisper: 1.0 kredi/dakika
            cost_breakdown = {
                "transcription_openai_whisper": round(credit_service.pricing.TRANSCRIPTION_BASE * minutes, 2)
            }
        
        if request.is_youtube:
            cost_breakdown["youtube_download"] = credit_service.pricing.YOUTUBE_DOWNLOAD
        
        total_cost = transcription_cost
        
        # Calculate AI enhancement cost if enabled
        if request.use_gemini_enhancement:
            # Determine AI operation based on mode
            if request.gemini_mode.upper() == "NOTE":
                operation_key = "lecture_notes"
            elif request.gemini_mode.upper() == "CUSTOM":
                operation_key = "custom_prompt"
            else:
                operation_key = "ai_enhancement"
            
            # Get AI model (use default if not specified)
            ai_model = request.ai_model
            if not ai_model:
                # Get default model for provider
                from app.models.ai_model_pricing import AIModelPricing
                default_model = db.query(AIModelPricing).filter(
                    AIModelPricing.provider == request.ai_provider,
                    AIModelPricing.is_default == True
                ).first()
                ai_model = default_model.model_key if default_model else "gemini-2.5-flash"
            
            ai_cost = credit_service.calculate_operation_cost(
                operation_key=operation_key,
                model_key=ai_model,
                provider=request.ai_provider
            )
            
            cost_breakdown[f"ai_enhancement_{request.gemini_mode}"] = ai_cost
            total_cost += ai_cost
        
        # Add web search cost if enabled
        if request.enable_web_search:
            web_search_cost = credit_service.pricing.TAVILY_WEB_SEARCH
            cost_breakdown["web_search"] = web_search_cost
            total_cost += web_search_cost
        
        # Round total cost
        total_cost = round(total_cost, 2)
        
        # Check if user has sufficient credits
        sufficient_credits = user_credits >= total_cost
        
        logger.info(f"💰 Cost estimation: {total_cost} credits (user has {user_credits})")
        
        return CostEstimationResponse(
            total_cost=total_cost,
            breakdown=cost_breakdown,
            user_credits=user_credits,
            sufficient_credits=sufficient_credits
        )
        
    except Exception as e:
        logger.error(f"❌ Cost estimation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cost estimation failed: {str(e)}"
        )


@router.get("/ai-models")
async def get_ai_models(
    db: Session = Depends(get_db)
):
    """Get list of available AI models grouped by provider (public endpoint)"""
    from app.models.ai_model_pricing import AIModelPricing
    
    try:
        models = db.query(AIModelPricing).filter(AIModelPricing.is_active == True).all()
        
        # Group by provider
        grouped_models = {}
        for model in models:
            provider = model.provider
            if provider not in grouped_models:
                grouped_models[provider] = []
            
            grouped_models[provider].append({
                "model_key": model.model_key,
                "model_name": model.model_name,
                "credit_multiplier": model.credit_multiplier,
                "cost_per_1k_chars": model.cost_per_1k_chars,
            })
        
        # Sort models within each provider by credit_multiplier (cheapest first)
        for provider in grouped_models:
            grouped_models[provider].sort(key=lambda x: x["credit_multiplier"])
        
        return {
            "models": grouped_models,
            "total_count": len(models)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch AI models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch AI models: {str(e)}"
        )
