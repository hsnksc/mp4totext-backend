"""
Image Generation API Router
Transcript'ten görsel oluşturma endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.transcription import Transcription
from app.models.generated_image import GeneratedImage
from app.models.credit_transaction import OperationType
from app.services.image_generator import get_image_generator
from app.services.storage import get_storage_service
from app.services.credit_service import get_credit_service, InsufficientCreditsError
from app.auth.utils import get_current_active_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["images"])


class ImageGenerationRequest(BaseModel):
    """Image generation request"""
    transcription_id: int = Field(..., description="Transcription ID")
    num_images: int = Field(1, ge=1, le=4, description="Number of images (1-4)")
    style: str = Field("professional", description="Image style: professional, artistic, technical, minimalist, cinematic")
    model_type: str = Field("sdxl", description="Model: sdxl (A10G, balanced), flux (H100, ultra quality), imagen (Replicate, photorealistic)")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt (overrides AI-generated)")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions for AI prompt generation")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    background: bool = Field(False, description="Generate in background (Celery task)")


class ImageGenerationResponse(BaseModel):
    """Image generation response"""
    status: str
    transcription_id: int
    prompt: str
    images: List[str]  # URLs
    count: int
    style: str
    task_id: Optional[str] = None  # Celery task ID if background


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_images(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transkript'ten görsel oluştur
    
    **Styles:**
    - `professional`: İş/toplantı görselleri, modern ve temiz
    - `artistic`: Sanatsal, yaratıcı illüstrasyon
    - `technical`: Teknik diyagram/infografik tarzı
    - `minimalist`: Minimalist tasarım, basit kompozisyon
    - `cinematic`: Sinematik ışıklandırma, dramatik
    
    **Examples:**
    ```json
    {
      "transcription_id": 123,
      "num_images": 1,
      "style": "professional"
    }
    ```
    
    With custom prompt:
    ```json
    {
      "transcription_id": 123,
      "num_images": 2,
      "style": "artistic",
      "custom_prompt": "Colorful abstract representation of a business meeting",
      "seed": 42
    }
    ```
    """
    logger.info(f"🎨 Image generation request: transcription_id={request.transcription_id}, style={request.style}")
    
    # 1. Transcription var mı ve user'a ait mi?
    transcription = db.query(Transcription).filter(
        Transcription.id == request.transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=404, 
            detail="Transcription not found or you don't have access"
        )
    
    # Check if audio transcription is completed OR document analysis is completed
    audio_completed = transcription.status == "completed" and transcription.text
    document_completed = transcription.has_document and transcription.vision_status == "completed"
    
    if not audio_completed and not document_completed:
        raise HTTPException(
            status_code=400,
            detail="Either audio transcription or document analysis must be completed"
        )
    
    # Get content for image generation - prefer document_summary, then text
    content_for_image = None
    if document_completed and transcription.document_summary:
        content_for_image = transcription.document_summary
        logger.info("📄 Using document_summary for image generation")
    elif document_completed and transcription.document_text:
        content_for_image = transcription.document_text[:2000]  # Limit for prompt
        logger.info("📄 Using document_text for image generation")
    elif audio_completed and transcription.text:
        content_for_image = transcription.text
        logger.info("🎵 Using audio transcription text for image generation")
    
    if not content_for_image:
        raise HTTPException(
            status_code=400,
            detail="No content available for image generation"
        )
    
    # 2. Kredi kontrolü - Her görsel için 1 kredi
    credits_service = get_credit_service(db)
    required_credits = float(request.num_images)  # 1 kredi/görsel
    
    if current_user.credits < required_credits:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=f"Insufficient credits. Required: {required_credits}, Available: {current_user.credits}"
        )
    
    logger.info(f"💰 User {current_user.id} has {current_user.credits} credits, needs {required_credits}")
    
    # 3. HER ZAMAN Celery task olarak çalıştır (uzun sürebilir)
    from app.workers.transcription_worker import generate_transcript_images
    
    logger.info(f"🚀 Launching Celery task for image generation...")
    logger.info(f"   Transcription: {request.transcription_id}")
    logger.info(f"   User: {current_user.id}")
    logger.info(f"   Num Images: {request.num_images}")
    logger.info(f"   Style: {request.style}")
    
    task = generate_transcript_images.delay(
        transcription_id=request.transcription_id,
        user_id=current_user.id,
        num_images=request.num_images,
        style=request.style,
        model_type=request.model_type,
        custom_prompt=request.custom_prompt,
        custom_instructions=request.custom_instructions,
        seed=request.seed
    )
    
    logger.info(f"✅ Celery task queued: {task.id}")
    
    return ImageGenerationResponse(
        status="processing",
        transcription_id=request.transcription_id,
        prompt="Generating in background...",
        images=[],
        count=0,
        style=request.style,
        task_id=task.id
    )
    
    # SYNC CODE REMOVED - Always use Celery
    # 3. Sync image generation (OLD CODE - REMOVED)
    try:
        image_gen = get_image_generator()
        
        # Use AI-generated summary as base prompt if available
        if request.custom_prompt:
            # User provided custom prompt - use it directly
            base_prompt = request.custom_prompt
        elif transcription.ai_generated_summary:
            # Use AI summary - most relevant for image generation
            logger.info("📝 Using AI-generated summary as image prompt base")
            base_prompt = transcription.ai_generated_summary
        else:
            # Fallback to transcript text
            base_prompt = transcription.text
        
        result = await image_gen.generate_images_from_transcript(
            transcript_text=base_prompt,
            num_images=request.num_images,
            style=request.style,
            model_type=request.model_type,
            custom_prompt=base_prompt if request.custom_prompt or transcription.ai_generated_summary else None,
            custom_instructions=request.custom_instructions,
            seed=request.seed
        )
        
        # 4. MinIO'ya yükle
        storage = get_storage_service()
        image_urls = []
        
        # Unique timestamp for cache busting
        import time
        timestamp = int(time.time())
        
        for i, image_bytes in enumerate(result["images"]):
            # Filename with timestamp - prevents browser cache issues
            filename = f"generated_{transcription.id}_{timestamp}_{i}_{result['style']}.png"
            
            # Upload to MinIO
            url = storage.upload_file_bytes(
                file_bytes=image_bytes,
                filename=filename,
                content_type="image/png"
            )
            
            # Save to database
            generated_image = GeneratedImage(
                transcription_id=transcription.id,
                user_id=current_user.id,
                prompt=result["prompt"],
                style=request.style,
                model_type=request.model_type,
                seed=request.seed,
                image_url=url,
                filename=filename,
                file_size=len(image_bytes)
            )
            db.add(generated_image)
            image_urls.append(url)
        
        db.commit()
        
        # 5. Kredi düş - Her görsel için 1 kredi
        try:
            credits_service.deduct_credits(
                user_id=current_user.id,
                amount=required_credits,
                operation_type=OperationType.IMAGE_GENERATION,
                description=f"Generated {request.num_images} image(s) - {request.style} style",
                transcription_id=transcription.id,
                metadata={
                    "num_images": request.num_images,
                    "style": request.style,
                    "prompt_length": len(result["prompt"]),
                    "seed": request.seed
                }
            )
            logger.info(f"💰 Deducted {required_credits} credits from user {current_user.id}")
        except Exception as e:
            logger.error(f"❌ Failed to deduct credits: {e}")
            # Don't rollback images - they're already generated
        
        logger.info(f"✅ Generated {len(image_urls)} image(s) for transcription {transcription.id}")
        
        return ImageGenerationResponse(
            status="success",
            transcription_id=transcription.id,
            prompt=result["prompt"],
            images=image_urls,
            count=len(image_urls),
            style=request.style
        )
        
    except Exception as e:
        logger.error(f"❌ Image generation error: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


@router.get("/transcription/{transcription_id}")
async def get_generated_images(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transkriptin tüm görsellerini getir
    
    **Example:**
    ```
    GET /api/v1/images/transcription/123
    ```
    
    **Response:**
    ```json
    {
      "transcription_id": 123,
      "count": 2,
      "images": [
        {
          "id": 1,
          "url": "https://...",
          "prompt": "...",
          "style": "professional",
          "created_at": "2024-01-15T10:30:00Z"
        }
      ]
    }
    ```
    """
    # Check access
    transcription = db.query(Transcription).filter(
        Transcription.id == transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(
            status_code=404,
            detail="Transcription not found or you don't have access"
        )
    
    # Get images
    images = db.query(GeneratedImage).filter(
        GeneratedImage.transcription_id == transcription_id,
        GeneratedImage.is_active == True
    ).order_by(GeneratedImage.created_at.desc()).all()
    
    # Generate fresh URLs from R2 (public URLs have no expiration!)
    storage = get_storage_service()
    
    def get_fresh_url(img: GeneratedImage) -> str:
        """Generate fresh public URL from R2"""
        if not img.filename:
            return img.image_url or ""
        
        try:
            # Use public URL for R2 (permanent, no expiration!)
            fresh_url = storage.get_public_url(img.filename)
            logger.info(f"✅ Generated public URL for {img.filename}")
            return fresh_url
        except Exception as e:
            logger.error(f"❌ Failed to generate URL for {img.filename}: {e}")
            # Fallback to stored URL
            return img.image_url or ""
    
    return {
        "transcription_id": transcription_id,
        "count": len(images),
        "images": [
            {
                "id": img.id,
                "url": get_fresh_url(img),
                "prompt": img.prompt,
                "style": img.style,
                "seed": img.seed,
                "file_size": img.file_size,
                "filename": img.filename,  # Include filename for URL refresh
                "created_at": img.created_at.isoformat() if img.created_at else None
            }
            for img in images
        ]
    }


@router.delete("/image/{image_id}")
async def delete_generated_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Oluşturulmuş görseli sil (soft delete)
    
    **Example:**
    ```
    DELETE /api/v1/images/image/456
    ```
    """
    image = db.query(GeneratedImage).filter(
        GeneratedImage.id == image_id,
        GeneratedImage.user_id == current_user.id
    ).first()
    
    if not image:
        raise HTTPException(
            status_code=404,
            detail="Image not found or you don't have access"
        )
    
    # Soft delete
    image.is_active = False
    db.commit()
    
    logger.info(f"🗑️ Deleted image {image_id} (soft delete)")
    
    return {"status": "success", "message": "Image deleted"}


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Celery task durumunu kontrol et (debug endpoint)
    
    **Example:**
    ```
    GET /api/v1/images/task/a00ad7f4-9342-480e-ae10-f2a2ee343175
    ```
    """
    from app.celery_app import celery_app
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        result = {
            "task_id": task_id,
            "status": task.status,
            "ready": task.ready(),
            "successful": task.successful() if task.ready() else None,
            "failed": task.failed() if task.ready() else None,
        }
        
        # Include result or error if available
        if task.ready():
            if task.successful():
                result["result"] = str(task.result)[:500]  # Truncate
            elif task.failed():
                result["error"] = str(task.result)[:500]
        
        # Include traceback if failed
        if task.failed():
            result["traceback"] = task.traceback[:1000] if task.traceback else None
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Task status check error: {e}")
        return {
            "task_id": task_id,
            "status": "ERROR",
            "error": str(e)
        }


@router.get("/styles")
async def get_available_styles():
    """
    Kullanılabilir görsel stillerini listele
    
    **Example:**
    ```
    GET /api/v1/images/styles
    ```
    """
    image_gen = get_image_generator()
    health = image_gen.health_check()
    
    return {
        "styles": health["available_styles"],
        "descriptions": {
            "professional": "İş/toplantı görselleri, modern ve temiz estetik",
            "artistic": "Sanatsal illüstrasyon, yaratıcı konsept sanatı, canlı renkler",
            "technical": "Teknik diyagram, infografik tarzı, eğitici",
            "minimalist": "Minimalist tasarım, basit kompozisyon, şık",
            "cinematic": "Sinematik ışıklandırma, dramatik atmosfer"
        },
        "service_status": health["status"]
    }
