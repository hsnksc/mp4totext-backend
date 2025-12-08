"""
Sources API Router
Handles CRUD operations for user-generated Sources (Mix Up feature)
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
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
    
    # PKB fields (optional - may not exist in older records)
    pkb_enabled: Optional[bool] = None
    pkb_status: Optional[str] = None
    pkb_collection_name: Optional[str] = None
    pkb_chunk_count: Optional[int] = None
    pkb_embedding_model: Optional[str] = None
    pkb_created_at: Optional[datetime] = None
    pkb_credits_used: Optional[float] = None
    pkb_error_message: Optional[str] = None
    
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

def source_to_response(source: Source) -> dict:
    """
    Safely convert Source model to response dict.
    Handles missing PKB columns gracefully.
    """
    response = {
        "id": source.id,
        "user_id": source.user_id,
        "title": source.title,
        "description": source.description,
        "content": source.content,
        "source_items": source.source_items,
        "ai_provider": source.ai_provider,
        "ai_model": source.ai_model,
        "credits_used": source.credits_used or 0.0,
        "status": source.status,
        "is_public": source.is_public,
        "tags": source.tags,
        "transcription_id": source.transcription_id,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
    }
    
    # PKB fields - safely access (may not exist in DB)
    try:
        response["pkb_enabled"] = getattr(source, 'pkb_enabled', None)
        response["pkb_status"] = getattr(source, 'pkb_status', None)
        response["pkb_collection_name"] = getattr(source, 'pkb_collection_name', None)
        response["pkb_chunk_count"] = getattr(source, 'pkb_chunk_count', None)
        response["pkb_embedding_model"] = getattr(source, 'pkb_embedding_model', None)
        response["pkb_created_at"] = getattr(source, 'pkb_created_at', None)
        response["pkb_credits_used"] = getattr(source, 'pkb_credits_used', None)
        response["pkb_error_message"] = getattr(source, 'pkb_error_message', None)
    except Exception:
        # PKB columns don't exist yet
        response["pkb_enabled"] = None
        response["pkb_status"] = None
        response["pkb_collection_name"] = None
        response["pkb_chunk_count"] = None
        response["pkb_embedding_model"] = None
        response["pkb_created_at"] = None
        response["pkb_credits_used"] = None
        response["pkb_error_message"] = None
    
    return response


@router.get("")
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
    try:
        # Only select core columns that definitely exist
        from sqlalchemy import text
        
        # Use raw SQL to avoid SQLAlchemy trying to access PKB columns
        sql = text("""
            SELECT id, user_id, title, description, content, source_items,
                   ai_provider, ai_model, credits_used, status, is_public,
                   tags, transcription_id, created_at, updated_at
            FROM sources
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = db.execute(sql, {
            "user_id": current_user.id,
            "limit": limit,
            "skip": skip
        })
        
        sources = []
        for row in result:
            source_dict = {
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "description": row[3],
                "content": row[4],
                "source_items": row[5],
                "ai_provider": row[6],
                "ai_model": row[7],
                "credits_used": row[8] or 0.0,
                "status": row[9],
                "is_public": row[10],
                "tags": row[11],
                "transcription_id": row[12],
                "created_at": row[13],
                "updated_at": row[14],
                # PKB fields - not available without migration
                "pkb_enabled": None,
                "pkb_status": None,
                "pkb_collection_name": None,
                "pkb_chunk_count": None,
                "pkb_embedding_model": None,
                "pkb_created_at": None,
                "pkb_credits_used": None,
                "pkb_error_message": None,
            }
            sources.append(source_dict)
        
        logger.info(f"📋 User {current_user.username} fetched {len(sources)} sources")
        return sources
    except Exception as e:
        logger.error(f"❌ Error fetching sources: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sources: {str(e)}"
        )


