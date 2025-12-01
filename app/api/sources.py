"""
Sources API Router
Handles CRUD operations for user-generated Sources (Mix Up feature)
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth.utils import get_current_active_user
from app.models.user import User
from app.models.source import Source
from app.services.credit_service import get_credit_service
from app.services.storage import get_storage_service
from app.models.credit_transaction import OperationType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def refresh_source_media_urls(source: Source) -> Source:
    """
    Refresh URLs for all image and video items in a source.
    For R2 public buckets, URLs are permanent (no expiration).
    For private buckets, generate presigned URLs.
    """
    if not source.source_items:
        return source
    
    storage = get_storage_service()
    if not storage.r2_enabled:
        return source
    
    updated_items = []
    for item in source.source_items:
        item_type = item.get("type")
        metadata = item.get("metadata", {})
        
        # Handle both images and videos
        if item_type in ("image", "video") and metadata:
            # Get URL and filename from metadata
            media_url = metadata.get("imageUrl") or metadata.get("url") or metadata.get("videoUrl")
            filename = metadata.get("filename")
            
            # If no filename, try to extract from URL
            if not filename and media_url:
                # Extract object name from URL patterns:
                # R2: https://xxx.r2.cloudflarestorage.com/bucket/filename.mp4
                # R2 presigned: has ?X-Amz-... params
                # MinIO: https://minio.../mp4totext/filename.png?X-Amz-...
                
                # Try to extract filename from various URL patterns
                match = re.search(r'r2\.dev/([^?]+)', media_url)
                if not match:
                    match = re.search(r'r2\.cloudflarestorage\.com/[^/]+/([^?]+)', media_url)
                if not match:
                    match = re.search(r'/mp4totext/([^?]+)', media_url)
                if match:
                    filename = match.group(1)
            
            # Generate fresh URL if we have filename
            if filename:
                try:
                    fresh_url = storage.get_public_url(filename)
                    # Update metadata with fresh URL
                    if item_type == "image":
                        metadata["imageUrl"] = fresh_url
                    elif item_type == "video":
                        metadata["videoUrl"] = fresh_url
                    metadata["url"] = fresh_url
                    metadata["filename"] = filename
                    item["metadata"] = metadata
                    logger.debug(f"✅ Generated URL for {item_type}: {filename}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to generate URL for {filename}: {e}")
        
        updated_items.append(item)
    
    source.source_items = updated_items
    return source


# Backwards compatibility alias
def refresh_source_image_urls(source: Source) -> Source:
    return refresh_source_media_urls(source)


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class MixUpItemSchema(BaseModel):
    """Schema for a single Mix Up item"""
    id: str
    type: str  # transcript, lecture_notes, exam_questions, custom_prompt, enhanced, summary
    title: str
    content: str
    preview: str
    metadata: Optional[dict] = None


class SourceCreate(BaseModel):
    """Schema for creating a new Source"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    source_items: List[MixUpItemSchema]
    transcription_id: Optional[int] = None
    tags: Optional[List[str]] = None


