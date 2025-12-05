"""Database models"""

from app.models.user import User
from app.models.transcription import Transcription
from app.models.generated_image import GeneratedImage
from app.models.source import Source
from app.models.rag import (
    PKBChunk, PKBChatSession, PKBChatMessage,
    # Backward compatibility aliases
    RAGSourceChunk, RAGChatSession, RAGChatMessage,
    # Enums
    MessageRole, MessageType, ChatSessionStatus, DocumentType,
    SourceStatus, SourceType, SourceItemType
)

__all__ = [
    "User", "Transcription", "GeneratedImage", "Source",
    # PKB Models
    "PKBChunk", "PKBChatSession", "PKBChatMessage",
    # Backward compatibility
    "RAGSourceChunk", "RAGChatSession", "RAGChatMessage",
    # Enums
    "MessageRole", "MessageType", "ChatSessionStatus", "DocumentType",
    "SourceStatus", "SourceType", "SourceItemType"
]
