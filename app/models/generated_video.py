"""
Generated Video Model - Video generation results from transcripts
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class GeneratedVideo(Base):
    """Model for storing generated videos from transcripts"""
    __tablename__ = "generated_videos"

    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Video details
    filename = Column(String(500), nullable=False)
    url = Column(String(1000))  # MinIO URL
    duration = Column(Float)  # Total duration in seconds
    style = Column(String(100))  # Image style used (professional, artistic, etc.)
    
    # Status tracking
    status = Column(String(50), default="processing")  # processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    
    # Segments info (JSON array of segment details)
    segments = Column(JSON, nullable=True)  # [{text, image_url, audio_url, duration}, ...]
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Celery task info
    task_id = Column(String(255), nullable=True)
    
    # Relationships
    transcription = relationship("Transcription", backref="generated_videos")
    user = relationship("User", backref="generated_videos")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "transcription_id": self.transcription_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "url": self.url,
            "duration": self.duration,
            "style": self.style,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "segments": self.segments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "task_id": self.task_id
        }