@router.get("/{source_id}")
async def get_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific Source by ID
    """
    from sqlalchemy import text
    
    # Use raw SQL to avoid SQLAlchemy trying to access PKB columns
    sql = text("""
        SELECT id, user_id, title, description, content, source_items,
               ai_provider, ai_model, credits_used, status, is_public,
               tags, transcription_id, created_at, updated_at
        FROM sources
        WHERE id = :source_id AND user_id = :user_id
    """)
    
    result = db.execute(sql, {
        "source_id": source_id,
        "user_id": current_user.id
    })
    
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source_dict = {
        "id": row[0],
        "user_id": row[1],
        "title": row[2],
        "description": row[3],
        "content": row[4],
        "source_items": row[5],
        "ai_provider": row[6],
        "ai_model": row[7],
        "credits_used": row[8] or 0.0,
        "status": row[9],
        "is_public": row[10],
        "tags": row[11],
        "transcription_id": row[12],
        "created_at": row[13],
        "updated_at": row[14],
        # PKB fields - not available without migration
        "pkb_enabled": None,
        "pkb_status": None,
        "pkb_collection_name": None,
        "pkb_chunk_count": None,
        "pkb_embedding_model": None,
        "pkb_created_at": None,
        "pkb_credits_used": None,
        "pkb_error_message": None,
    }
    
    return source_dict


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
    
    # 5. Call AI service using GeminiService with provider/model routing
    # This ensures all providers use the user-selected model
    try:
        result = None
        logger.info(f"🤖 Calling AI: provider={request.ai_provider}, model={request.ai_model}")
        
        # Use GeminiService which handles all providers with model routing
        from app.services.gemini_service import GeminiService
        service = GeminiService(preferred_provider=request.ai_provider, preferred_model=request.ai_model)
        
        if not service.is_enabled():
            raise Exception(f"{request.ai_provider.upper()} service not configured. Check API key.")
        
        logger.info(f"📡 Calling {request.ai_provider.upper()} with model {request.ai_model}...")
        response = await service.enhance_text(full_prompt, language=content_language)
        result = response.get("enhanced_text", "")
        
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


# ============================================================================
# PKB (Personal Knowledge Base) ENDPOINTS
# ============================================================================

class PKBCreateRequest(BaseModel):
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 512
    chunk_overlap: int = 50


class PKBStatusResponse(BaseModel):
    pkb_enabled: bool
    pkb_status: str
    chunk_count: int = 0
    embedding_model: Optional[str] = None
    credits_used: float = 0.0
    error_message: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/{source_id}/pkb/status")
async def get_pkb_status(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get PKB status for a source
    """
    from sqlalchemy import text
    
    # First verify source exists
    check_sql = text("SELECT id FROM sources WHERE id = :source_id AND user_id = :user_id")
    check_result = db.execute(check_sql, {"source_id": source_id, "user_id": current_user.id})
    if not check_result.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Try to get PKB status (columns may not exist)
    try:
        sql = text("""
            SELECT pkb_enabled, pkb_status, pkb_chunk_count, 
                   pkb_embedding_model, pkb_credits_used, pkb_error_message, pkb_created_at
            FROM sources
            WHERE id = :source_id
        """)
        result = db.execute(sql, {"source_id": source_id})
        row = result.fetchone()
        
        if row:
            return {
                "pkb_enabled": bool(row[0]) if row[0] is not None else False,
                "pkb_status": row[1] or "not_created",
                "chunk_count": row[2] or 0,
                "embedding_model": row[3],
                "credits_used": float(row[4]) if row[4] else 0.0,
                "error_message": row[5],
                "created_at": row[6].isoformat() if row[6] else None
            }
    except Exception as e:
        # PKB columns don't exist yet - this is expected before migration
        logger.info(f"ℹ️ PKB columns not available yet: {e}")
    
    # Return default PKB status (not created / migration pending)
    return {
        "pkb_enabled": False,
        "pkb_status": "not_created",
        "chunk_count": 0,
        "embedding_model": None,
        "credits_used": 0.0,
        "error_message": None,
        "created_at": None
    }


