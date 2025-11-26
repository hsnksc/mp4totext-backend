"""
Transcription model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TranscriptionStatus(enum.Enum):
    """Transcription status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SpeakerModelType(enum.Enum):
    """Speaker recognition model type"""
    SILERO = "silero"  # Silero VAD (requires TorchCodec/FFmpeg)
    RESEMBLYZER = "resemblyzer"  # Resemblyzer (lightweight, no FFmpeg dependency)
    PYANNOTE = "pyannote"  # pyannote.audio 3.1 (state-of-the-art, Modal only)
    CUSTOM = "custom"  # Custom trained model (best_model.pth)
    NONE = "none"  # No speaker recognition


class GeminiMode(enum.Enum):
    """Gemini AI processing mode"""
    TEXT = "text"  # Standard text enhancement (default)
    NOTE = "note"  # Convert to structured lecture notes
    CUSTOM = "custom"  # Use custom user-provided prompt


class Transcription(Base):
    """Transcription job model"""
    
    __tablename__ = "transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)  # Foreign key to users
    
    # File info
    file_id = Column(String, unique=True, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)  # MinIO path
    content_type = Column(String, nullable=False)
    
    # Transcription settings
    language = Column(String, nullable=True)  # None = auto-detect
    whisper_model = Column(String, default="base")  # tiny, base, small, medium, large, turbo
    use_speaker_recognition = Column(Boolean, default=True)
    speaker_model_type = Column(SQLEnum(SpeakerModelType), default=SpeakerModelType.RESEMBLYZER)
    use_gemini_enhancement = Column(Boolean, default=False)
    ai_provider = Column(String, default="gemini")  # AI provider: "gemini" or "openai"
    ai_model = Column(String, nullable=True)  # AI model: "gemini-2.5-flash", "gpt-4o-mini", etc.
    enable_web_search = Column(Boolean, default=False)  # Enable Tavily web search (optional)
    
    # Status & Progress
    status = Column(SQLEnum(TranscriptionStatus), default=TranscriptionStatus.PENDING)
    progress = Column(Integer, default=0)
    
    # Results
    text = Column(Text, nullable=True)  # Full transcription text (RAW from Whisper)
    cleaned_text = Column(Text, nullable=True)  # Cleaned text (Together AI - filler removal, grammar fixes)
    result = Column(Text, nullable=True)  # Deprecated: JSON string (use text + segments)
    duration = Column(Float, nullable=True)  # Audio duration in seconds
    processing_time = Column(Float, nullable=True)  # Processing duration in seconds
    
    # Speaker Recognition Results
    speaker_count = Column(Integer, default=0)  # Number of unique speakers
    speakers = Column(JSON, nullable=True)  # List of speaker names: ["Speaker_1", "Speaker_2"]
    segments = Column(JSON, nullable=True)  # List of segments with speaker info
    
    # Transcription Provider
    transcription_provider = Column(String, default="openai_whisper")  # "openai_whisper" or "assemblyai"
    
    # Speaker Diarization
    enable_diarization = Column(Boolean, default=False)  # Enable speaker diarization (AssemblyAI)
    min_speakers = Column(Integer, nullable=True)  # Minimum number of speakers (optional constraint)
    max_speakers = Column(Integer, nullable=True)  # Maximum number of speakers (optional constraint)
    speakers_json = Column(JSON, nullable=True)  # Diarization data: [{"speaker": "A", "start": 0.0, "end": 2.5}]
    transcript_with_speakers = Column(Text, nullable=True)  # Formatted transcript with speaker labels
    
    # Gemini AI Enhancement
    enhanced_text = Column(Text, nullable=True)  # AI-enhanced transcription text (standard improvement)
    summary = Column(Text, nullable=True)  # AI-generated summary
    web_context_enrichment = Column(Text, nullable=True)  # AI-synthesized web search context with references
    gemini_status = Column(String, nullable=True)  # Status: pending, processing, completed, failed
    gemini_improvements = Column(JSON, nullable=True)  # List of improvements made
    gemini_metadata = Column(JSON, nullable=True)  # Additional AI metadata
    gemini_mode = Column(SQLEnum(GeminiMode), default=GeminiMode.TEXT)  # Processing mode
    custom_prompt = Column(Text, nullable=True)  # User-provided custom prompt (DEPRECATED - use custom_prompt_history)
    custom_prompt_result = Column(Text, nullable=True)  # Result of custom prompt processing (DEPRECATED - use custom_prompt_history)
    custom_prompt_history = Column(JSON, nullable=True)  # Array of custom prompt results: [{prompt, result, model, provider, timestamp}]
    lecture_notes = Column(Text, nullable=True)  # Structured lecture notes output (post-processing)
    exam_questions = Column(Text, nullable=True)  # AI-generated exam questions with answers (JSON string)
    translated_text = Column(Text, nullable=True)  # Translations to different languages (JSON string: {"lang": "text"})
    custom_model_path = Column(String, nullable=True)  # Path to custom speaker model file
    original_filename = Column(String, nullable=True)  # Original uploaded filename
    
    # AssemblyAI Speech Understanding Results (NEW!)
    sentiment_analysis = Column(JSON, nullable=True)  # Sentiment analysis results: [{"text": "...", "sentiment": "POSITIVE", "confidence": 0.9}]
    auto_chapters = Column(JSON, nullable=True)  # Auto chapters: [{"headline": "...", "summary": "...", "start": 0.0, "end": 10.0}]
    entities = Column(JSON, nullable=True)  # Entity detection: [{"entity_type": "person_name", "text": "John", "start": 0.0}]
    topics = Column(JSON, nullable=True)  # Topic detection (IAB): [{"text": "...", "labels": [{"label": "Business", "relevance": 0.8}]}]
    content_safety = Column(JSON, nullable=True)  # Content moderation: [{"text": "...", "labels": [{"label": "violence", "confidence": 0.9}]}]
    highlights = Column(JSON, nullable=True)  # Auto highlights: [{"text": "keyword", "count": 5, "rank": 0.9}]
    
    # LeMUR AI Results (NEW!)
    lemur_summary = Column(Text, nullable=True)  # LeMUR-generated summary
    lemur_questions_answers = Column(JSON, nullable=True)  # Q&A results: [{"question": "...", "answer": "..."}]
    lemur_action_items = Column(JSON, nullable=True)  # Action items: {"items": ["Task 1", "Task 2"]}
    lemur_custom_tasks = Column(JSON, nullable=True)  # Custom LeMUR tasks: [{"prompt": "...", "response": "..."}]
    
    # Feature Configuration
    assemblyai_features_enabled = Column(JSON, nullable=True)  # Track which AssemblyAI features were used
    
    # YouTube specific fields
    youtube_url = Column(String, nullable=True)  # YouTube video URL
    youtube_title = Column(String, nullable=True)  # YouTube video title
    youtube_duration = Column(Integer, nullable=True)  # YouTube video duration in seconds
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)  # Deprecated: use error_message
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    generated_images = relationship(
        "GeneratedImage", 
        back_populates="transcription",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Transcription(id={self.id}, filename={self.filename}, status={self.status})>"

    @property
    def speech_understanding(self):
        data = {
            "sentiment_analysis": self.sentiment_analysis,
            "auto_chapters": self.auto_chapters,
            "entities": self.entities,
            "topics": self.topics,
            "content_safety": self.content_safety,
            "highlights": self.highlights,
        }
        return data if any(value for value in data.values()) else None

    @property
    def llm_gateway(self):
        payload = {}
        if self.lemur_summary:
            payload["summary"] = {"text": self.lemur_summary}
        if self.lemur_questions_answers:
            payload["questions_and_answers"] = self.lemur_questions_answers
        if self.lemur_action_items:
            payload["action_items"] = self.lemur_action_items
        if self.lemur_custom_tasks:
            payload["custom_tasks"] = self.lemur_custom_tasks
        return payload or None
