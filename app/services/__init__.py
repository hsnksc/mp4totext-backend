"""
Services module - Business logic and external integrations
"""

from app.services.storage import FileStorageService, get_storage_service
from app.services.whisper_service import WhisperService
from app.services.audio_processor import AudioProcessor, get_audio_processor

# Try to import speaker service (optional dependency)
try:
    from app.services.speaker_service import SpeakerRecognitionService, get_speaker_service
    SPEAKER_SERVICE_AVAILABLE = True
except ImportError:
    SPEAKER_SERVICE_AVAILABLE = False
    SpeakerRecognitionService = None
    get_speaker_service = None

__all__ = [
    "FileStorageService",
    "get_storage_service",
    "WhisperService",
    "SpeakerRecognitionService",
    "get_speaker_service",
    "AudioProcessor",
    "get_audio_processor",
    "SPEAKER_SERVICE_AVAILABLE",
]

from app.services.storage import get_storage_service

__all__ = ["get_storage_service"]