@router.post("/{source_id}/pkb/create")
async def create_pkb(
    source_id: int,
    request: PKBCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create PKB (Personal Knowledge Base) for a source
    """
    from sqlalchemy import text
    import uuid
    
    # Lazy import - will fail gracefully if rag_service has issues
    try:
        # Try imports one by one to identify which one fails
        logger.info("🔍 Attempting to import rag_service components...")
        
        try:
            from app.services.rag_service import TextChunker
            logger.info("✅ TextChunker imported successfully")
        except Exception as e1:
            logger.error(f"❌ TextChunker import failed: {type(e1).__name__}: {e1}")
            raise
        
        try:
            from app.services.rag_service import EmbeddingService
            logger.info("✅ EmbeddingService imported successfully")
        except Exception as e2:
            logger.error(f"❌ EmbeddingService import failed: {type(e2).__name__}: {e2}")
            raise
        
        try:
            from app.services.rag_service import VectorStoreService
            logger.info("✅ VectorStoreService imported successfully")
        except Exception as e3:
            logger.error(f"❌ VectorStoreService import failed: {type(e3).__name__}: {e3}")
            raise
            
    except Exception as e:
        logger.error(f"❌ Failed to import rag_service: {type(e).__name__}: {e}")
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Traceback: {tb}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Knowledge Base service is not available: {type(e).__name__}: {str(e)}"
        )
    
    from app.settings import get_settings
    settings = get_settings()
    
    # First check if source exists (basic columns only)
    check_sql = text("SELECT id, content, title FROM sources WHERE id = :source_id AND user_id = :user_id")
    check_result = db.execute(check_sql, {"source_id": source_id, "user_id": current_user.id})
    source_row = check_result.fetchone()
    
    if not source_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source_id_db, content, title = source_row
    
    # Check content
    if not content or len(content.strip()) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source content too short for PKB (minimum 100 characters)"
        )
    
    # Try to check PKB status (columns may not exist)
    pkb_enabled = False
    pkb_status = "not_created"
    try:
        pkb_sql = text("SELECT pkb_enabled, pkb_status FROM sources WHERE id = :source_id")
        pkb_result = db.execute(pkb_sql, {"source_id": source_id})
        pkb_row = pkb_result.fetchone()
        if pkb_row:
            pkb_enabled = bool(pkb_row[0]) if pkb_row[0] is not None else False
            pkb_status = pkb_row[1] or "not_created"
    except Exception as e:
        # PKB columns don't exist - need migration
        logger.warning(f"⚠️ PKB columns don't exist, migration required: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge Base feature is not available yet. Database migration is required."
        )
    
    # Check if already has PKB
    if pkb_enabled and pkb_status == "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PKB already exists for this source"
        )
    
    # Calculate credits (estimate)
    content_length = len(content)
    estimated_chunks = content_length // request.chunk_size + 1
    credits_needed = estimated_chunks * 0.001  # 0.001 credits per chunk
    
    # Check credits
    if current_user.credits < credits_needed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Need {credits_needed:.3f}, have {current_user.credits:.3f}"
        )
    
    # Update source status using raw SQL
    collection_name = f"source_{source_id}_{uuid.uuid4().hex[:8]}"
    try:
        update_sql = text("""
            UPDATE sources SET
                pkb_status = :status,
                pkb_collection_name = :collection,
                pkb_embedding_model = :model,
                pkb_chunk_size = :chunk_size,
                pkb_chunk_overlap = :chunk_overlap,
                updated_at = :updated_at
            WHERE id = :source_id
        """)
        db.execute(update_sql, {
            "status": "processing",
            "collection": collection_name,
            "model": request.embedding_model,
            "chunk_size": request.chunk_size,
            "chunk_overlap": request.chunk_overlap,
            "updated_at": datetime.utcnow(),
            "source_id": source_id
        })
        db.commit()
    except Exception as e:
        logger.error(f"❌ Failed to update source for PKB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update source: {str(e)}"
        )
    
    # Start background task
    background_tasks.add_task(
        process_pkb_creation,
        source_id=source_id,
        user_id=current_user.id,
        content=content,  # Using content from raw SQL query above
        collection_name=collection_name,
        embedding_model=request.embedding_model,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap
    )
    
    logger.info(f"🚀 PKB creation started for source {source_id}")
    
    return {
        "success": True,
        "message": "PKB creation started",
        "source_id": source_id,
        "status": "processing"
    }


async def process_pkb_creation(
    source_id: int,
    user_id: int,
    content: str,
    collection_name: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int
):
    """
    Background task to create PKB
    """
    from app.database import SessionLocal
    from app.services.rag_service import TextChunker, EmbeddingService, VectorStoreService
    from app.services.credit_service import get_credit_service
    
    db = SessionLocal()
    
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.error(f"❌ Source {source_id} not found")
            return
        
        # Chunk the content
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunk_results = chunker.chunk_text(content)
        
        # Extract text from chunk results
        chunk_texts = [chunk.content for chunk in chunk_results]
        
        logger.info(f"📦 Created {len(chunk_texts)} chunks for source {source_id}")
        
        # Get embeddings (sync method, no await)
        embedding_service = EmbeddingService()
        from app.services.rag_service import EmbeddingModel
        embedding_results = embedding_service.get_embeddings_batch(
            texts=chunk_texts,
            model=EmbeddingModel.OPENAI_SMALL
        )
        
        # Extract embedding vectors
        embeddings = [result.embedding for result in embedding_results]
        
        logger.info(f"🔢 Generated {len(embeddings)} embeddings")
        
        # Store in vector database (sync methods)
        vector_store = VectorStoreService()
        vector_store.create_collection(collection_name, dimensions=len(embeddings[0]))
        
        # Prepare points for Qdrant
        import uuid
        points = [
            {
                "id": str(uuid.uuid4()),
                "vector": embeddings[i],
                "payload": {
                    "text": chunk_texts[i],
                    "source_id": source_id,
                    "chunk_idx": i
                }
            }
            for i in range(len(chunk_texts))
        ]
        
        vector_store.upsert_vectors(
            collection_name=collection_name,
            points=points
        )
        
        logger.info(f"💾 Stored vectors in collection {collection_name}")
        
        # Calculate and deduct credits
        credits_used = len(chunk_texts) * 0.001
        credit_service = get_credit_service(db)
        # Use AI_ENHANCEMENT temporarily until rag_pkb_creation is added to PostgreSQL enum
        credit_service.deduct_credits(
            user_id=user_id,
            amount=credits_used,
            operation_type=OperationType.AI_ENHANCEMENT,  # TODO: Change to RAG_PKB_CREATION after enum migration
            description=f"PKB created for source: {source.title[:50]}",
            metadata={"source_id": source_id, "chunk_count": len(chunk_texts), "type": "rag_pkb_creation"}
        )
        
        # Update source
        source.pkb_enabled = True
        source.pkb_status = "ready"
        source.pkb_chunk_count = len(chunk_texts)
        source.pkb_credits_used = credits_used
        source.pkb_created_at = datetime.utcnow()
        source.pkb_error_message = None
        source.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ PKB created for source {source_id}: {len(chunk_texts)} chunks, {credits_used:.4f} credits")
        
    except Exception as e:
        logger.error(f"❌ PKB creation failed for source {source_id}: {e}")
        source = db.query(Source).filter(Source.id == source_id).first()
        if source:
            source.pkb_status = "error"
            source.pkb_error_message = str(e)
            source.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.delete("/{source_id}/pkb")
async def delete_pkb(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete PKB for a source
    """
    from app.services.rag_service import VectorStoreService
    from sqlalchemy import text
    
    # Query PKB status using raw SQL
    try:
        sql = text("""
            SELECT id, pkb_enabled, pkb_collection_name
            FROM sources
            WHERE id = :source_id AND user_id = :user_id
        """)
        result = db.execute(sql, {"source_id": source_id, "user_id": current_user.id})
        row = result.fetchone()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PKB feature requires database migration"
        )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source_id_db, pkb_enabled, pkb_collection_name = row
    
    if not pkb_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PKB exists for this source"
        )
    
    # Delete collection from vector store
    if pkb_collection_name:
        try:
            vector_store = VectorStoreService()
            await vector_store.delete_collection(pkb_collection_name)
            logger.info(f"🗑️ Deleted collection {pkb_collection_name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete collection: {e}")
    
    # Reset PKB fields using raw SQL
    try:
        update_sql = text("""
            UPDATE sources SET
                pkb_enabled = 0,
                pkb_status = 'not_created',
                pkb_collection_name = NULL,
                pkb_chunk_count = 0,
                pkb_created_at = NULL,
                pkb_error_message = NULL,
                updated_at = :updated_at
            WHERE id = :source_id
        """)
        db.execute(update_sql, {"updated_at": datetime.utcnow(), "source_id": source_id})
        db.commit()
    except Exception as e:
        logger.error(f"❌ Failed to reset PKB fields: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete PKB: {str(e)}"
        )
    
    logger.info(f"🗑️ PKB deleted for source {source_id}")
    
    return {"success": True, "message": "PKB deleted"}


