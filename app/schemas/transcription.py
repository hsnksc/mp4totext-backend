"""
File upload schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict, Union
from datetime import datetime
from enum import Enum
import json


class TranscriptionStatus(str, Enum):
    """Transcription status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileUploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str
    filename: str
    file_size: int
    content_type: str
    upload_url: Optional[str] = None
    message: str = "File uploaded successfully"


class WhisperModel(str, Enum):
    """Whisper model size enum"""
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    TURBO = "turbo"


class GeminiMode(str, Enum):
    """Gemini AI processing mode"""
    TEXT = "text"  # Standard text enhancement
    NOTE = "note"  # Convert to structured lecture notes
    CUSTOM = "custom"  # Use custom user-provided prompt


class CostEstimationRequest(BaseModel):
    """Schema for cost estimation request"""
    duration_seconds: float = Field(..., description="Audio duration in seconds")
    use_speaker_recognition: bool = Field(True, description="Enable speaker recognition")
    use_gemini_enhancement: bool = Field(False, description="Enhance with AI")
    ai_provider: Optional[str] = Field("gemini", description="AI provider (gemini, openai, groq, together)")
    ai_model: Optional[str] = Field(None, description="AI model key")
    gemini_mode: GeminiMode = Field(GeminiMode.TEXT, description="AI processing mode")
    enable_web_search: bool = Field(False, description="Enable web search enrichment")
    is_youtube: bool = Field(False, description="Is YouTube video transcription")


class CostEstimationResponse(BaseModel):
    """Schema for cost estimation response"""
    total_cost: float = Field(..., description="Total estimated credit cost")
    breakdown: Dict[str, float] = Field(..., description="Cost breakdown by feature")
    user_credits: float = Field(..., description="Current user credit balance")
    sufficient_credits: bool = Field(..., description="Whether user has enough credits")


class TranscriptionProvider(str, Enum):
    """Transcription service provider"""
    OPENAI_WHISPER = "openai_whisper"  # Modal OpenAI Whisper (no diarization)
    ASSEMBLYAI = "assemblyai"  # AssemblyAI (with diarization)


class TranscriptionCreate(BaseModel):
    """Schema for creating transcription job"""
    file_id: str
    language: Optional[str] = Field(None, description="Language code (auto-detect if None)")
    whisper_model: WhisperModel = Field(WhisperModel.BASE, description="Whisper model size")
    transcription_provider: TranscriptionProvider = Field(
        TranscriptionProvider.OPENAI_WHISPER,
        description="Transcription provider (openai_whisper or assemblyai)"
    )
    enable_diarization: bool = Field(False, description="Enable speaker diarization (only for AssemblyAI)")
    use_speaker_recognition: bool = Field(True, description="Enable speaker recognition (DEPRECATED)")
    use_gemini_enhancement: bool = Field(False, description="Enhance with Gemini AI")
    gemini_mode: GeminiMode = Field(GeminiMode.TEXT, description="Gemini processing mode")
    custom_prompt: Optional[str] = Field(None, description="Custom prompt for Gemini (required if mode=CUSTOM)")


class SegmentResponse(BaseModel):
    """Schema for transcription segment"""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Segment text")
    speaker: Optional[str] = Field(None, description="Speaker name")
    speaker_confidence: Optional[float] = Field(None, description="Speaker confidence score")