class SourceUpdate(BaseModel):
    """Schema for updating a Source"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None  # draft, published, archived


class SourceResponse(BaseModel):
    """Schema for Source response"""
    id: int
    user_id: int
    title: str
    description: Optional[str]
    content: str
    source_items: Optional[list]
    ai_provider: Optional[str]
    ai_model: Optional[str]
    credits_used: float
    status: str
    is_public: bool
    tags: Optional[list]
    transcription_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExecuteMixUpRequest(BaseModel):
    """Schema for executing Mix Up with AI"""
    source_items: List[MixUpItemSchema]
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    transcription_id: Optional[int] = None
    tags: Optional[List[str]] = None
    ai_provider: str = "openai"
    ai_model: str = "gpt-5-pro"
    custom_instruction: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=List[SourceResponse])
async def get_user_sources(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all Sources for the current user
    """
    query = db.query(Source).filter(Source.user_id == current_user.id)
    
    if status:
        query = query.filter(Source.status == status)
    
    sources = query.order_by(Source.created_at.desc()).offset(skip).limit(limit).all()
    
    # Refresh presigned URLs for image items
    refreshed_sources = [refresh_source_image_urls(source) for source in sources]
    
    logger.info(f"📋 User {current_user.username} fetched {len(sources)} sources")
    return refreshed_sources


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific Source by ID
    """
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Refresh presigned URLs for image items
    source = refresh_source_image_urls(source)
    
    return source


@router.post("/execute", response_model=SourceResponse)
async def execute_mix_up(
    request: ExecuteMixUpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Execute Mix Up - Combine selected items using AI and create a new Source
    """
    from app.models.ai_model_pricing import AIModelPricing
    
    logger.info(f"🧪 User {current_user.username} executing Mix Up with {len(request.source_items)} items")
    
    # 1. Get AI model pricing
    model = db.query(AIModelPricing).filter(
        AIModelPricing.model_key == request.ai_model,
        AIModelPricing.is_active == True
    ).first()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI model '{request.ai_model}' not found or inactive"
        )
    
    # 2. Calculate credits (base: 5 credits * model multiplier)
    base_credits = 5.0
    required_credits = base_credits * model.credit_multiplier
    
    if current_user.credits < required_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {required_credits:.2f}, Available: {current_user.credits:.2f}"
        )
    
    # 3. Prepare content for AI - separate text and media
    text_content = ""
    image_items = []
    video_items = []
    
    for i, item in enumerate(request.source_items, 1):
        if item.type == "image":
            # Get URL from metadata (could be url or imageUrl)
            img_url = None
            if item.metadata:
                img_url = item.metadata.get("imageUrl") or item.metadata.get("url")
            image_items.append({
                "title": item.title,
                "url": img_url,
                "style": item.metadata.get("style") if item.metadata else None,
                "prompt": item.content[:200] if item.content else ""
            })
        elif item.type == "video":
            video_items.append({
                "title": item.title,
                "url": item.metadata.get("url") if item.metadata else None,
                "duration": item.metadata.get("duration") if item.metadata else None
            })
        else:
            text_content += f"\n\n### {i}. {item.title} ({item.type.upper()})\n"
            text_content += item.content
    
    # 4a. Get transcription language if transcription_id is provided
    content_language = "en"  # Default to English
    language_instruction = ""
    
    if request.transcription_id:
        from app.models.transcription import Transcription
        transcription = db.query(Transcription).filter(
            Transcription.id == request.transcription_id,
            Transcription.user_id == current_user.id
        ).first()
        
        if transcription and transcription.language:
            content_language = transcription.language
            logger.info(f"📝 Using transcription language: {content_language}")
    
    # Map language codes to full names for better AI understanding
    language_names = {
        "tr": "Turkish (Türkçe)",
        "en": "English",
        "de": "German (Deutsch)",
        "fr": "French (Français)",
        "es": "Spanish (Español)",
        "it": "Italian (Italiano)",
        "pt": "Portuguese (Português)",
        "ru": "Russian (Русский)",
        "ar": "Arabic (العربية)",
        "zh": "Chinese (中文)",
        "ja": "Japanese (日本語)",
        "ko": "Korean (한국어)",
    }
    
    language_name = language_names.get(content_language, content_language)
    
    # Only add language instruction if NOT English and no custom instruction overrides it
    if content_language != "en":
        language_instruction = f"""
## ⚠️ CRITICAL: OUTPUT LANGUAGE
**You MUST write the ENTIRE article in {language_name}.**
- All headings, paragraphs, and content must be in {language_name}
- Only exception: technical terms or proper nouns may remain in original language
- This is the source content's original language - maintain it throughout

"""
    
    # 4b. Create comprehensive prompt for shareable content
    base_prompt = f"""You are an expert content creator and researcher. Your task is to create a comprehensive, well-researched, and shareable article based on the provided content.
{language_instruction}
## YOUR MISSION:
Create a professional, engaging, and informative article that could be shared on social media, blogs, or professional platforms.

## CONTENT CREATION GUIDELINES:

### 1. STRUCTURE (Use Markdown formatting)
- Start with an engaging **title** (# heading)
- Write a compelling **introduction** that hooks the reader
- Organize into clear **sections** with descriptive headings (## and ###)
- Include a **summary/conclusion** with key takeaways
- Add **bullet points** for lists and key facts

### 2. CONTENT QUALITY
- **Synthesize** all provided information into a coherent narrative
- **Expand** on key points with additional context and explanations
- **Connect** different pieces of information logically
- **Highlight** important insights, statistics, and conclusions
- Make it **educational** and **valuable** to readers

### 3. WRITING STYLE
- Professional yet accessible tone
- Clear and concise language
- Engaging and reader-friendly
- Use transitions between sections
- Include relevant examples when possible

### 4. FORMATTING FOR SHARING
- Use emojis sparingly but effectively (📌 💡 ⚡ 🔑 etc.)
- Include quotable sentences that could be shared
- Add section dividers for visual clarity
- Keep paragraphs digestible (3-5 sentences max)

### 5. ENHANCEMENTS
- If there are factual claims, acknowledge them
- Suggest areas for further research
- Include actionable insights where applicable
- Make the content timeless when possible

## SOURCE CONTENT TO SYNTHESIZE:
{text_content}
"""

    # Add media references if present
    if image_items:
        base_prompt += f"\n\n## VISUAL CONTENT ({len(image_items)} images):\n"
        for img in image_items:
            base_prompt += f"- 🖼️ **{img['title']}**: {img['prompt']}\n"
        base_prompt += "\nMention these visuals appropriately in your article where relevant.\n"
    
    if video_items:
        base_prompt += f"\n\n## VIDEO CONTENT ({len(video_items)} videos):\n"
        for vid in video_items:
            base_prompt += f"- 🎬 **{vid['title']}**"
            if vid.get('duration'):
                base_prompt += f" ({vid['duration']})"
            base_prompt += "\n"
        base_prompt += "\nReference these videos where appropriate in your article.\n"
    
    # Add custom instruction if provided - this OVERRIDES default language if user specifies differently
    if request.custom_instruction:
        base_prompt += f"""

## 🎯 SPECIAL INSTRUCTIONS FROM USER (HIGHEST PRIORITY):
**These instructions take precedence over all other guidelines, including language settings.**

{request.custom_instruction}

(If the user specifies a different language above, use THAT language instead of the default.)
"""
    
    base_prompt += """

## OUTPUT FORMAT:
Write the article in Markdown format. Make it comprehensive (at least 500 words for complex topics), well-structured, and ready to be shared on professional platforms.

BEGIN YOUR ARTICLE:
"""
    
    full_prompt = base_prompt
    
    # 5. Call AI service
    try:
        result = None
        logger.info(f"🤖 Calling AI: provider={request.ai_provider}, model={request.ai_model}")
        
        if request.ai_provider == "openai":
            from app.services.openai_cleaner_service import get_openai_cleaner
            service = get_openai_cleaner()
            if not service.is_enabled():
                raise Exception("OpenAI service not configured")
            logger.info("📡 Calling OpenAI...")
            response = service.clean_transcript(full_prompt)
            result = response.get("cleaned_text", "")
            
        elif request.ai_provider == "gemini":
            from app.services.gemini_service import get_gemini_service
            service = get_gemini_service()
            if not service.is_enabled():
                raise Exception("Gemini service not configured")
            logger.info("📡 Calling Gemini...")
            response = await service.enhance_text(full_prompt, language="en")
            result = response.get("enhanced_text", "")
            
        elif request.ai_provider == "together":
            from app.services.together_service import get_together_service
            service = get_together_service()
            if not service.is_enabled():
                raise Exception("Together AI service not configured")
            logger.info("📡 Calling Together AI...")
            response = service.clean_transcript(full_prompt)
            result = response.get("cleaned_text", "")
            
        elif request.ai_provider == "groq":
            from app.services.groq_service import get_groq_service
            service = get_groq_service()
            if not service.is_enabled():
                raise Exception("Groq service not configured")
            logger.info("📡 Calling Groq...")
            response = await service.enhance_text(full_prompt, language="en")
            result = response.get("enhanced_text", "")
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown AI provider: {request.ai_provider}"
            )
        
        if not result:
            raise Exception("AI returned empty result")
        
        logger.info(f"✅ AI response received: {len(result)} chars")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ AI processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI processing failed: {str(e)}"
        )
    
    # 6. Deduct credits AFTER success
    credit_service = get_credit_service(db)
    credit_service.deduct_credits(
        user_id=current_user.id,
        amount=required_credits,
        operation_type=OperationType.AI_ENHANCEMENT,
        description=f"Mix Up: {request.title}",
        metadata={
            "provider": request.ai_provider,
            "model": request.ai_model,
            "items_count": len(request.source_items)
        }
    )
    
    # 7. Create Source
    source = Source(
        user_id=current_user.id,
        title=request.title,
        description=request.description,
        content=result,
        source_items=[item.dict() for item in request.source_items],
        ai_provider=request.ai_provider,
        ai_model=request.ai_model,
        ai_prompt=request.custom_instruction,
        credits_used=required_credits,
        status="draft",
        tags=request.tags,
        transcription_id=request.transcription_id
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    logger.info(f"✅ Source created: id={source.id}, title='{source.title}', credits={required_credits}")
    
    return source


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    update_data: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing Source
    """
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Update fields
    if update_data.title is not None:
        source.title = update_data.title
    if update_data.description is not None:
        source.description = update_data.description
    if update_data.content is not None:
        source.content = update_data.content
    if update_data.tags is not None:
        source.tags = update_data.tags
    if update_data.status is not None:
        source.status = update_data.status
        if update_data.status == "published" and not source.published_at:
            source.published_at = datetime.utcnow()
    
    source.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(source)
    
    logger.info(f"📝 Source updated: id={source.id}")
    
    return source


@router.delete("/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a Source
    """
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    db.delete(source)
    db.commit()
    
    logger.info(f"🗑️ Source deleted: id={source_id}")
    
    return {"success": True, "message": "Source deleted"}


@router.post("/{source_id}/publish")
async def publish_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Publish a Source (make it ready for River sharing)
    """
    source = db.query(Source).filter(
        Source.id == source_id,
        Source.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source.status = "published"
    source.published_at = datetime.utcnow()
    source.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(source)
    
    logger.info(f"🌊 Source published: id={source.id}")
    
    return {"success": True, "message": "Source published", "source_id": source.id}