@router.post("/{source_id}/pkb/chat")
async def chat_with_pkb(
    source_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Chat with source PKB using RAG
    """
    from app.services.rag_service import VectorStoreService, EmbeddingService, LLMService
    from app.services.credit_service import get_credit_service
    from sqlalchemy import text
    
    # Query PKB status using raw SQL
    try:
        sql = text("""
            SELECT id, pkb_enabled, pkb_status, pkb_collection_name, pkb_embedding_model
            FROM sources
            WHERE id = :source_id AND user_id = :user_id
        """)
        result = db.execute(sql, {"source_id": source_id, "user_id": current_user.id})
        row = result.fetchone()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PKB feature requires database migration"
        )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source_id_db, pkb_enabled, pkb_status, pkb_collection_name, pkb_embedding_model = row
    
    if not pkb_enabled or pkb_status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PKB not ready for this source"
        )
    
    message = request.get("message", "").strip()
    llm_model = request.get("llm_model", "gpt-4o-mini")
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is required"
        )
    
    # Minimum credit check (actual cost calculated after LLM call)
    min_credits_needed = 0.005  # Minimum cost per chat
    if current_user.credits < min_credits_needed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits"
        )
    
    try:
        # Get query embedding (sync method)
        embedding_service = EmbeddingService()
        from app.services.rag_service import EmbeddingModel
        query_result = embedding_service.get_embedding(
            text=message,
            model=EmbeddingModel.OPENAI_SMALL
        )
        query_vector = query_result.embedding
        logger.info(f"🔍 Query embedding generated for: {message[:50]}...")
        
        # Search vector store (sync method)
        vector_store = VectorStoreService()
        results = vector_store.search(
            collection_name=pkb_collection_name,
            query_vector=query_vector,
            top_k=5,
            score_threshold=0.3  # Lower threshold for better recall
        )
        
        logger.info(f"📊 Vector search returned {len(results)} results for collection {pkb_collection_name}")
        for i, r in enumerate(results):
            logger.info(f"  Result {i+1}: score={r.score:.3f}, content_len={len(r.content)}")
        
        # Build context from SearchResult objects
        context_chunks = [r.content for r in results]
        context = "\n\n---\n\n".join(context_chunks)
        
        # Check if we got meaningful context
        no_context_found = not context.strip() or len(results) == 0
        
        if no_context_found:
            logger.warning(f"⚠️ No context found for query: {message[:50]}")
            context = "No relevant context found in the knowledge base."
        
        # Generate response with LLM (sync method)
        llm_service = LLMService()
        from app.services.rag_service import LLMModel
        llm_model_enum = LLMModel.GPT4O_MINI if "mini" in llm_model.lower() else LLMModel.GPT4O
        
        # Add special instruction if no context found
        system_prompt = f"Answer the user's question based on the following context:\n\n{context}"
        if no_context_found:
            system_prompt = """You are a helpful assistant. The knowledge base search returned no relevant results.
            
Please respond with a helpful message explaining that:
1. No relevant information was found in the knowledge base for this query
2. This might happen if the PKB was just created and vector indexing is still in progress (takes 1-2 minutes)
3. Suggest the user to wait a moment and try again, or rephrase their question

Respond in the same language as the user's question."""
        
        response_text, input_tokens, output_tokens = llm_service.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            model=llm_model_enum
        )
        
        # Calculate credits based on token usage
        # Pricing: 
        #   - Embedding: 0.001 credits per query
        #   - GPT-4o-mini: $0.15/1M input, $0.60/1M output -> ~0.0001 per 1K tokens
        #   - GPT-4o: $2.50/1M input, $10/1M output -> ~0.001 per 1K tokens
        embedding_cost = 0.001  # Per query embedding
        
        if "mini" in llm_model.lower():
            # GPT-4o-mini pricing (cheaper)
            input_cost = (input_tokens / 1000) * 0.0002   # $0.15/1M = ~0.0002 per 1K
            output_cost = (output_tokens / 1000) * 0.0008  # $0.60/1M = ~0.0008 per 1K
        else:
            # GPT-4o pricing (more expensive)
            input_cost = (input_tokens / 1000) * 0.003    # $2.50/1M = ~0.003 per 1K
            output_cost = (output_tokens / 1000) * 0.012  # $10/1M = ~0.012 per 1K
        
        credits_used = embedding_cost + input_cost + output_cost
        credits_used = round(max(credits_used, 0.005), 4)  # Minimum 0.005, round to 4 decimals
        
        logger.info(f"💰 Chat cost breakdown: embedding={embedding_cost:.4f}, input={input_cost:.4f} ({input_tokens} tokens), output={output_cost:.4f} ({output_tokens} tokens), total={credits_used:.4f}")
        
        # Deduct credits
        credit_service = get_credit_service(db)
        # Use AI_ENHANCEMENT temporarily until rag_chat is added to PostgreSQL enum
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=credits_used,
            operation_type=OperationType.AI_ENHANCEMENT,  # TODO: Change to RAG_CHAT after enum migration
            description=f"PKB chat: {message[:50]}",
            metadata={
                "source_id": source_id, 
                "llm_model": llm_model, 
                "type": "rag_chat",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        )
        
        return {
            "response": response_text,
            "sources_used": [{"content_preview": r.content[:100], "score": r.score} for r in results],
            "credits_used": credits_used,
            "no_context_warning": no_context_found,
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        }
        
    except Exception as e:
        logger.error(f"❌ PKB chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


# ============================================================================
# PKB SEMANTIC SEARCH
# ============================================================================

@router.post("/{source_id}/pkb/search")
async def search_pkb(
    source_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Semantic search in PKB - find most relevant passages
    """
    from app.services.rag_service import VectorStoreService, EmbeddingService
    from app.services.credit_service import get_credit_service
    from sqlalchemy import text
    
    # Query PKB status
    try:
        sql = text("""
            SELECT id, pkb_enabled, pkb_status, pkb_collection_name
            FROM sources
            WHERE id = :source_id AND user_id = :user_id
        """)
        result = db.execute(sql, {"source_id": source_id, "user_id": current_user.id})
        row = result.fetchone()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PKB feature requires database migration"
        )
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    source_id_db, pkb_enabled, pkb_status, pkb_collection_name = row
    
    if not pkb_enabled or pkb_status != "ready":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PKB not ready")
    
    query = request.get("query", "").strip()
    top_k = min(request.get("top_k", 10), 50)  # Max 50 results
    score_threshold = request.get("score_threshold", 0.3)
    
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query is required")
    
    # Credit check (search is cheap - only embedding cost)
    credits_needed = 0.002
    if current_user.credits < credits_needed:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")
    
    try:
        # Get query embedding
        embedding_service = EmbeddingService()
        from app.services.rag_service import EmbeddingModel
        query_result = embedding_service.get_embedding(text=query, model=EmbeddingModel.OPENAI_SMALL)
        query_vector = query_result.embedding
        
        # Search vector store
        vector_store = VectorStoreService()
        results = vector_store.search(
            collection_name=pkb_collection_name,
            query_vector=query_vector,
            top_k=top_k,
            score_threshold=score_threshold
        )
        
        logger.info(f"🔍 Search returned {len(results)} results for: {query[:50]}...")
        
        # Deduct credits
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=credits_needed,
            operation_type=OperationType.AI_ENHANCEMENT,
            description=f"PKB search: {query[:50]}",
            metadata={"source_id": source_id, "type": "rag_search", "results_count": len(results)}
        )
        
        return {
            "results": [
                {
                    "content": r.content,
                    "score": round(r.score, 4),
                    "metadata": r.metadata
                }
                for r in results
            ],
            "total_results": len(results),
            "credits_used": credits_needed
        }
        
    except Exception as e:
        logger.error(f"❌ PKB search failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)}")


# ============================================================================
# PKB SUMMARIZE
# ============================================================================

@router.post("/{source_id}/pkb/summarize")
async def summarize_pkb(
    source_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate summary of PKB content
    Styles: bullet_points, paragraph, executive, detailed
    """
    from app.services.rag_service import VectorStoreService, LLMService
    from app.services.credit_service import get_credit_service
    from sqlalchemy import text
    
    # Query PKB status
    try:
        sql = text("""
            SELECT id, title, pkb_enabled, pkb_status, pkb_collection_name, pkb_chunk_count
            FROM sources
            WHERE id = :source_id AND user_id = :user_id
        """)
        result = db.execute(sql, {"source_id": source_id, "user_id": current_user.id})
        row = result.fetchone()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PKB migration required")
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    source_id_db, title, pkb_enabled, pkb_status, pkb_collection_name, chunk_count = row
    
    if not pkb_enabled or pkb_status != "ready":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PKB not ready")
    
    style = request.get("style", "paragraph")  # bullet_points, paragraph, executive, detailed
    llm_model = request.get("llm_model", "gpt-4o-mini")
    max_chunks = min(request.get("max_chunks", 20), 50)  # Limit chunks to process
    
    # Summarization costs more (uses LLM)
    min_credits = 0.05
    if current_user.credits < min_credits:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")
    
    try:
        # Get all chunks from PKB (or sample if too many)
        vector_store = VectorStoreService()
        all_points = vector_store.get_all_points(collection_name=pkb_collection_name, limit=max_chunks)
        
        if not all_points:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No content found in PKB")
        
        # Build content from chunks
        content_parts = [p.get("content", "") for p in all_points if p.get("content")]
        full_content = "\n\n".join(content_parts)
        
        # Truncate if too long (max ~12K tokens worth)
        max_chars = 48000  # ~12K tokens
        if len(full_content) > max_chars:
            full_content = full_content[:max_chars] + "\n\n[Content truncated...]"
        
        # Style-specific prompts
        style_prompts = {
            "bullet_points": "Create a comprehensive bullet-point summary. Use clear hierarchical structure with main points and sub-points.",
            "paragraph": "Write a well-structured summary in paragraph form. Include all key information in a flowing narrative.",
            "executive": "Create a concise executive summary (3-5 paragraphs). Focus on the most important insights and conclusions.",
            "detailed": "Provide a detailed summary covering all major topics. Include specific examples and data points where available."
        }
        
        system_prompt = f"""You are a professional summarizer. {style_prompts.get(style, style_prompts['paragraph'])}
        
The document is titled: "{title or 'Untitled'}"

Summarize the following content:"""
        
        # Generate summary with LLM
        llm_service = LLMService()
        from app.services.rag_service import LLMModel
        llm_model_enum = LLMModel.GPT4O_MINI if "mini" in llm_model.lower() else LLMModel.GPT4O
        
        summary, input_tokens, output_tokens = llm_service.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_content}
            ],
            model=llm_model_enum
        )
        
        # Calculate credits
        if "mini" in llm_model.lower():
            input_cost = (input_tokens / 1000) * 0.0002
            output_cost = (output_tokens / 1000) * 0.0008
        else:
            input_cost = (input_tokens / 1000) * 0.003
            output_cost = (output_tokens / 1000) * 0.012
        
        credits_used = round(max(input_cost + output_cost, 0.01), 4)
        
        logger.info(f"📝 Summarization: {len(content_parts)} chunks, {input_tokens}+{output_tokens} tokens, {credits_used} credits")
        
        # Deduct credits
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=credits_used,
            operation_type=OperationType.AI_ENHANCEMENT,
            description=f"PKB summarize: {title or 'Untitled'}",
            metadata={"source_id": source_id, "type": "rag_summarize", "style": style, "chunks_used": len(content_parts)}
        )
        
        return {
            "summary": summary,
            "style": style,
            "chunks_processed": len(content_parts),
            "credits_used": credits_used,
            "token_usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PKB summarize failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Summarization failed: {str(e)}")


