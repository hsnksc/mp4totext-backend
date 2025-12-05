"""
Credit transaction model for tracking credit usage
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class OperationType(str, enum.Enum):
    """Types of credit operations"""
    # Transcription operations
    TRANSCRIPTION = "transcription"
    SPEAKER_RECOGNITION = "speaker_recognition"
    YOUTUBE_DOWNLOAD = "youtube_download"
    
    # AI enhancement operations
    AI_ENHANCEMENT = "ai_enhancement"
    LECTURE_NOTES = "lecture_notes"
    CUSTOM_PROMPT = "custom_prompt"
    EXAM_QUESTIONS = "exam_questions"
    TRANSLATION = "translation"
    
    # Image generation
    IMAGE_GENERATION = "image_generation"
    
    # Video generation
    VIDEO_GENERATION = "video_generation"
    
    # RAG operations
    RAG_PKB_CREATION = "rag_pkb_creation"
    RAG_EMBEDDING = "rag_embedding"
    RAG_CHAT = "rag_chat"
    RAG_DOCUMENT = "rag_document"
    
    # Credit purchase
    PURCHASE = "purchase"
    BONUS = "bonus"
    REFUND = "refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class CreditTransaction(Base):
    """Credit transaction model for tracking all credit movements"""
    
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)  # Float for fractional credits (0.5, 1.5, etc.)
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    description = Column(String, nullable=True)  # Human-readable description
    
    # Related transcription (if applicable)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=True)
    
    # Additional info
    extra_info = Column(String, nullable=True)  # JSON string for additional info (avoid 'metadata' - reserved)
    balance_after = Column(Float, nullable=False)  # Float for fractional credits
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", backref="credit_transactions")
    transcription = relationship("Transcription", backref="credit_transactions")
    
    def __repr__(self):
        return f"<CreditTransaction(id={self.id}, user_id={self.user_id}, amount={self.amount}, type={self.operation_type})>"
