"""
Pulse Social Platform Models
============================
Models for the Pulse social media platform integrated with MixUp/Gistify.
All users share the same Gistify authentication system.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    ForeignKey, JSON, Table, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class PulseVisibility(str, Enum):
    """Visibility settings for pulses"""
    PUBLIC = "public"           # Everyone can see
    FOLLOWERS = "followers"     # Only followers
    CIRCLE = "circle"           # Specific circle only
    PRIVATE = "private"         # Only author


class PulseStatus(str, Enum):
    """Status of a pulse"""
    DRAFT = "draft"             # Not published yet
    PUBLISHED = "published"     # Live and visible
    ARCHIVED = "archived"       # Hidden but not deleted
    DELETED = "deleted"         # Soft deleted


class ResonanceType(str, Enum):
    """Types of resonance reactions (instead of likes)"""
    INSPIRE = "inspire"         # 💡 Inspiring
    AGREE = "agree"             # 🤝 I agree
    THINK = "think"             # 🤔 Makes me think
    FEEL = "feel"               # ❤️ I feel this
    ACT = "act"                 # 🚀 Makes me want to act


class ContentType(str, Enum):
    """Types of pulse content"""
    TEXT = "text"               # Plain text pulse
    MIXUP = "mixup"             # Imported from MixUp
    IMAGE = "image"             # Image with optional text
    LINK = "link"               # Link preview
    POLL = "poll"               # Poll/voting
    THREAD = "thread"           # Multi-part thread


class AIGenerationType(str, Enum):
    """Types of AI generation operations"""
    FORMAT = "format"           # Format/style content
    EXPAND = "expand"           # Expand content
    SUMMARIZE = "summarize"     # Summarize content
    TRANSLATE = "translate"     # Translate content
    ENHANCE = "enhance"         # General enhancement


# ============================================================================
# ASSOCIATION TABLES
# ============================================================================

# Many-to-many: Pulse <-> Hashtag
pulse_hashtags = Table(
    'pulse_hashtags',
    Base.metadata,
    Column('pulse_id', Integer, ForeignKey('pulses.id', ondelete='CASCADE'), primary_key=True),
    Column('hashtag_id', Integer, ForeignKey('hashtags.id', ondelete='CASCADE'), primary_key=True)
)

# Many-to-many: Circle <-> User (members)
circle_members = Table(
    'circle_members',
    Base.metadata,
    Column('circle_id', Integer, ForeignKey('circles.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('joined_at', DateTime(timezone=True), server_default=func.now())
)


# ============================================================================
# MAIN MODELS
# ============================================================================

class Pulse(Base):
    """
    Main content unit in Pulse platform.
    Can be created manually, via AI, or imported from MixUp.
    """
    __tablename__ = "pulses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Author (Gistify user)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    formatted_content = Column(Text, nullable=True)  # AI-formatted version
    
    # Media
    media_urls = Column(JSON, default=list)  # List of media URLs
    link_preview = Column(JSON, nullable=True)  # {url, title, description, image}
    
    # Metadata
    content_type = Column(SQLEnum(ContentType), default=ContentType.TEXT)
    visibility = Column(SQLEnum(PulseVisibility), default=PulseVisibility.PUBLIC)
    status = Column(SQLEnum(PulseStatus), default=PulseStatus.PUBLISHED)
    
    # MixUp Integration
    mixup_source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    mixup_items = Column(JSON, nullable=True)  # Original MixUp items
    
    # Threading
    parent_id = Column(Integer, ForeignKey("pulses.id", ondelete="SET NULL"), nullable=True)
    thread_position = Column(Integer, default=0)  # Position in thread
    
    # Circle restriction (if visibility=CIRCLE)
    circle_id = Column(Integer, ForeignKey("circles.id", ondelete="SET NULL"), nullable=True)
    
    # AI Generation info
    ai_generated = Column(Boolean, default=False)
    ai_model = Column(String(100), nullable=True)
    ai_prompt = Column(Text, nullable=True)
    
    # Stats (denormalized for performance)
    resonance_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", backref="pulses")
    hashtags = relationship("Hashtag", secondary=pulse_hashtags, back_populates="pulses")
    resonances = relationship("Resonance", back_populates="pulse", cascade="all, delete-orphan")
    comments = relationship("PulseComment", back_populates="pulse", cascade="all, delete-orphan")
    parent = relationship("Pulse", remote_side=[id], backref="thread_replies")
    circle = relationship("Circle", back_populates="pulses")
    mixup_source = relationship("Source", backref="deployed_pulses")
    ai_generations = relationship("PulseAIGeneration", back_populates="pulse", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_pulses_user_created', 'user_id', 'created_at'),
        Index('ix_pulses_visibility_status', 'visibility', 'status'),
        Index('ix_pulses_parent', 'parent_id'),
    )
    
    def __repr__(self):
        return f"<Pulse(id={self.id}, user_id={self.user_id}, type={self.content_type})>"


class Follow(Base):
    """
    User following relationship.
    """
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    follower = relationship("User", foreign_keys=[follower_id], backref="following")
    following = relationship("User", foreign_keys=[following_id], backref="followers")
    
    __table_args__ = (
        Index('ix_follows_unique', 'follower_id', 'following_id', unique=True),
    )


class Circle(Base):
    """
    Private sharing groups for users.
    Content can be shared only with specific circles.
    """
    __tablename__ = "circles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Creator
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")  # Hex color for UI
    icon = Column(String(50), default="👥")  # Emoji icon
    
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="circles")
    members = relationship("User", secondary=circle_members, backref="member_circles")
    pulses = relationship("Pulse", back_populates="circle")
    
    def __repr__(self):
        return f"<Circle(id={self.id}, name={self.name}, user_id={self.user_id})>"


class Hashtag(Base):
    """
    Hashtags for content discovery.
    """
    __tablename__ = "hashtags"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(100), unique=True, index=True, nullable=False)  # Without #
    
    # Stats
    use_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pulses = relationship("Pulse", secondary=pulse_hashtags, back_populates="hashtags")
    
    def __repr__(self):
        return f"<Hashtag(id={self.id}, name=#{self.name})>"


class Resonance(Base):
    """
    Reactions to pulses (replaces traditional "likes").
    5 types: inspire, agree, think, feel, act
    """
    __tablename__ = "resonances"
    
    id = Column(Integer, primary_key=True, index=True)
    
    pulse_id = Column(Integer, ForeignKey("pulses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    resonance_type = Column(SQLEnum(ResonanceType), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pulse = relationship("Pulse", back_populates="resonances")
    user = relationship("User", backref="resonances")
    
    __table_args__ = (
        Index('ix_resonance_unique', 'pulse_id', 'user_id', 'resonance_type', unique=True),
    )


class PulseComment(Base):
    """
    Comments on pulses.
    """
    __tablename__ = "pulse_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    pulse_id = Column(Integer, ForeignKey("pulses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    content = Column(Text, nullable=False)
    
    # Reply to another comment
    parent_id = Column(Integer, ForeignKey("pulse_comments.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    pulse = relationship("Pulse", back_populates="comments")
    user = relationship("User", backref="pulse_comments")
    parent = relationship("PulseComment", remote_side=[id], backref="replies")
    
    __table_args__ = (
        Index('ix_comments_pulse_created', 'pulse_id', 'created_at'),
    )


class PulseNotification(Base):
    """
    Notifications for pulse-related activities.
    """
    __tablename__ = "pulse_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Who receives the notification
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Who triggered the notification
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    # Related entities
    pulse_id = Column(Integer, ForeignKey("pulses.id", ondelete="CASCADE"), nullable=True)
    comment_id = Column(Integer, ForeignKey("pulse_comments.id", ondelete="CASCADE"), nullable=True)
    
    # Notification type and content
    notification_type = Column(String(50), nullable=False)  # resonance, comment, follow, mention
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="pulse_notifications")
    actor = relationship("User", foreign_keys=[actor_id])
    pulse = relationship("Pulse", backref="notifications")
    comment = relationship("PulseComment", backref="notifications")
    
    __table_args__ = (
        Index('ix_notifications_user_unread', 'user_id', 'is_read'),
    )


class PulseAIGeneration(Base):
    """
    Track AI generation operations for pulses.
    """
    __tablename__ = "pulse_ai_generations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    pulse_id = Column(Integer, ForeignKey("pulses.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    generation_type = Column(SQLEnum(AIGenerationType), nullable=False)
    
    # AI details
    ai_provider = Column(String(50), nullable=False)  # gemini, openai, groq
    ai_model = Column(String(100), nullable=False)
    
    # Input/Output
    input_content = Column(Text, nullable=False)
    output_content = Column(Text, nullable=False)
    prompt_used = Column(Text, nullable=True)
    
    # Cost
    credits_used = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pulse = relationship("Pulse", back_populates="ai_generations")
    user = relationship("User", backref="pulse_ai_generations")


class VibeCheck(Base):
    """
    Community mood/vibe tracking.
    Users can set their current "vibe" which aggregates into community mood.
    """
    __tablename__ = "vibe_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    vibe = Column(String(50), nullable=False)  # emoji or predefined vibe
    message = Column(String(200), nullable=True)  # Optional short message
    
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-expires
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", backref="vibe_checks")
    
    __table_args__ = (
        Index('ix_vibe_user_created', 'user_id', 'created_at'),
    )


class PulseMessage(Base):
    """
    Direct messages between users (optional, for future).
    """
    __tablename__ = "pulse_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    content = Column(Text, nullable=False)
    
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")
    
    __table_args__ = (
        Index('ix_messages_conversation', 'sender_id', 'receiver_id', 'created_at'),
    )
