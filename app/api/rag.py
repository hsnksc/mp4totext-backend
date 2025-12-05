"""
Gistify RAG API Endpoints
==========================
Source, PKB (Personal Knowledge Base) ve Chat için API endpoint'leri.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import logging

from app.database import get_db
from app.auth.utils import get_current_active_user
from app.models.user import User
from app.models.rag import (
    RAGSource, RAGSourceItem, RAGSourceChunk,
    RAGChatSession, RAGChatMessage, RAGGeneratedDocument,
    SourceStatus, SourceType, SourceItemType, MessageRole, 
    MessageType, ChatSessionStatus, DocumentType
)
from app.models.transcription import Transcription
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType
from app.services.rag_service import (
    RAGService, TextChunker, EmbeddingService, VectorStoreService, LLMService,
    DocumentGeneratorService, EmbeddingModel, LLMModel,
    EmbeddingResponse, RAGResponse, DocumentResponse
)
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/rag", tags=["RAG & PKB"])


# =========================================================================
# PYDANTIC SCHEMAS
# =========================================================================

class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_type: str = "general"
    tags: List[str] = []
    color: str = "#3B82F6"
    icon: str = "folder"


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_favorite: Optional[bool] = None


class SourceItemAdd(BaseModel):
    item_type: str  # transcription, document, note, image
    reference_id: Optional[int] = None  # transcription_id
    title: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TranscriptionItemAdd(BaseModel):
    """Add transcription to source"""
    transcription_id: int


class PKBCreateRequest(BaseModel):
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = Field(default=512, ge=128, le=2048)
    chunk_overlap: int = Field(default=50, ge=0, le=200)


class ChatCreateRequest(BaseModel):
    source_id: int
    title: Optional[str] = "Yeni Sohbet"
    llm_model: str = "gpt-4o-mini"


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    llm_model: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_k: int = Field(default=5, ge=1, le=20)


class DocumentGenerateRequest(BaseModel):
    document_type: str = Field(..., pattern="^(summary|report|quiz|analysis)$")
    length: str = "medium"  # short, medium, long
    style: str = "professional"
    options: Dict[str, Any] = {}


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)


# =========================================================================
# CREDIT CALCULATION
# =========================================================================

CREDIT_RATES = {
    # Embedding (per 1K tokens)
    "embedding_small": 0.1,
    "embedding_large": 0.5,
    "embedding_gemini": 0.5,
    
    # Chat (per query)
    "chat_gpt4o_mini": 1.0,
    "chat_gpt4o": 5.0,
    "chat_gemini_pro": 3.0,
    "chat_gemini_flash": 1.0,
    
    # PKB (per chunk)
    "pkb_per_chunk": 0.1,
    
    # Document Generation
    "summary_short": 2.0,
    "summary_medium": 3.0,
    "summary_long": 5.0,
    "report": 25.0,
    "quiz_10": 15.0,
    "quiz_20": 25.0,
    "analysis": 20.0,
    "compare": 15.0,
    "translate": 10.0,
    "rewrite": 8.0,
}


def calculate_credits(operation: str, **kwargs) -> float:
    """Kredi hesapla"""
    
    if operation == "embedding":
        tokens = kwargs.get("tokens", 0)
        model = kwargs.get("model", "small")
        rate = CREDIT_RATES.get(f"embedding_{model}", 0.1)
        return (tokens / 1000) * rate
    
    elif operation == "chat":
        model = kwargs.get("model", "gpt4o_mini")
        return CREDIT_RATES.get(f"chat_{model}", 1.0)
    
    elif operation == "pkb":
        chunk_count = kwargs.get("chunk_count", 0)
        return chunk_count * CREDIT_RATES["pkb_per_chunk"]
    
    elif operation in CREDIT_RATES:
        return CREDIT_RATES[operation]
    
    return 0.0


def check_user_credits(user: User, required_credits: float):
    """Kullanıcının yeterli kredisi var mı kontrol et"""
    if user.credits < required_credits:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Yetersiz kredi. Gerekli: {required_credits:.2f}, Mevcut: {user.credits:.2f}"
        )


# =========================================================================
# SERVICE FACTORIES
# =========================================================================

def create_rag_service() -> RAGService:
    """RAG Service factory"""
    return RAGService(
        qdrant_url=settings.QDRANT_URL,
        qdrant_api_key=settings.QDRANT_API_KEY
    )


def create_document_generator() -> DocumentGeneratorService:
    """Document Generator factory"""
    return DocumentGeneratorService()


# =========================================================================
# SOURCE ENDPOINTS
# =========================================================================

@router.post("/sources", status_code=status.HTTP_201_CREATED)
async def create_source(
    data: SourceCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Yeni source oluştur"""
    logger.info(f"🚀 Creating source: {data.name} for user {current_user.id}")
    
    # Validate source_type
    try:
        source_type_enum = SourceType(data.source_type)
    except ValueError:
        source_type_enum = SourceType.GENERAL
    
    source = RAGSource(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        source_type=source_type_enum,
        status=SourceStatus.DRAFT,
        tags=data.tags,
        color=data.color,
        icon=data.icon
    )
    
    db.add(source)
    db.commit()
    db.refresh(source)
    
    logger.info(f"✅ Source created: id={source.id}")
    
    return {
        "id": source.id,
        "user_id": source.user_id,
        "name": source.name,
        "description": source.description,
        "source_type": source.source_type.value,
        "status": source.status.value,
        "tags": source.tags,
        "color": source.color,
        "icon": source.icon,
        "document_count": 0,
        "transcription_count": 0,
        "image_count": 0,
        "total_items": 0,
        "total_words": 0,
        "total_chunks": 0,
        "pkb_enabled": source.pkb_enabled,
        "pkb_status": "not_created",
        "is_favorite": source.is_favorite,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None
    }


