"""
Generated Image Model
AI-generated images from transcripts
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class GeneratedImage(Base):
    """AI-generated images from transcripts"""
    __tablename__ = "generated_images"
    
    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # For easy user queries
    
    # Image generation info
    prompt = Column(Text, nullable=False)  # Image generation prompt
    style = Column(String(50), nullable=False, default="professional")  # Image style
    model_type = Column(String(20), nullable=False, default="sdxl")  # Model: sdxl, flux
    seed = Column(Integer, nullable=True)  # Random seed (for reproducibility)
    
    # Storage
    image_url = Column(String(500), nullable=False)  # MinIO URL
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)  # Image file size in bytes
    
    # Status
    is_active = Column(Boolean, default=True)  # Soft delete support
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    transcription = relationship("Transcription", back_populates="generated_images")
    
    def __repr__(self):
        return f"<GeneratedImage(id={self.id}, transcription_id={self.transcription_id}, style={self.style})>"
    
    @property
    def public_url(self):
        """Get public-accessible URL"""
        return self.image_url
