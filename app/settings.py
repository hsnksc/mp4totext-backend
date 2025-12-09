"""
MP4toText Backend Configuration
Pydantic settings for environment variables and app configuration
"""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # =============================================================================
    # APP CONFIGURATION
    # =============================================================================
    APP_NAME: str = "MP4toText API"
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=True, env="DEBUG")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:19006"],
        env="CORS_ORIGINS"
    )
    
    # =============================================================================
    # DATABASE
    # =============================================================================
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    
    # =============================================================================
    # REDIS
    # =============================================================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # =============================================================================
    # GOOGLE OAUTH
    # =============================================================================
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(default="https://api.gistify.pro/api/auth/google/callback", env="GOOGLE_REDIRECT_URI")
    
    # =============================================================================
    # AMAZON OAUTH (Login with Amazon)
    # =============================================================================
    AMAZON_CLIENT_ID: Optional[str] = Field(default=None, env="AMAZON_CLIENT_ID")
    AMAZON_CLIENT_SECRET: Optional[str] = Field(default=None, env="AMAZON_CLIENT_SECRET")
    AMAZON_REDIRECT_URI: str = Field(default="https://api.gistify.pro/api/auth/amazon/callback", env="AMAZON_REDIRECT_URI")
    
    # =============================================================================
    # STORAGE (Cloudflare R2 / S3-compatible)
    # =============================================================================
    STORAGE_ACCOUNT_ID: str = Field(default="", env="STORAGE_ACCOUNT_ID")  # Cloudflare Account ID
    STORAGE_ENDPOINT: str = Field(default="", env="STORAGE_ENDPOINT")  # Full endpoint URL (optional)
    STORAGE_ACCESS_KEY: str = Field(default="", env="STORAGE_ACCESS_KEY")  # R2 Access Key ID
    STORAGE_SECRET_KEY: str = Field(default="", env="STORAGE_SECRET_KEY")  # R2 Secret Access Key
    STORAGE_BUCKET: str = Field(default="mp4totext", env="STORAGE_BUCKET")  # Bucket name
    STORAGE_PUBLIC_URL: str = Field(default="", env="STORAGE_PUBLIC_URL")  # Public URL base (e.g., https://pub-xxx.r2.dev)
    STORAGE_REGION: str = Field(default="auto", env="STORAGE_REGION")
    STORAGE_SECURE: bool = Field(default=True, env="STORAGE_SECURE")
    
    # =============================================================================
    # AI SERVICES
    # =============================================================================
    
    # Whisper (Legacy fallback)
    WHISPER_MODEL_SIZE: str = Field(default="large-v3", env="WHISPER_MODEL_SIZE")
    WHISPER_DEVICE: str = Field(default="cpu", env="WHISPER_DEVICE")
    
    # Faster-Whisper Large-v3 (CTranslate2) - ALL LANGUAGES including Turkish
    # 5-10x faster than OpenAI Whisper, best accuracy
    USE_FASTER_WHISPER: bool = Field(default=True, env="USE_FASTER_WHISPER")
    FASTER_WHISPER_MODEL: str = Field(default="large-v3", env="FASTER_WHISPER_MODEL")
    FASTER_WHISPER_DEVICE: str = Field(default="auto", env="FASTER_WHISPER_DEVICE")
    FASTER_WHISPER_COMPUTE_TYPE: str = Field(default="auto", env="FASTER_WHISPER_COMPUTE_TYPE")
    
    # RunPod Serverless (Cloud Whisper Transcription)
    USE_RUNPOD: bool = Field(default=False, env="USE_RUNPOD")
    RUNPOD_API_KEY: Optional[str] = Field(default=None, env="RUNPOD_API_KEY")
    RUNPOD_ENDPOINT_ID: Optional[str] = Field(default=None, env="RUNPOD_ENDPOINT_ID")
    RUNPOD_TIMEOUT: int = Field(default=300, env="RUNPOD_TIMEOUT")  # 5 minutes
    
    # Replicate (Cloud Whisper with native URL support - better for large files)
    USE_REPLICATE: bool = Field(default=False, env="USE_REPLICATE")
    REPLICATE_API_TOKEN: Optional[str] = Field(default=None, env="REPLICATE_API_TOKEN")
    
    # Modal.com (Serverless GPU - best for large files, pay-per-second)
    USE_MODAL: bool = Field(default=False, env="USE_MODAL")
    MODAL_API_TOKEN: Optional[str] = Field(default=None, env="MODAL_API_TOKEN")
    MODAL_APP_NAME: str = Field(default="mp4totext-whisper", env="MODAL_APP_NAME")
    MODAL_FUNCTION_NAME: str = Field(default="transcribe", env="MODAL_FUNCTION_NAME")
    MODAL_TIMEOUT: int = Field(default=600, env="MODAL_TIMEOUT")  # 10 minutes
    
    # AssemblyAI (Cloud transcription with built-in speaker diarization)
    USE_ASSEMBLYAI: bool = Field(default=False, env="USE_ASSEMBLYAI")
    ASSEMBLYAI_API_KEY: Optional[str] = Field(default=None, env="ASSEMBLYAI_API_KEY")
    ASSEMBLYAI_TIMEOUT: int = Field(default=600, env="ASSEMBLYAI_TIMEOUT")  # 10 minutes
    
    # AI Enhancement (OpenAI or Gemini or Groq)
    USE_OPENAI: bool = Field(default=False, env="USE_OPENAI")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    
    # Gemini (2.0-flash-lite: latest, fastest, most efficient model)
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(
        default="gemini-2.0-flash-lite",
        env="GEMINI_MODEL"
    )
    
    # Groq (Ultra-fast LLM inference - 10x faster than OpenAI)
    USE_GROQ: bool = Field(default=False, env="USE_GROQ")
    GROQ_API_KEY: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", env="GROQ_MODEL")
    
    # Together AI (Transcript Cleaning - MANDATORY for all transcripts)
    TOGETHER_API_KEY: Optional[str] = Field(default=None, env="TOGETHER_API_KEY")
    TOGETHER_MODEL: str = Field(
        default="meta-llama/Llama-2-13b-chat-hf",
        env="TOGETHER_MODEL"
    )
    TOGETHER_TEMPERATURE: float = Field(default=0.2, env="TOGETHER_TEMPERATURE")
    TOGETHER_MAX_TOKENS: int = Field(default=4000, env="TOGETHER_MAX_TOKENS")
    
    # Tavily Web Search API (for AI context enrichment)
    TAVILY_API_KEY: Optional[str] = Field(default=None, env="TAVILY_API_KEY")
    ENABLE_WEB_SEARCH: bool = Field(default=True, env="ENABLE_WEB_SEARCH")
    WEB_SEARCH_MAX_RESULTS: int = Field(default=3, env="WEB_SEARCH_MAX_RESULTS")
    
    # HuggingFace
    HF_TOKEN: Optional[str] = Field(default=None, env="HF_TOKEN")
    
    # Global Speaker Model
    GLOBAL_MODEL_PATH: str = Field(
        default="models/best_model.pth",
        env="GLOBAL_MODEL_PATH"
    )
    GLOBAL_MAPPING_PATH: str = Field(
        default="models/speaker_mapping.json",
        env="GLOBAL_MAPPING_PATH"
    )
    GLOBAL_MODEL_THRESHOLD: float = Field(default=0.70, env="GLOBAL_MODEL_THRESHOLD")
    
    # =============================================================================
    # JWT AUTHENTICATION
    # =============================================================================
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION: int = Field(default=3600, env="JWT_EXPIRATION")  # 1 hour
    JWT_REFRESH_EXPIRATION: int = Field(
        default=604800,
        env="JWT_REFRESH_EXPIRATION"
    )  # 7 days
    
    # =============================================================================
    # CELERY
    # =============================================================================
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = Field(default=3600, env="CELERY_TASK_TIME_LIMIT")
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=3300,
        env="CELERY_TASK_SOFT_TIME_LIMIT"
    )
    
    # =============================================================================
    # FILE UPLOAD
    # =============================================================================
    MAX_UPLOAD_SIZE: int = Field(
        default=104857600,  # 100 MB
        env="MAX_UPLOAD_SIZE"
    )
    ALLOWED_AUDIO_FORMATS: List[str] = Field(
        default=["mp3", "wav", "m4a", "flac", "ogg", "aac", "wma"],
        env="ALLOWED_AUDIO_FORMATS"
    )
    ALLOWED_VIDEO_FORMATS: List[str] = Field(
        default=["mp4", "avi", "mkv", "mov", "wmv", "flv"],
        env="ALLOWED_VIDEO_FORMATS"
    )
    
    # =============================================================================
    # RATE LIMITING
    # =============================================================================
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # =============================================================================
    # LOGGING
    # =============================================================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE: str = Field(default="logs/app.log", env="LOG_FILE")
    
    # =============================================================================
    # QDRANT VECTOR DATABASE (RAG+PKB)
    # =============================================================================
    QDRANT_URL: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    QDRANT_API_KEY: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    QDRANT_COLLECTION_PREFIX: str = Field(default="gistify", env="QDRANT_COLLECTION_PREFIX")
    
    # RAG Settings
    RAG_DEFAULT_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="RAG_DEFAULT_EMBEDDING_MODEL")
    RAG_DEFAULT_LLM_MODEL: str = Field(default="gpt-4o-mini", env="RAG_DEFAULT_LLM_MODEL")
    RAG_DEFAULT_CHUNK_SIZE: int = Field(default=512, env="RAG_DEFAULT_CHUNK_SIZE")
    RAG_DEFAULT_CHUNK_OVERLAP: int = Field(default=50, env="RAG_DEFAULT_CHUNK_OVERLAP")
    RAG_DEFAULT_TOP_K: int = Field(default=5, env="RAG_DEFAULT_TOP_K")
    
    # =============================================================================
    # MONITORING
    # =============================================================================
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    SENTRY_ENVIRONMENT: str = Field(default="development", env="SENTRY_ENVIRONMENT")
    
    # =============================================================================
    # EMAIL (Optional)
    # =============================================================================
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_FROM: str = Field(default="noreply@mp4totext.com", env="SMTP_FROM")
    
    # =============================================================================
    # GEMINI AI
    # =============================================================================
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")
    
    # =============================================================================
    # SPEAKER RECOGNITION
    # =============================================================================
    CUSTOM_SPEAKER_MODEL_PATH: str = Field(
        default="models/best_model.pth",
        env="CUSTOM_SPEAKER_MODEL_PATH"
    )
    DEFAULT_SPEAKER_MODEL: str = Field(
        default="silero",  # Options: silero, custom, none
        env="DEFAULT_SPEAKER_MODEL"
    )
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_AUDIO_FORMATS", "ALLOWED_VIDEO_FORMATS", pre=True)
    def parse_formats(cls, v):
        """Parse file formats from string or list"""
        if isinstance(v, str):
            return [fmt.strip() for fmt in v.split(",")]
        return v
    
    @validator("WHISPER_MODEL_SIZE")
    def validate_whisper_model(cls, v):
        """Validate Whisper model size"""
        allowed_sizes = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
        if v not in allowed_sizes:
            raise ValueError(f"Invalid Whisper model size. Choose from: {allowed_sizes}")
        return v
    
    @validator("WHISPER_DEVICE")
    def validate_device(cls, v):
        """Validate device type"""
        allowed_devices = ["cpu", "cuda"]
        if v not in allowed_devices:
            raise ValueError(f"Invalid device. Choose from: {allowed_devices}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"Invalid log level. Choose from: {allowed_levels}")
        return v_upper
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENV.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENV.lower() == "development"
    
    @property
    def all_allowed_formats(self) -> List[str]:
        """Get all allowed file formats"""
        return self.ALLOWED_AUDIO_FORMATS + self.ALLOWED_VIDEO_FORMATS
    
    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Using lru_cache ensures settings are only loaded once
    """
    return Settings()
