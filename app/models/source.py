"""
Source Model - User-created content from Mix Up feature
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, deferred
from app.database import Base


class Source(Base):
    """
    A Source is user-generated content created by mixing up various transcription outputs
    using GPT-5 Pro (or other AI models).
    
    This content can be:
    - Edited by the user
    - Shared on river.gistify (future feature)
    - Exported in various formats
    - PKB (Personal Knowledge Base) oluşturulabilir
    """
    __tablename__ = "sources"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Source metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Main content
    content = Column(Text, nullable=False)
    
    # Source items that were mixed to create this
    source_items = Column(JSON, nullable=True)  # Array of MixUpItem objects
    
    # AI processing details
    ai_provider = Column(String(50), nullable=True)  # openai, gemini, etc.
    ai_model = Column(String(100), nullable=True)  # gpt-5-pro, etc.
    ai_prompt = Column(Text, nullable=True)  # The prompt used to generate
    
    # Credits used
    credits_used = Column(Float, default=0.0)
    
    # Status
    status = Column(String(50), default="draft")  # draft, published, archived
    
    # River.gistify sharing (future)
    is_public = Column(Boolean, default=False)
    river_post_id = Column(String(100), nullable=True)  # ID in river system
    likes_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    
    # Tags for categorization
    tags = Column(JSON, nullable=True)  # Array of strings
    
    # Linked transcription (optional)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=True)
    
    # PKB (Personal Knowledge Base) fields - all nullable for backward compatibility
    # These columns may not exist in older databases until migration runs
    pkb_enabled = Column(Boolean, default=False, nullable=True)
    pkb_status = Column(String(50), default="not_created", nullable=True)
    pkb_collection_name = Column(String(255), nullable=True)
    pkb_chunk_count = Column(Integer, default=0, nullable=True)
    pkb_embedding_model = Column(String(100), nullable=True)
    pkb_chunk_size = Column(Integer, nullable=True)
    pkb_chunk_overlap = Column(Integer, nullable=True)
    pkb_created_at = Column(DateTime, nullable=True)
    pkb_credits_used = Column(Float, default=0.0, nullable=True)
    pkb_error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sources")
    transcription = relationship("Transcription", back_populates="sources")
    
    # PKB Relationships - lazy='dynamic' to avoid loading issues
    pkb_chunks = relationship("PKBChunk", back_populates="source", cascade="all, delete-orphan", lazy='dynamic')
    pkb_chat_sessions = relationship("PKBChatSession", back_populates="source", cascade="all, delete-orphan", lazy='dynamic')

    def __repr__(self):
        return f"<Source(id={self.id}, title='{self.title[:50]}...', user_id={self.user_id})>"
