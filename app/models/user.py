"""
User model for authentication
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    credits = Column(Float, default=100.0)  # Float for fractional credits (0.5, 1.5, etc.)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    sources = relationship("Source", back_populates="user", lazy="dynamic")
    
    # PKB Relationships
    pkb_chat_sessions = relationship("PKBChatSession", back_populates="user", lazy="dynamic")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})"
