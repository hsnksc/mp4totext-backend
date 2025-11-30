"""
Sources API Router
Handles CRUD operations for user-generated Sources (Mix Up feature)
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth.utils import get_current_active_user
from app.models.user import User
from app.models.source import Source
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


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
    
    logger.info(f"📋 User {current_user.username} fetched {len(sources)} sources")
    return sources


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
    
    # 3. Prepare content for AI
    combined_content = ""
    for i, item in enumerate(request.source_items, 1):
        combined_content += f"\n\n--- [{item.type.upper()}] {item.title} ---\n"
        combined_content += item.content
    
    # 4. Create prompt
    base_prompt = """You are an expert content synthesizer. Analyze the following content pieces and create a comprehensive, well-structured document that:

1. Identifies key themes and connections between the pieces
2. Synthesizes the information into a coherent narrative
3. Highlights important insights and conclusions
4. Organizes the content in a logical, easy-to-follow structure
5. Uses appropriate headings, bullet points, and formatting

The output should be professional, informative, and valuable to the reader.

Content to synthesize:
"""
    
    if request.custom_instruction:
        base_prompt += f"\n\nAdditional instructions: {request.custom_instruction}\n\n"
    
    full_prompt = base_prompt + combined_content
    
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