@router.get("/sources")
async def list_sources(
    skip: int = 0,
    limit: int = 20,
    is_favorite: Optional[bool] = None,
    source_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının source'larını listele"""
    
    query = db.query(RAGSource).filter(RAGSource.user_id == current_user.id)
    
    if is_favorite is not None:
        query = query.filter(RAGSource.is_favorite == is_favorite)
    
    if source_type:
        try:
            source_type_enum = SourceType(source_type)
            query = query.filter(RAGSource.source_type == source_type_enum)
        except ValueError:
            pass
    
    total = query.count()
    sources = query.order_by(RAGSource.updated_at.desc()).offset(skip).limit(limit).all()
    
    items = []
    for s in sources:
        # Count items
        item_count = db.query(RAGSourceItem).filter(RAGSourceItem.source_id == s.id).count()
        transcription_count = db.query(RAGSourceItem).filter(
            RAGSourceItem.source_id == s.id,
            RAGSourceItem.item_type == SourceItemType.TRANSCRIPTION
        ).count()
        document_count = db.query(RAGSourceItem).filter(
            RAGSourceItem.source_id == s.id,
            RAGSourceItem.item_type == SourceItemType.DOCUMENT
        ).count()
        
        items.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "source_type": s.source_type.value if s.source_type else "general",
            "status": s.status.value if s.status else "draft",
            "document_count": document_count,
            "transcription_count": transcription_count,
            "total_items": item_count,
            "total_words": s.total_words or 0,
            "total_chunks": s.total_chunks or 0,
            "pkb_enabled": s.pkb_enabled,
            "pkb_status": "ready" if s.pkb_enabled else "not_created",
            "is_favorite": s.is_favorite,
            "color": s.color,
            "icon": s.icon,
            "tags": s.tags or [],
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/sources/{source_id}")
async def get_source(
    source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source detaylarını getir"""
    
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source bulunamadı"
        )
    
    # Count items by type
    items = db.query(RAGSourceItem).filter(RAGSourceItem.source_id == source_id).all()
    transcription_count = sum(1 for i in items if i.item_type == SourceItemType.TRANSCRIPTION)
    document_count = sum(1 for i in items if i.item_type == SourceItemType.DOCUMENT)
    note_count = sum(1 for i in items if i.item_type == SourceItemType.NOTE)
    image_count = sum(1 for i in items if i.item_type == SourceItemType.IMAGE)
    
    # Count chunks
    chunk_count = db.query(RAGSourceChunk).filter(
        RAGSourceChunk.source_id == source_id
    ).count()
    
    return {
        "id": source.id,
        "name": source.name,
        "description": source.description,
        "source_type": source.source_type.value if source.source_type else "general",
        "status": source.status.value if source.status else "draft",
        "document_count": document_count,
        "transcription_count": transcription_count,
        "note_count": note_count,
        "image_count": image_count,
        "total_items": len(items),
        "total_words": source.total_words or 0,
        "total_characters": source.total_characters or 0,
        "total_chunks": chunk_count,
        "total_tokens": source.total_tokens or 0,
        "pkb_enabled": source.pkb_enabled,
        "pkb_status": "ready" if source.pkb_enabled else "not_created",
        "pkb_created_at": source.pkb_created_at.isoformat() if source.pkb_created_at else None,
        "vector_collection_name": source.vector_collection_name,
        "vector_count": chunk_count,
        "embedding_model": source.embedding_model,
        "embedding_dimensions": source.embedding_dimensions,
        "chunk_size": source.chunk_size or 512,
        "chunk_overlap": source.chunk_overlap or 50,
        "tags": source.tags or [],
        "color": source.color,
        "icon": source.icon,
        "is_favorite": source.is_favorite,
        "total_credits_used": float(source.total_credits_used) if source.total_credits_used else 0.0,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None
    }


@router.put("/sources/{source_id}")
async def update_source(
    source_id: int,
    data: SourceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source güncelle"""
    
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source bulunamadı"
        )
    
    if data.name is not None:
        source.name = data.name
    if data.description is not None:
        source.description = data.description
    if data.tags is not None:
        source.tags = data.tags
    if data.color is not None:
        source.color = data.color
    if data.icon is not None:
        source.icon = data.icon
    if data.is_favorite is not None:
        source.is_favorite = data.is_favorite
    
    source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(source)
    
    return {"status": "updated", "id": source.id}


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source sil (PKB dahil)"""
    
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source bulunamadı"
        )
    
    # Delete from Qdrant if PKB exists
    if source.pkb_enabled and source.vector_collection_name:
        try:
            rag_service = create_rag_service()
            rag_service.delete_knowledge_base(current_user.id, source_id)
            logger.info(f"✅ PKB deleted from Qdrant: {source.vector_collection_name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete PKB from Qdrant: {e}")
    
    # Delete chunks
    db.query(RAGSourceChunk).filter(RAGSourceChunk.source_id == source_id).delete()
    
    # Delete items
    db.query(RAGSourceItem).filter(RAGSourceItem.source_id == source_id).delete()
    
    # Delete chat sessions and messages
    sessions = db.query(RAGChatSession).filter(RAGChatSession.source_id == source_id).all()
    for session in sessions:
        db.query(RAGChatMessage).filter(RAGChatMessage.session_id == session.id).delete()
    db.query(RAGChatSession).filter(RAGChatSession.source_id == source_id).delete()
    
    # Delete generated documents
    db.query(RAGGeneratedDocument).filter(RAGGeneratedDocument.source_id == source_id).delete()
    
    # Delete source
    db.delete(source)
    db.commit()
    
    logger.info(f"✅ Source deleted: id={source_id}")
    
    return {"status": "deleted", "id": source_id}


# =========================================================================
# SOURCE ITEMS ENDPOINTS
# =========================================================================

@router.get("/sources/{source_id}/items")
async def list_source_items(
    source_id: int,
    skip: int = 0,
    limit: int = 50,
    item_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source içindeki öğeleri listele"""
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    query = db.query(RAGSourceItem).filter(RAGSourceItem.source_id == source_id)
    
    if item_type:
        try:
            item_type_enum = SourceItemType(item_type)
            query = query.filter(RAGSourceItem.item_type == item_type_enum)
        except ValueError:
            pass
    
    total = query.count()
    items = query.order_by(RAGSourceItem.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": item.id,
                "source_id": item.source_id,
                "item_type": item.item_type.value if item.item_type else "note",
                "reference_id": item.reference_id,
                "title": item.title,
                "content_preview": (item.content[:200] + "...") if item.content and len(item.content) > 200 else item.content,
                "word_count": item.word_count or 0,
                "is_indexed": item.is_indexed,
                "metadata": item.metadata,
                "created_at": item.created_at.isoformat() if item.created_at else None
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/sources/{source_id}/items")
async def add_item_to_source(
    source_id: int,
    data: SourceItemAdd,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source'a içerik ekle"""
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    # Validate item_type
    try:
        item_type_enum = SourceItemType(data.item_type)
    except ValueError:
        item_type_enum = SourceItemType.NOTE
    
    # Create item
    item = RAGSourceItem(
        source_id=source_id,
        item_type=item_type_enum,
        reference_id=data.reference_id,
        title=data.title,
        content=data.content,
        word_count=len(data.content.split()) if data.content else 0,
        metadata=data.metadata
    )
    
    db.add(item)
    
    # Update source word count
    if data.content:
        source.total_words = (source.total_words or 0) + len(data.content.split())
        source.total_characters = (source.total_characters or 0) + len(data.content)
    
    source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    return {
        "id": item.id,
        "source_id": source_id,
        "item_type": item.item_type.value,
        "title": item.title,
        "word_count": item.word_count,
        "is_indexed": item.is_indexed,
        "created_at": item.created_at.isoformat() if item.created_at else None
    }


@router.post("/sources/{source_id}/transcriptions")
async def add_transcription_to_source(
    source_id: int,
    data: TranscriptionItemAdd,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source'a transkripsiyon ekle"""
    
    # Verify source ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    # Verify transcription ownership
    transcription = db.query(Transcription).filter(
        Transcription.id == data.transcription_id,
        Transcription.user_id == current_user.id
    ).first()
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transkripsiyon bulunamadı")
    
    # Check if already added
    existing = db.query(RAGSourceItem).filter(
        RAGSourceItem.source_id == source_id,
        RAGSourceItem.reference_id == data.transcription_id,
        RAGSourceItem.item_type == SourceItemType.TRANSCRIPTION
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Bu transkripsiyon zaten eklenmiş")
    
    # Get transcription content
    content = transcription.text or transcription.result or ""
    
    # Create item
    item = RAGSourceItem(
        source_id=source_id,
        item_type=SourceItemType.TRANSCRIPTION,
        reference_id=data.transcription_id,
        title=transcription.filename or f"Transkripsiyon #{data.transcription_id}",
        content=content,
        word_count=len(content.split()) if content else 0,
        metadata={
            "filename": transcription.filename,
            "duration": transcription.duration,
            "language": transcription.language,
            "status": transcription.status
        }
    )
    
    db.add(item)
    
    # Update source stats
    if content:
        source.total_words = (source.total_words or 0) + len(content.split())
        source.total_characters = (source.total_characters or 0) + len(content)
    
    source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    
    logger.info(f"✅ Transcription {data.transcription_id} added to source {source_id}")
    
    return {
        "id": item.id,
        "source_id": source_id,
        "transcription_id": data.transcription_id,
        "title": item.title,
        "word_count": item.word_count,
        "created_at": item.created_at.isoformat() if item.created_at else None
    }


@router.delete("/sources/{source_id}/items/{item_id}")
async def remove_item_from_source(
    source_id: int,
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source'dan öğe kaldır"""
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    item = db.query(RAGSourceItem).filter(
        RAGSourceItem.id == item_id,
        RAGSourceItem.source_id == source_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Öğe bulunamadı")
    
    # Update source stats
    if item.content:
        source.total_words = max(0, (source.total_words or 0) - (item.word_count or 0))
        source.total_characters = max(0, (source.total_characters or 0) - len(item.content))
    
    # Delete related chunks
    db.query(RAGSourceChunk).filter(RAGSourceChunk.item_id == item_id).delete()
    
    db.delete(item)
    source.updated_at = datetime.utcnow()
    db.commit()
    
    return {"status": "deleted", "item_id": item_id}


# =========================================================================
# PKB (Personal Knowledge Base) ENDPOINTS
# =========================================================================

@router.post("/sources/{source_id}/pkb/create")
async def create_pkb(
    source_id: int,
    data: PKBCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Source için PKB (Personal Knowledge Base) oluştur
    
    Bu işlem:
    1. Source içindeki tüm içerikleri toplar
    2. Metinleri chunk'lara ayırır
    3. Her chunk için embedding oluşturur
    4. Vektörleri Qdrant'a kaydeder
    """
    logger.info(f"🚀 Creating PKB for source {source_id}")
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    # Get all items
    items = db.query(RAGSourceItem).filter(RAGSourceItem.source_id == source_id).all()
    
    if not items:
        raise HTTPException(status_code=400, detail="Source'da içerik yok")
    
    # Calculate estimated chunks and credits
    total_content = " ".join([item.content or "" for item in items])
    total_words = len(total_content.split())
    estimated_chunks = max(1, total_words // (data.chunk_size // 5))  # Rough estimate
    
    estimated_credits = calculate_credits("pkb", chunk_count=estimated_chunks)
    estimated_credits += calculate_credits("embedding", tokens=estimated_chunks * 500, model="small")
    
    # Check credits
    check_user_credits(current_user, estimated_credits)
    
    # Update source settings
    source.embedding_model = data.embedding_model
    source.chunk_size = data.chunk_size
    source.chunk_overlap = data.chunk_overlap
    source.status = SourceStatus.INDEXING
    db.commit()
    
    # Queue background task
    from app.workers.rag_worker import create_pkb_task
    task = create_pkb_task.apply_async(
        args=[source_id, current_user.id, data.dict()],
        queue='default'
    )
    
    return {
        "status": "processing",
        "task_id": task.id,
        "message": "PKB oluşturma başlatıldı",
        "source_id": source_id,
        "estimated_chunks": estimated_chunks,
        "estimated_credits": round(estimated_credits, 2),
        "embedding_model": data.embedding_model,
        "chunk_size": data.chunk_size,
        "chunk_overlap": data.chunk_overlap
    }


@router.get("/sources/{source_id}/pkb/status")
async def get_pkb_status(
    source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """PKB durumunu sorgula"""
    
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    chunk_count = db.query(RAGSourceChunk).filter(
        RAGSourceChunk.source_id == source_id
    ).count()
    
    total_tokens = db.query(func.sum(RAGSourceChunk.token_count)).filter(
        RAGSourceChunk.source_id == source_id
    ).scalar() or 0
    
    return {
        "source_id": source_id,
        "pkb_enabled": source.pkb_enabled,
        "pkb_status": source.status.value if source.status else "draft",
        "vector_count": chunk_count,
        "chunk_count": chunk_count,
        "embedding_model": source.embedding_model,
        "embedding_dimensions": source.embedding_dimensions,
        "collection_name": source.vector_collection_name,
        "chunk_size": source.chunk_size,
        "chunk_overlap": source.chunk_overlap,
        "last_updated": source.pkb_created_at.isoformat() if source.pkb_created_at else None,
        "total_tokens_embedded": total_tokens,
        "credits_used": float(source.total_credits_used) if source.total_credits_used else 0.0
    }


@router.delete("/sources/{source_id}/pkb")
async def delete_pkb(
    source_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """PKB'yi sil"""
    
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    # Delete from Qdrant
    if source.vector_collection_name:
        try:
            rag_service = create_rag_service()
            rag_service.delete_knowledge_base(current_user.id, source_id)
            logger.info(f"✅ PKB deleted from Qdrant: {source.vector_collection_name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete from Qdrant: {e}")
    
    # Delete chunks from DB
    db.query(RAGSourceChunk).filter(RAGSourceChunk.source_id == source_id).delete()
    
    # Reset source PKB settings
    source.pkb_enabled = False
    source.vector_collection_name = None
    source.total_chunks = 0
    source.status = SourceStatus.READY
    db.commit()
    
    return {
        "status": "deleted",
        "message": "PKB başarıyla silindi",
        "source_id": source_id
    }


# =========================================================================
# CHAT ENDPOINTS
# =========================================================================

@router.post("/chat/sessions", status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    data: ChatCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Yeni chat oturumu başlat"""
    
    # Verify source ownership and PKB status
    source = db.query(RAGSource).filter(
        RAGSource.id == data.source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    if not source.pkb_enabled:
        raise HTTPException(status_code=400, detail="Bu source için PKB oluşturulmamış")
    
    session = RAGChatSession(
        user_id=current_user.id,
        source_id=data.source_id,
        title=data.title,
        llm_model=data.llm_model,
        status=ChatSessionStatus.ACTIVE
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "source_id": session.source_id,
        "source_name": source.name,
        "title": session.title,
        "llm_model": session.llm_model,
        "status": session.status.value,
        "message_count": 0,
        "total_credits_used": 0,
        "created_at": session.created_at.isoformat() if session.created_at else None
    }


@router.get("/chat/sessions")
async def list_chat_sessions(
    source_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Chat oturumlarını listele"""
    
    query = db.query(RAGChatSession).filter(RAGChatSession.user_id == current_user.id)
    
    if source_id:
        query = query.filter(RAGChatSession.source_id == source_id)
    
    total = query.count()
    sessions = query.order_by(RAGChatSession.updated_at.desc()).offset(skip).limit(limit).all()
    
    items = []
    for s in sessions:
        source = db.query(RAGSource).filter(RAGSource.id == s.source_id).first()
        message_count = db.query(RAGChatMessage).filter(RAGChatMessage.session_id == s.id).count()
        
        items.append({
            "id": s.id,
            "source_id": s.source_id,
            "source_name": source.name if source else "Unknown",
            "title": s.title,
            "llm_model": s.llm_model,
            "status": s.status.value if s.status else "active",
            "message_count": message_count,
            "total_credits_used": float(s.total_credits_used) if s.total_credits_used else 0,
            "last_message_at": s.updated_at.isoformat() if s.updated_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Chat oturumu detaylarını getir"""
    
    session = db.query(RAGChatSession).filter(
        RAGChatSession.id == session_id,
        RAGChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    
    source = db.query(RAGSource).filter(RAGSource.id == session.source_id).first()
    message_count = db.query(RAGChatMessage).filter(RAGChatMessage.session_id == session_id).count()
    
    return {
        "id": session.id,
        "source_id": session.source_id,
        "source_name": source.name if source else "Unknown",
        "title": session.title,
        "llm_model": session.llm_model,
        "temperature": session.temperature,
        "top_k": session.top_k,
        "status": session.status.value if session.status else "active",
        "message_count": message_count,
        "total_credits_used": float(session.total_credits_used) if session.total_credits_used else 0,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None
    }


@router.post("/chat/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: int,
    data: ChatMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Chat mesajı gönder ve RAG yanıtı al"""
    
    # Get session
    session = db.query(RAGChatSession).filter(
        RAGChatSession.id == session_id,
        RAGChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    
    # Get source
    source = db.query(RAGSource).filter(RAGSource.id == session.source_id).first()
    if not source or not source.pkb_enabled:
        raise HTTPException(status_code=400, detail="PKB aktif değil")
    
    # Calculate credits
    llm_key = (data.llm_model or session.llm_model or "gpt-4o-mini").replace("-", "_")
    required_credits = calculate_credits("chat", model=llm_key)
    check_user_credits(current_user, required_credits)
    
    # Save user message
    user_message = RAGChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        message_type=MessageType.TEXT,
        content=data.message
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)
    
    # Perform RAG query
    try:
        rag_service = create_rag_service()
        
        # Map model names
        llm_model = LLMModel.GPT4O_MINI
        if data.llm_model == "gpt-4o":
            llm_model = LLMModel.GPT4O
        elif data.llm_model == "gemini-pro":
            llm_model = LLMModel.GEMINI_PRO
        elif data.llm_model == "gemini-flash":
            llm_model = LLMModel.GEMINI_FLASH
        
        response = rag_service.query(
            user_id=current_user.id,
            source_id=session.source_id,
            question=data.message,
            embedding_model=EmbeddingModel.OPENAI_SMALL,
            llm_model=llm_model,
            top_k=data.top_k,
            temperature=data.temperature
        )
        
        # Save assistant message
        assistant_message = RAGChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.TEXT,
            content=response.answer,
            sources_used=response.sources,
            confidence_score=response.confidence_score,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            credits_used=required_credits
        )
        db.add(assistant_message)
        
        # Deduct credits AFTER success
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=required_credits,
            operation_type=OperationType.RAG_CHAT,
            description=f"RAG Chat: {data.message[:50]}",
            metadata={"session_id": session_id, "model": llm_key}
        )
        
        # Update session
        session.total_credits_used = (session.total_credits_used or 0) + required_credits
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(assistant_message)
        
        return {
            "user_message": {
                "id": user_message.id,
                "role": "user",
                "content": user_message.content,
                "created_at": user_message.created_at.isoformat() if user_message.created_at else None
            },
            "assistant_message": {
                "id": assistant_message.id,
                "role": "assistant",
                "content": response.answer,
                "sources_used": response.sources,
                "confidence_score": response.confidence_score,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
                "processing_time_ms": response.processing_time_ms,
                "credits_used": required_credits,
                "created_at": assistant_message.created_at.isoformat() if assistant_message.created_at else None
            }
        }
        
    except Exception as e:
        logger.error(f"❌ RAG query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG sorgusu başarısız: {str(e)}"
        )


@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_messages(
    session_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Chat mesaj geçmişini getir"""
    
    # Verify ownership
    session = db.query(RAGChatSession).filter(
        RAGChatSession.id == session_id,
        RAGChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    
    query = db.query(RAGChatMessage).filter(RAGChatMessage.session_id == session_id)
    total = query.count()
    messages = query.order_by(RAGChatMessage.created_at.asc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": m.id,
                "role": m.role.value if m.role else "user",
                "content": m.content,
                "sources_used": m.sources_used,
                "confidence_score": m.confidence_score,
                "tokens_used": (m.input_tokens or 0) + (m.output_tokens or 0),
                "credits_used": float(m.credits_used) if m.credits_used else 0,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in messages
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Chat oturumunu sil"""
    
    session = db.query(RAGChatSession).filter(
        RAGChatSession.id == session_id,
        RAGChatSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    
    # Delete messages
    db.query(RAGChatMessage).filter(RAGChatMessage.session_id == session_id).delete()
    
    # Delete session
    db.delete(session)
    db.commit()
    
    return {"status": "deleted", "session_id": session_id}


# =========================================================================
# DOCUMENT GENERATION ENDPOINTS
# =========================================================================

@router.post("/sources/{source_id}/generate")
async def generate_document(
    source_id: int,
    data: DocumentGenerateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source'dan doküman oluştur (özet, rapor, quiz, analiz)"""
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    if not source.pkb_enabled:
        raise HTTPException(status_code=400, detail="Bu source için PKB oluşturulmamış")
    
    # Calculate credits
    credit_key = f"{data.document_type}_{data.length}" if data.document_type == "summary" else data.document_type
    if data.document_type == "quiz":
        question_count = data.options.get("question_count", 10)
        credit_key = "quiz_10" if question_count <= 10 else "quiz_20"
    
    required_credits = calculate_credits(credit_key)
    check_user_credits(current_user, required_credits)
    
    try:
        generator = create_document_generator()
        
        if data.document_type == "summary":
            result = generator.generate_summary(
                user_id=current_user.id,
                source_id=source_id,
                length=data.length,
                style=data.style
            )
        elif data.document_type == "report":
            result = generator.generate_report(
                user_id=current_user.id,
                source_id=source_id,
                report_type=data.options.get("report_type", "general"),
                sections=data.options.get("sections")
            )
        elif data.document_type == "quiz":
            result = generator.generate_quiz(
                user_id=current_user.id,
                source_id=source_id,
                question_count=data.options.get("question_count", 10),
                question_types=data.options.get("question_types"),
                difficulty=data.options.get("difficulty", "medium")
            )
        elif data.document_type == "analysis":
            result = generator.generate_analysis(
                user_id=current_user.id,
                source_id=source_id,
                analysis_type=data.options.get("analysis_type", "swot"),
                focus_areas=data.options.get("focus_areas")
            )
        else:
            raise HTTPException(status_code=400, detail="Geçersiz doküman tipi")
        
        # Save to database
        doc_type_enum = DocumentType(data.document_type.upper())
        generated_doc = RAGGeneratedDocument(
            user_id=current_user.id,
            source_id=source_id,
            document_type=doc_type_enum,
            title=result.get("title", f"{data.document_type.title()} - {source.name}"),
            content=result.get("content", ""),
            metadata=data.options,
            credits_used=required_credits
        )
        db.add(generated_doc)
        
        # Deduct credits
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=required_credits,
            operation_type=OperationType.RAG_DOCUMENT,
            description=f"RAG Document: {data.document_type}",
            metadata={"source_id": source_id, "document_type": data.document_type}
        )
        
        db.commit()
        db.refresh(generated_doc)
        
        return {
            "id": generated_doc.id,
            "document_type": data.document_type,
            "title": generated_doc.title,
            "content": result.get("content", ""),
            "word_count": result.get("word_count", 0),
            "credits_used": required_credits,
            "created_at": generated_doc.created_at.isoformat() if generated_doc.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Document generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Doküman oluşturma başarısız: {str(e)}"
        )


@router.get("/sources/{source_id}/documents")
async def list_generated_documents(
    source_id: int,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Oluşturulan dokümanları listele"""
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    query = db.query(RAGGeneratedDocument).filter(
        RAGGeneratedDocument.source_id == source_id,
        RAGGeneratedDocument.user_id == current_user.id
    )
    
    total = query.count()
    documents = query.order_by(RAGGeneratedDocument.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": doc.id,
                "document_type": doc.document_type.value.lower() if doc.document_type else "summary",
                "title": doc.title,
                "content_preview": (doc.content[:200] + "...") if doc.content and len(doc.content) > 200 else doc.content,
                "word_count": len(doc.content.split()) if doc.content else 0,
                "credits_used": float(doc.credits_used) if doc.credits_used else 0,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in documents
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }


# =========================================================================
# SEMANTIC SEARCH ENDPOINT
# =========================================================================

@router.post("/sources/{source_id}/search")
async def semantic_search(
    source_id: int,
    data: SemanticSearchRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Source içinde semantic arama yap"""
    
    # Verify ownership
    source = db.query(RAGSource).filter(
        RAGSource.id == source_id,
        RAGSource.user_id == current_user.id
    ).first()
    
    if not source:
        raise HTTPException(status_code=404, detail="Source bulunamadı")
    
    if not source.pkb_enabled:
        raise HTTPException(status_code=400, detail="Bu source için PKB oluşturulmamış")
    
    try:
        rag_service = create_rag_service()
        
        # Get query embedding
        query_embedding = rag_service.embedding_service.get_embedding(
            text=data.query,
            model=EmbeddingModel.OPENAI_SMALL
        )
        
        # Search in Qdrant
        collection_name = source.vector_collection_name or f"user_{current_user.id}_source_{source_id}"
        results = rag_service.vector_store.search(
            collection_name=collection_name,
            query_vector=query_embedding.embedding,
            top_k=data.top_k
        )
        
        return {
            "query": data.query,
            "source_id": source_id,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "score": r.score,
                    "metadata": r.metadata
                }
                for r in results
            ],
            "total": len(results)
        }
        
    except Exception as e:
        logger.error(f"❌ Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Arama başarısız: {str(e)}"
        )


# =========================================================================
# PRICING INFO ENDPOINT
# =========================================================================

@router.get("/pricing")
async def get_pricing_info():
    """Fiyatlandırma bilgilerini getir"""
    
    return {
        "embedding": {
            "text-embedding-3-small": {
                "credits_per_1k_tokens": 0.1,
                "dimensions": 1536,
                "description": "Hızlı ve ekonomik embedding"
            },
            "text-embedding-3-large": {
                "credits_per_1k_tokens": 0.5,
                "dimensions": 3072,
                "description": "Yüksek kalite embedding"
            }
        },
        "chat": {
            "gpt-4o-mini": {
                "credits_per_query": 1.0,
                "description": "Hızlı ve ekonomik sohbet"
            },
            "gpt-4o": {
                "credits_per_query": 5.0,
                "description": "En gelişmiş GPT modeli"
            },
            "gemini-pro": {
                "credits_per_query": 3.0,
                "description": "Google Gemini Pro"
            },
            "gemini-flash": {
                "credits_per_query": 1.0,
                "description": "Hızlı Gemini modeli"
            }
        },
        "document_generation": {
            "summary_short": {"credits": 2.0, "description": "Kısa özet (1 paragraf)"},
            "summary_medium": {"credits": 3.0, "description": "Orta özet (1 sayfa)"},
            "summary_long": {"credits": 5.0, "description": "Detaylı özet"},
            "report": {"credits": 25.0, "description": "Kapsamlı rapor"},
            "quiz_10": {"credits": 15.0, "description": "10 soruluk quiz"},
            "quiz_20": {"credits": 25.0, "description": "20 soruluk quiz"},
            "analysis": {"credits": 20.0, "description": "Derinlemesine analiz"}
        },
        "pkb": {
            "creation": {
                "credits_per_chunk": 0.1,
                "description": "PKB oluşturma (chunk başına)"
            }
        }
    }


# =========================================================================
# STATS ENDPOINT
# =========================================================================

@router.get("/stats")
async def get_rag_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Kullanıcının RAG istatistiklerini getir"""
    
    source_count = db.query(RAGSource).filter(RAGSource.user_id == current_user.id).count()
    pkb_count = db.query(RAGSource).filter(
        RAGSource.user_id == current_user.id,
        RAGSource.pkb_enabled == True
    ).count()
    chat_count = db.query(RAGChatSession).filter(RAGChatSession.user_id == current_user.id).count()
    doc_count = db.query(RAGGeneratedDocument).filter(RAGGeneratedDocument.user_id == current_user.id).count()
    
    total_chunks = db.query(func.sum(RAGSource.total_chunks)).filter(
        RAGSource.user_id == current_user.id
    ).scalar() or 0
    
    total_credits = db.query(func.sum(RAGSource.total_credits_used)).filter(
        RAGSource.user_id == current_user.id
    ).scalar() or 0
    
    return {
        "source_count": source_count,
        "pkb_count": pkb_count,
        "chat_session_count": chat_count,
        "generated_document_count": doc_count,
        "total_chunks": total_chunks,
        "total_credits_used": float(total_credits)
    }
