"""
RAG (Retrieval Augmented Generation) + PKB (Personal Knowledge Base) Models
=============================================================================
Source, SourceItem, SourceChunk, ChatSession, ChatMessage ve GeneratedDocument modelleri
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, 
    ForeignKey, Enum, JSON, Index
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


# =========================================================================
# ENUMS
# =========================================================================

class SourceStatus(str, enum.Enum):
    """Source durumu"""
    DRAFT = "draft"              # İçerik ekleniyor
    READY = "ready"              # PKB oluşturulmaya hazır
    INDEXING = "indexing"        # PKB oluşturuluyor
    INDEXED = "indexed"          # PKB hazır, sorgulama yapılabilir
    FAILED = "failed"            # PKB oluşturma başarısız
    ARCHIVED = "archived"        # Arşivlenmiş


class SourceType(str, enum.Enum):
    """Source tipi"""
    GENERAL = "general"          # Genel
    PROJECT = "project"          # Proje dökümanları
    MEETING = "meeting"          # Toplantı notları
    LECTURE = "lecture"          # Ders notları
    RESEARCH = "research"        # Araştırma
    LEGAL = "legal"              # Hukuki dökümanlar
    TECHNICAL = "technical"      # Teknik dökümanlar


class SourceItemType(str, enum.Enum):
    """Source item tipi"""
    TRANSCRIPTION = "transcription"
    DOCUMENT = "document"
    NOTE = "note"
    IMAGE = "image"
    VIDEO = "video"
    URL = "url"


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
    COMPARE = "compare"
    TRANSLATE = "translate"
    REWRITE = "rewrite"


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
    PRESENTATION = "presentation"
    EMAIL = "email"
    BLOG = "blog"


# =========================================================================
# RAG SOURCE MODEL (PKB Container)
# =========================================================================

class RAGSource(Base):
    """
    RAG Source - Kullanıcının bilgi kaynağı container'ı
    
    Bu model, kullanıcının oluşturduğu PKB (Personal Knowledge Base) için
    ana container görevi görür. İçerisine transkriptler, dökümanlar,
    notlar ve görseller eklenebilir.
    """
    __tablename__ = "rag_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Temel bilgiler
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(50), default=SourceType.GENERAL.value)
    
    # Durum
    status = Column(String(50), default=SourceStatus.DRAFT.value, index=True)
    
    # İçerik sayıları (denormalized - hızlı erişim için)
    document_count = Column(Integer, default=0)
    transcription_count = Column(Integer, default=0)
    image_count = Column(Integer, default=0)
    note_count = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    
    # Metin istatistikleri
    total_words = Column(Integer, default=0)
    total_characters = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # PKB (Vector Database) bilgileri
    pkb_enabled = Column(Boolean, default=False)
    pkb_status = Column(String(50), default="not_created")  # not_created, creating, ready, failed
    pkb_created_at = Column(DateTime, nullable=True)
    pkb_updated_at = Column(DateTime, nullable=True)
    
    # Vector collection bilgileri
    vector_collection_name = Column(String(255), nullable=True)  # Qdrant collection adı
    vector_count = Column(Integer, default=0)  # Toplam vektör sayısı
    total_chunks = Column(Integer, default=0)
    
    # Embedding ayarları
    embedding_model = Column(String(100), default="text-embedding-3-small")
    embedding_dimensions = Column(Integer, default=1536)
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=50)
    
    # UI/UX
    color = Column(String(20), default="#3B82F6")
    icon = Column(String(50), default="folder")
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)  # ["tag1", "tag2"]
    
    # Kredi takibi
    total_credits_used = Column(Float, default=0.0)
    embedding_credits_used = Column(Float, default=0.0)
    chat_credits_used = Column(Float, default=0.0)
    generation_credits_used = Column(Float, default=0.0)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    user = relationship("User", back_populates="rag_sources")
    items = relationship("RAGSourceItem", back_populates="source", cascade="all, delete-orphan")
    chunks = relationship("RAGSourceChunk", back_populates="source", cascade="all, delete-orphan")
    chat_sessions = relationship("RAGChatSession", back_populates="source", cascade="all, delete-orphan")
    documents = relationship("RAGGeneratedDocument", back_populates="source", cascade="all, delete-orphan")
    
    # Indexler
    __table_args__ = (
        Index('idx_rag_sources_user_status', 'user_id', 'status'),
        Index('idx_rag_sources_user_favorite', 'user_id', 'is_favorite'),
    )
    
    def __repr__(self):
        return f"<RAGSource(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "status": self.status,
            "document_count": self.document_count,
            "transcription_count": self.transcription_count,
            "image_count": self.image_count,
            "note_count": self.note_count,
            "total_items": self.total_items,
            "total_words": self.total_words,
            "total_chunks": self.total_chunks,
            "pkb_enabled": self.pkb_enabled,
            "pkb_status": self.pkb_status,
            "embedding_model": self.embedding_model,
            "color": self.color,
            "icon": self.icon,
            "is_favorite": self.is_favorite,
            "tags": self.tags or [],
            "total_credits_used": self.total_credits_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# =========================================================================
# RAG SOURCE ITEM MODEL
# =========================================================================

class RAGSourceItem(Base):
    """
    Source içindeki her bir içerik öğesi
    
    Bir Source birden fazla item içerebilir:
    - Transkriptler
    - Dökümanlar (PDF, DOCX, TXT)
    - Notlar
    - Görseller (OCR ile)
    """
    __tablename__ = "rag_source_items"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("rag_sources.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Item tipi ve referans
    item_type = Column(String(50), nullable=False)  # transcription, document, note, image
    reference_id = Column(Integer, nullable=True)   # transcription_id veya document_id
    reference_table = Column(String(100), nullable=True)  # "transcriptions", "documents"
    
    # İçerik
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)  # Çıkarılan veya yazılan metin
    content_hash = Column(String(64), nullable=True)  # İçerik değişikliği kontrolü için
    
    # Metin istatistikleri
    word_count = Column(Integer, default=0)
    character_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    
    # İşleme durumu
    status = Column(String(50), default="pending")  # pending, processing, ready, failed
    processing_error = Column(Text, nullable=True)
    
    # Kaynak bilgileri
    file_url = Column(String(1000), nullable=True)
    file_name = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    language = Column(String(10), nullable=True)  # "tr", "en", etc.
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)
    
    # İlişkiler
    source = relationship("RAGSource", back_populates="items")
    chunks = relationship("RAGSourceChunk", back_populates="source_item", cascade="all, delete-orphan")
    
    # Indexler
    __table_args__ = (
        Index('idx_rag_items_source_type', 'source_id', 'item_type'),
        Index('idx_rag_items_reference', 'reference_table', 'reference_id'),
    )
    
    def __repr__(self):
        return f"<RAGSourceItem(id={self.id}, title='{self.title[:30]}...', type='{self.item_type}')>"


# =========================================================================
# RAG SOURCE CHUNK MODEL
# =========================================================================

class RAGSourceChunk(Base):
    """
    Vektörleştirilmiş metin parçaları
    
    Her item, chunking işlemi sonrası birden fazla chunk'a bölünür.
    Her chunk ayrı ayrı vektörleştirilir ve Qdrant'a kaydedilir.
    """
    __tablename__ = "rag_source_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("rag_sources.id"), nullable=False, index=True)
    source_item_id = Column(Integer, ForeignKey("rag_source_items.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Chunk tanımlayıcı (Qdrant point ID olarak da kullanılır)
    chunk_id = Column(String(100), nullable=False, unique=True, index=True)
    chunk_index = Column(Integer, nullable=False)  # Item içindeki sıra
    
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
    vector_point_id = Column(String(100), nullable=True)  # Qdrant'taki point ID
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    source = relationship("RAGSource", back_populates="chunks")
    source_item = relationship("RAGSourceItem", back_populates="chunks")
    
    # Indexler
    __table_args__ = (
        Index('idx_rag_chunks_source_item', 'source_id', 'source_item_id'),
        Index('idx_rag_chunks_embedded', 'source_id', 'is_embedded'),
    )
    
    def __repr__(self):
        return f"<RAGSourceChunk(id={self.id}, chunk_id='{self.chunk_id}', tokens={self.token_count})>"


# =========================================================================
# RAG CHAT SESSION MODEL
# =========================================================================

class RAGChatSession(Base):
    """
    RAG Chat oturumu
    
    Kullanıcının bir Source ile yaptığı sohbet oturumu.
    Birden fazla mesaj içerebilir ve bağlam korunur.
    """
    __tablename__ = "rag_chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("rag_sources.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Oturum bilgileri
    title = Column(String(255), default="Yeni Sohbet")
    status = Column(String(50), default=ChatSessionStatus.ACTIVE.value)
    
    # LLM ayarları
    llm_model = Column(String(100), default="gpt-4o-mini")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    top_k = Column(Integer, default=5)  # RAG için alınacak chunk sayısı
    
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
    source = relationship("RAGSource", back_populates="chat_sessions")
    user = relationship("User", back_populates="rag_chat_sessions")
    messages = relationship("RAGChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    # Indexler
    __table_args__ = (
        Index('idx_rag_sessions_source', 'source_id', 'status'),
        Index('idx_rag_sessions_user', 'user_id', 'status'),
    )
    
    def __repr__(self):
        return f"<RAGChatSession(id={self.id}, title='{self.title}', messages={self.message_count})>"


# =========================================================================
# RAG CHAT MESSAGE MODEL
# =========================================================================

class RAGChatMessage(Base):
    """
    Chat mesajı
    
    Kullanıcı soruları ve AI yanıtları.
    AI yanıtları için kullanılan kaynaklar da kaydedilir.
    """
    __tablename__ = "rag_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("rag_chat_sessions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Mesaj bilgileri
    role = Column(String(20), nullable=False)  # user, assistant, system
    message_type = Column(String(50), default=MessageType.CHAT.value)
    content = Column(Text, nullable=False)
    
    # AI yanıtı için ek bilgiler
    sources_used = Column(JSON, nullable=True)  # Kullanılan chunk'ların listesi
    confidence_score = Column(Float, nullable=True)  # 0-1 arası güven skoru
    
    # Token ve kredi bilgileri
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    credits_used = Column(Float, default=0.0)
    
    # İşlem süresi
    processing_time_ms = Column(Integer, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Kullanıcı geri bildirimi
    feedback_rating = Column(Integer, nullable=True)  # 1-5
    feedback_text = Column(Text, nullable=True)
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    session = relationship("RAGChatSession", back_populates="messages")
    
    # Indexler
    __table_args__ = (
        Index('idx_rag_messages_session', 'session_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<RAGChatMessage(id={self.id}, role='{self.role}', tokens={self.total_tokens})>"


# =========================================================================
# RAG GENERATED DOCUMENT MODEL
# =========================================================================

class RAGGeneratedDocument(Base):
    """
    AI tarafından oluşturulan dökümanlar
    
    Source'dan üretilen özet, rapor, quiz, analiz vb. dökümanlar.
    """
    __tablename__ = "rag_generated_documents"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("rag_sources.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Döküman bilgileri
    title = Column(String(500), nullable=False)
    document_type = Column(String(50), nullable=False)  # summary, report, quiz, analysis
    
    # İçerik
    content = Column(Text, nullable=False)
    content_html = Column(Text, nullable=True)  # HTML formatı
    content_markdown = Column(Text, nullable=True)  # Markdown formatı
    
    # AI bilgileri
    llm_model = Column(String(100), nullable=True)
    prompt_used = Column(Text, nullable=True)
    
    # Token ve kredi bilgileri
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    credits_used = Column(Float, default=0.0)
    
    # Export bilgileri
    export_url = Column(String(1000), nullable=True)  # PDF/DOCX export URL
    export_format = Column(String(20), nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    options = Column(JSON, nullable=True)  # Oluşturma seçenekleri
    
    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    source = relationship("RAGSource", back_populates="documents")
    user = relationship("User", back_populates="rag_documents")
    
    # Indexler
    __table_args__ = (
        Index('idx_rag_docs_source_type', 'source_id', 'document_type'),
        Index('idx_rag_docs_user', 'user_id', 'document_type'),
    )
    
    def __repr__(self):
        return f"<RAGGeneratedDocument(id={self.id}, title='{self.title[:30]}...', type='{self.document_type}')>"
