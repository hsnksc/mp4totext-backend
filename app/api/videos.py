"""
Videos API - Video generation from transcripts
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import time

from app.database import get_db
from app.models.user import User
from app.models.transcription import Transcription
from app.models.generated_video import GeneratedVideo
from app.models.credit_transaction import OperationType
from app.api.auth import get_current_active_user
from app.services.credit_service import get_credit_service, InsufficientCreditsError
from app.services.video_generator import get_video_generator_service

logger = logging.getLogger(__name__)
router = APIRouter()


class VideoGenerationRequest(BaseModel):
    """Request model for video generation"""
    transcription_id: int = Field(..., description="ID of the transcription")
    style: str = Field(default="professional", description="Image style for video frames")
    model_type: str = Field(default="sdxl", description="Image model: sdxl (A10G, balanced), flux (H100, ultra quality)")
    voice: str = Field(default="alloy", description="TTS voice (alloy, echo, fable, onyx, nova, shimmer)")
    background: bool = Field(default=True, description="Run as background task")
    custom_prompt: Optional[str] = Field(default=None, description="Custom prompt for video content (overrides transcript)")


class VideoGenerationResponse(BaseModel):
    """Response model for video generation"""
    message: str
    video_id: Optional[int] = None
    task_id: Optional[str] = None
    status: str  # processing, completed, failed
    estimated_cost: Optional[float] = None


@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate a video from transcript using AI
    
    Pipeline:
    1. Segment transcript into ~1min meaningful chunks (Gemini 2.5 Pro)
    2. Generate images for each segment (Modal SDXL)
    3. Generate speech for each segment (OpenAI TTS)
    4. Combine images + audio into video segments (FFmpeg)
    5. Concatenate all segments into final video
    """
    try:
        logger.info(f"🎬 Video generation request: transcription_id={request.transcription_id}, user={current_user.id}")
        
        # 1. Get transcription
        transcription = db.query(Transcription).filter(
            Transcription.id == request.transcription_id,
            Transcription.user_id == current_user.id
        ).first()
        
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        # Check if audio transcription is completed OR document analysis is completed
        audio_completed = transcription.status == "completed" and transcription.text
        document_completed = transcription.has_document and transcription.vision_status == "completed"
        
        if not audio_completed and not document_completed:
            raise HTTPException(
                status_code=400,
                detail="Either audio transcription or document analysis must be completed"
            )
        
        # Get content for video generation
        content_for_video = None
        if document_completed and transcription.document_summary:
            content_for_video = transcription.document_summary
        elif document_completed and transcription.document_text:
            content_for_video = transcription.document_text[:5000]
        elif audio_completed and transcription.text:
            content_for_video = transcription.text
        
        if not content_for_video:
            raise HTTPException(status_code=400, detail="No content available for video generation")
        
        # 2. Estimate cost
        video_gen = get_video_generator_service()
        cost_estimate = video_gen.estimate_video_cost(content_for_video)
        required_credits = cost_estimate["total_credits"]
        
        logger.info(f"💰 Estimated cost: {required_credits} credits")
        
        # 3. Check user credits
        credits_service = get_credit_service(db)
        if current_user.credits < required_credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {required_credits}, Available: {current_user.credits}"
            )
        
        # 4. Create video record
        video = GeneratedVideo(
            transcription_id=transcription.id,
            user_id=current_user.id,
            filename=f"video_{transcription.id}_{int(time.time())}.mp4",
            style=request.style,
            status="processing",
            progress=0
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        
        if request.background:
            # 5. Start background task
            from app.workers.transcription_worker import generate_video_task
            
            # DEBUG: Log custom_prompt
            if request.custom_prompt:
                logger.info(f"🎨 Custom prompt provided: {request.custom_prompt[:100]}...")
            else:
                logger.info("📝 No custom prompt, will use transcript segmentation")
            
            task = generate_video_task.delay(
                video_id=video.id,
                transcription_id=transcription.id,
                user_id=current_user.id,
                style=request.style,
                model_type=request.model_type,
                voice=request.voice,
                custom_prompt=request.custom_prompt
            )
            
            video.task_id = task.id
            db.commit()
            
            logger.info(f"✅ Video generation task started: task_id={task.id}")
            
            return VideoGenerationResponse(
                message="Video generation started",
                video_id=video.id,
                task_id=task.id,
                status="processing",
                estimated_cost=required_credits
            )
        else:
            # Synchronous generation (for testing)
            raise HTTPException(
                status_code=501,
                detail="Synchronous video generation not implemented. Use background=true"
            )
            
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Video generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transcription/{transcription_id}")
async def get_videos_for_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all generated videos for a transcription"""
    videos = db.query(GeneratedVideo).filter(
        GeneratedVideo.transcription_id == transcription_id,
        GeneratedVideo.user_id == current_user.id
    ).order_by(GeneratedVideo.created_at.desc()).all()
    
    # Generate fresh presigned URLs for completed videos
    from app.services.storage import get_storage_service
    from datetime import timedelta
    
    storage = get_storage_service()
    result_videos = []
    
    for video in videos:
        video_dict = video.to_dict()
        
        if video.status == "completed" and video.filename:
            try:
                # Generate fresh MinIO presigned URL
                url = storage.minio_client.presigned_get_object(
                    bucket_name=storage.bucket_name,
                    object_name=video.filename,
                    expires=timedelta(hours=1)
                )
                video_dict["url"] = url
                logger.info(f"✅ Generated fresh URL for video {video.filename}")
            except Exception as e:
                logger.error(f"❌ Failed to generate URL for {video.filename}: {e}")
        
        result_videos.append(video_dict)
    
    return {"videos": result_videos}


@router.get("/{video_id}")
async def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific video with fresh URL"""
    video = db.query(GeneratedVideo).filter(
        GeneratedVideo.id == video_id,
        GeneratedVideo.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_dict = video.to_dict()
    
    if video.status == "completed" and video.filename:
        from app.services.storage import get_storage_service
        from datetime import timedelta
        
        storage = get_storage_service()
        try:
            url = storage.minio_client.presigned_get_object(
                bucket_name=storage.bucket_name,
                object_name=video.filename,
                expires=timedelta(hours=1)
            )
            video_dict["url"] = url
        except Exception as e:
            logger.error(f"❌ Failed to generate URL: {e}")
    
    return video_dict


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a generated video"""
    video = db.query(GeneratedVideo).filter(
        GeneratedVideo.id == video_id,
        GeneratedVideo.user_id == current_user.id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Delete from storage
    if video.filename:
        from app.services.storage import get_storage_service
        storage = get_storage_service()
        try:
            storage.delete_file(video.filename)
            logger.info(f"🗑️ Deleted video file: {video.filename}")
        except Exception as e:
            logger.error(f"❌ Failed to delete video file: {e}")
    
    # Delete from database
    db.delete(video)
    db.commit()
    
    return {"message": "Video deleted successfully"}


import time
