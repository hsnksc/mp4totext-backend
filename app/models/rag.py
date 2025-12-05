"""
RAG (Retrieval Augmented Generation) + PKB (Personal Knowledge Base) Models
=============================================================================

Bu dosya PKB (Personal Knowledge Base) için gereken modelleri içerir.

NOT: Ana Source modeli app/models/source.py'de tanımlıdır.
PKB özellikleri Source modeline eklenmiştir.
Bu dosyadaki modeller sadece chunk'lar ve chat için kullanılır.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, 
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


# =========================================================================
# ENUMS
# =========================================================================

class MessageRole(str, enum.Enum):
    """Mesaj rolü"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageType(str, enum.Enum):
    """Mesaj tipi (AI aksiyonu)"""
    CHAT = "chat"
    SUMMARIZE = "summarize"
    GENERATE = "generate"
    QUIZ = "quiz"
    ANALYZE = "analyze"


class ChatSessionStatus(str, enum.Enum):
    """Chat oturumu durumu"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DocumentType(str, enum.Enum):
    """Oluşturulan döküman tipi"""
    SUMMARY = "summary"
    REPORT = "report"
    QUIZ = "quiz"
    ANALYSIS = "analysis"


# Backward compatibility için eski enum isimleri
class SourceStatus(str, enum.Enum):
    """Source durumu (backward compatibility)"""
    DRAFT = "draft"
    READY = "ready"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class SourceType(str, enum.Enum):
    """Source tipi (backward compatibility)"""
    GENERAL = "general"
    PROJECT = "project"
    MEETING = "meeting"
    LECTURE = "lecture"
    RESEARCH = "research"


class SourceItemType(str, enum.Enum):
    """Source item tipi (backward compatibility)"""
    TRANSCRIPTION = "transcription"
    DOCUMENT = "document"
    NOTE = "note"
    URL = "url"


# =========================================================================
# PKB CHUNK MODEL
# =========================================================================

class PKBChunk(Base):
    """
    PKB Chunk - Source içeriğinin vektörleştirilmiş parçası
    
    Source.content chunking işlemi sonrası birden fazla chunk'a bölünür.
    Her chunk ayrı ayrı vektörleştirilir ve Qdrant'a kaydedilir.
    """
    __tablename__ = "pkb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Chunk tanımlayıcı (Qdrant point ID olarak da kullanılır)
    chunk_id = Column(String(100), nullable=False, unique=True, index=True)
    chunk_index = Column(Integer, nullable=False)  # Source içindeki sıra
    
    # İçerik
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=True)
    
    # Token bilgileri
    token_count = Column(Integer, default=0)
    start_char = Column(Integer, nullable=True)  # Orijinal metindeki başlangıç pozisyonu
    end_char = Column(Integer, nullable=True)
    
    # Embedding bilgileri
    embedding_model = Column(String(100), nullable=True)
    embedding_dimensions = Column(Integer, nullable=True)
    is_embedded = Column(Boolean, default=False)
    embedded_at = Column(DateTime, nullable=True)
    
    # Qdrant bilgileri
    vector_collection = Column(String(255), nullable=True)
    vector_point_id = Column(String(100), nullable=True)
    
    # Chunk metadata (not 'metadata' - it's reserved in SQLAlchemy)
    chunk_metadata = Column(JSON, nullable=True)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    source = relationship("Source", back_populates="pkb_chunks")
    
    # Indexler
    __table_args__ = (
        Index('idx_pkb_chunks_source', 'source_id'),
        Index('idx_pkb_chunks_embedded', 'source_id', 'is_embedded'),
    )
    
    def __repr__(self):
        return f"<PKBChunk(id={self.id}, chunk_id='{self.chunk_id}', tokens={self.token_count})>"


# =========================================================================
# PKB CHAT SESSION MODEL
# =========================================================================

class PKBChatSession(Base):
    """
    PKB Chat oturumu
    
    Kullanıcının bir Source ile yaptığı sohbet oturumu.
    """
    __tablename__ = "pkb_chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Oturum bilgileri
    title = Column(String(255), default="Yeni Sohbet")
    status = Column(String(50), default=ChatSessionStatus.ACTIVE.value)
    
    # LLM ayarları
    llm_model = Column(String(100), default="gpt-4o-mini")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    top_k = Column(Integer, default=5)
    
    # Sistem promptu
    system_prompt = Column(Text, nullable=True)
    
    # İstatistikler
    message_count = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_credits_used = Column(Float, default=0.0)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at = Column(DateTime, nullable=True)
    
    # İlişkiler
    source = relationship("Source", back_populates="pkb_chat_sessions")
    user = relationship("User", back_populates="pkb_chat_sessions")
    messages = relationship("PKBChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    # Indexler
    __table_args__ = (
        Index('idx_pkb_sessions_source', 'source_id', 'status'),
        Index('idx_pkb_sessions_user', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<PKBChatSession(id={self.id}, title='{self.title}', messages={self.message_count})>"


# =========================================================================
# PKB CHAT MESSAGE MODEL
# =========================================================================

class PKBChatMessage(Base):
    """
    PKB Chat mesajı
    """
    __tablename__ = "pkb_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("pkb_chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Mesaj bilgileri
    role = Column(String(20), nullable=False)  # user, assistant, system
    message_type = Column(String(50), default=MessageType.CHAT.value)
    content = Column(Text, nullable=False)
    
    # AI yanıtı için ek bilgiler
    sources_used = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Token ve kredi bilgileri
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    credits_used = Column(Float, default=0.0)
    
    # İşlem süresi
    processing_time_ms = Column(Integer, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    session = relationship("PKBChatSession", back_populates="messages")
    
    # Indexler
    __table_args__ = (
        Index('idx_pkb_messages_session', 'session_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PKBChatMessage(id={self.id}, role='{self.role}', tokens={self.total_tokens})>"


# =========================================================================
# BACKWARD COMPATIBILITY ALIASES
# =========================================================================
# Eski kod uyumluluğu için alias'lar (import hatalarını önlemek için)
RAGSourceChunk = PKBChunk
RAGChatSession = PKBChatSession
RAGChatMessage = PKBChatMessage