# ============================================================================
# PKB GENERATE QUESTIONS
# ============================================================================

@router.post("/{source_id}/pkb/generate-questions")
async def generate_questions_from_pkb(
    source_id: int,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate quiz/exam questions from PKB content
    Types: multiple_choice, true_false, short_answer, essay, flashcard
    """
    from app.services.rag_service import VectorStoreService, LLMService
    from app.services.credit_service import get_credit_service
    from sqlalchemy import text
    
    # Query PKB status
    try:
        sql = text("""
            SELECT id, title, pkb_enabled, pkb_status, pkb_collection_name
            FROM sources
            WHERE id = :source_id AND user_id = :user_id
        """)
        result = db.execute(sql, {"source_id": source_id, "user_id": current_user.id})
        row = result.fetchone()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PKB migration required")
    
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    
    source_id_db, title, pkb_enabled, pkb_status, pkb_collection_name = row
    
    if not pkb_enabled or pkb_status != "ready":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PKB not ready")
    
    # Parameters
    question_count = min(request.get("count", 10), 30)  # Max 30 questions
    question_type = request.get("type", "mixed")  # multiple_choice, true_false, short_answer, essay, flashcard, mixed
    difficulty = request.get("difficulty", "medium")  # easy, medium, hard
    language = request.get("language", "en")  # Output language
    llm_model = request.get("llm_model", "gpt-4o-mini")
    
    # Credit check
    min_credits = 0.05
    if current_user.credits < min_credits:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")
    
    try:
        # Get content from PKB
        vector_store = VectorStoreService()
        all_points = vector_store.get_all_points(collection_name=pkb_collection_name, limit=30)
        
        if not all_points:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No content found in PKB")
        
        # Build content
        content_parts = [p.get("content", "") for p in all_points if p.get("content")]
        full_content = "\n\n".join(content_parts)
        
        # Truncate if needed
        max_chars = 40000
        if len(full_content) > max_chars:
            full_content = full_content[:max_chars]
        
        # Question type instructions
        type_instructions = {
            "multiple_choice": "Generate multiple choice questions with 4 options (A, B, C, D). Mark the correct answer.",
            "true_false": "Generate true/false statements. Indicate whether each is True or False.",
            "short_answer": "Generate questions that require short (1-3 sentence) answers.",
            "essay": "Generate essay questions that require detailed explanations.",
            "flashcard": "Generate flashcard pairs with a term/question on one side and definition/answer on the other.",
            "mixed": "Generate a mix of multiple choice, true/false, and short answer questions."
        }
        
        difficulty_instructions = {
            "easy": "Create basic recall questions testing fundamental concepts.",
            "medium": "Create questions requiring understanding and application of concepts.",
            "hard": "Create challenging questions requiring analysis and critical thinking."
        }
        
        lang_map = {"en": "English", "tr": "Turkish", "de": "German", "fr": "French", "es": "Spanish"}
        output_lang = lang_map.get(language, language)
        
        system_prompt = f"""You are an expert educator creating {question_type} questions.

{type_instructions.get(question_type, type_instructions['mixed'])}
{difficulty_instructions.get(difficulty, difficulty_instructions['medium'])}

Generate exactly {question_count} questions in {output_lang}.

The source material is titled: "{title or 'Untitled'}"

Format your response as a JSON array with this structure:
[
  {{
    "question": "The question text",
    "type": "{question_type if question_type != 'mixed' else 'multiple_choice|true_false|short_answer'}",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],  // Only for multiple_choice
    "answer": "The correct answer",
    "explanation": "Brief explanation of why this is correct"
  }}
]