class TranscriptionResponse(BaseModel):
    """Schema for transcription response"""
    id: int
    file_id: str
    filename: str
    status: TranscriptionStatus
    progress: int = Field(0, ge=0, le=100)
    
    # Main results
    text: Optional[str] = Field(None, description="Raw transcription text from Whisper")
    cleaned_text: Optional[str] = Field(None, description="Cleaned text (Together AI - filler removal, grammar fixes)")
    language: Optional[str] = Field(None, description="Detected language")
    whisper_model: Optional[str] = Field(None, description="Whisper model used")
    
    # Speaker recognition
    speaker_count: int = Field(0, description="Number of unique speakers")
    speakers: Optional[List[Union[str, Dict[str, Any]]]] = Field(None, description="List of speakers (string labels or dict with timestamps)")
    segments: Optional[List[dict]] = Field(None, description="Segments with speaker info")
    
    # Gemini AI Enhancement
    enhanced_text: Optional[str] = Field(None, description="AI-enhanced transcription text (standard improvement)")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    web_context_enrichment: Optional[str] = Field(None, description="AI-synthesized web search context with references")
    gemini_status: Optional[str] = Field(None, description="AI processing status")
    gemini_improvements: Optional[Any] = Field(None, description="AI improvements metadata (list or dict)")
    gemini_metadata: Optional[dict] = Field(None, description="AI processing metadata including provider info")
    gemini_mode: Optional[str] = Field(None, description="Processing mode used")
    ai_provider: Optional[str] = Field(None, description="AI provider used (gemini/openai)")
    ai_model: Optional[str] = Field(None, description="AI model used (e.g., gemini-2.5-flash, gpt-4o-mini)")
    custom_prompt: Optional[str] = Field(None, description="Last custom prompt (DEPRECATED - use custom_prompt_history)")
    custom_prompt_result: Optional[str] = Field(None, description="Last custom prompt result (DEPRECATED - use custom_prompt_history)")
    custom_prompt_history: Optional[list] = Field(None, description="History of custom prompts (newest first): [{prompt, result, model, provider, timestamp}]")
    lecture_notes: Optional[str] = Field(None, description="Structured lecture notes (post-processing)")
    exam_questions: Optional[str] = Field(None, description="AI-generated exam questions with answers (JSON string)")
    translated_text: Optional[dict] = Field(None, description="Translations to different languages (JSON: {lang: text})")
    
    # YouTube specific fields
    youtube_url: Optional[str] = Field(None, description="YouTube video URL")
    youtube_title: Optional[str] = Field(None, description="YouTube video title")
    youtube_duration: Optional[int] = Field(None, description="YouTube video duration in seconds")
    
    # 🎯 NEW: AssemblyAI Speech Understanding Results
    speech_understanding: Optional[dict] = Field(None, description="Full AssemblyAI Speech Understanding payload")
    sentiment_analysis: Optional[List[dict]] = Field(None, description="Sentiment analysis per sentence (emotion detection)")
    auto_chapters: Optional[List[dict]] = Field(None, description="Auto-generated chapters with timestamps")
    entities: Optional[List[dict]] = Field(None, description="Named entities detected (people, places, organizations)")
    topics: Optional[List[dict]] = Field(None, description="IAB content taxonomy topics")
    content_safety: Optional[dict] = Field(None, description="Content moderation results")
    highlights: Optional[List[dict]] = Field(None, description="Auto-detected highlights and key phrases")
    
    # 🤖 NEW: LeMUR AI Results
    llm_gateway: Optional[dict] = Field(None, description="LLM Gateway aggregated results")
    lemur_summary: Optional[str] = Field(None, description="LeMUR AI-generated summary")
    lemur_questions_answers: Optional[List[dict]] = Field(None, description="LeMUR Q&A results")
    lemur_action_items: Optional[dict] = Field(None, description="LeMUR extracted action items")
    lemur_custom_tasks: Optional[List[dict]] = Field(None, description="LeMUR custom task results")
    assemblyai_features_enabled: Optional[dict] = Field(None, description="Enabled AssemblyAI features configuration")
    
    # Custom models
    speaker_model_type: Optional[str] = Field(None, description="Speaker model type (silero/custom/none)")
    custom_model_path: Optional[str] = Field(None, description="Path to custom speaker model")
    original_filename: Optional[str] = Field(None, description="Original uploaded filename")
    
    # 📄 Vision API / Document Analysis Fields
    has_audio: Optional[bool] = Field(None, description="Has audio file")
    has_document: Optional[bool] = Field(None, description="Has document file")
    processing_mode: Optional[str] = Field(None, description="Processing mode (audio_only, document_only, combined)")
    document_file_id: Optional[str] = Field(None, description="Document file ID in storage")
    document_filename: Optional[str] = Field(None, description="Original document filename")
    document_file_size: Optional[int] = Field(None, description="Document file size in bytes")
    document_mime_type: Optional[str] = Field(None, description="Document MIME type")
    document_page_count: Optional[int] = Field(None, description="Number of pages in document")
    document_text: Optional[str] = Field(None, description="Extracted text from document")
    document_analysis: Optional[str] = Field(None, description="AI analysis of document")
    document_summary: Optional[str] = Field(None, description="Document summary")
    document_key_points: Optional[List[str]] = Field(None, description="Key points from document")
    document_topics: Optional[List[str]] = Field(None, description="Topics extracted from document")
    vision_provider: Optional[str] = Field(None, description="Vision API provider (gemini, openai)")
    vision_model: Optional[str] = Field(None, description="Vision model used")
    vision_status: Optional[str] = Field(None, description="Vision processing status")
    vision_error: Optional[str] = Field(None, description="Vision processing error message")
    vision_processing_time: Optional[float] = Field(None, description="Vision processing time in seconds")
    combined_summary: Optional[str] = Field(None, description="Combined audio+document summary")
    combined_insights: Optional[str] = Field(None, description="Combined insights from both sources")
    combined_key_points: Optional[List[str]] = Field(None, description="Combined key points")
    enable_combined_analysis: Optional[bool] = Field(None, description="Enable combined analysis flag")
    
    # File info
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    # Processing info
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    
    # Legacy fields
    result: Optional[dict] = None
    error: Optional[str] = None
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @field_validator('translated_text', mode='before')
    @classmethod
    def parse_translated_text(cls, v):
        """Parse translated_text from JSON string to dict"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return None
        return v
    
    class Config:
        from_attributes = True


class TranscriptionListResponse(BaseModel):
    """Schema for transcription list"""
    items: List[TranscriptionResponse]
    total: int
    page: int
    page_size: int


class CostEstimationRequest(BaseModel):
    """Schema for cost estimation request"""
    duration_seconds: float = Field(..., description="Duration of the audio/video file in seconds")
    transcription_provider: TranscriptionProvider = Field(
        default=TranscriptionProvider.OPENAI_WHISPER,
        description="Transcription provider"
    )
    enable_diarization: bool = Field(default=False, description="Enable speaker diarization (AssemblyAI only)")
    use_speaker_recognition: bool = Field(default=False, description="DEPRECATED - use enable_diarization")
    is_youtube: bool = Field(default=False, description="Whether it's a YouTube video")
    use_gemini_enhancement: bool = Field(default=False, description="Whether to use AI enhancement")
    gemini_mode: str = Field(default="enhance", description="AI enhancement mode (enhance, note, custom)")
    ai_model: Optional[str] = Field(default=None, description="AI model key")
    ai_provider: str = Field(default="gemini", description="AI provider (gemini, openai, groq, together)")
    enable_web_search: bool = Field(default=False, description="Whether to enable web search")


class CostEstimationResponse(BaseModel):
    """Schema for cost estimation response"""
    total_cost: float = Field(..., description="Total estimated cost in credits")
    breakdown: Dict[str, float] = Field(..., description="Cost breakdown by feature")
    user_credits: float = Field(..., description="User's current credit balance")
    sufficient_credits: bool = Field(..., description="Whether user has sufficient credits")