Ensure questions cover different topics from the content."""

        # Generate questions with LLM
        llm_service = LLMService()
        from app.services.rag_service import LLMModel
        llm_model_enum = LLMModel.GPT4O_MINI if "mini" in llm_model.lower() else LLMModel.GPT4O
        
        response_text, input_tokens, output_tokens = llm_service.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate questions from this content:\n\n{full_content}"}
            ],
            model=llm_model_enum
        )
        
        # Parse JSON response
        import json
        try:
            # Clean response - remove markdown code blocks if present
            clean_response = response_text.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            questions = json.loads(clean_response.strip())
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw text
            questions = [{"raw_response": response_text, "parse_error": True}]
        
        # Calculate credits
        if "mini" in llm_model.lower():
            input_cost = (input_tokens / 1000) * 0.0002
            output_cost = (output_tokens / 1000) * 0.0008
        else:
            input_cost = (input_tokens / 1000) * 0.003
            output_cost = (output_tokens / 1000) * 0.012
        
        credits_used = round(max(input_cost + output_cost, 0.01), 4)
        
        logger.info(f"❓ Generated {len(questions) if isinstance(questions, list) else 1} questions, {credits_used} credits")
        
        # Deduct credits
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=credits_used,
            operation_type=OperationType.AI_ENHANCEMENT,
            description=f"PKB questions: {title or 'Untitled'}",
            metadata={"source_id": source_id, "type": "rag_questions", "question_type": question_type, "count": question_count}
        )
        
        return {
            "questions": questions,
            "question_type": question_type,
            "difficulty": difficulty,
            "language": language,
            "credits_used": credits_used,
            "token_usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ PKB generate questions failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Question generation failed: {str(e)}")
