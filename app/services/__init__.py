"""
Services module - Business logic and external integrations
"""

from app.services.storage import FileStorageService, get_storage_service

# Try to import audio processor (optional dependency)
try:
    from app.services.audio_processor import AudioProcessor, get_audio_processor
    AUDIO_PROCESSOR_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSOR_AVAILABLE = False
    AudioProcessor = None
    get_audio_processor = None

# Try to import whisper service (optional - requires torch + whisper)
try:
    from app.services.whisper_service import WhisperService
    WHISPER_SERVICE_AVAILABLE = True
except ImportError:
    WHISPER_SERVICE_AVAILABLE = False
    WhisperService = None

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
    "WHISPER_SERVICE_AVAILABLE",
    "SpeakerRecognitionService",
    "get_speaker_service",
    "AudioProcessor",
    "get_audio_processor",
    "SPEAKER_SERVICE_AVAILABLE",
    "AUDIO_PROCESSOR_AVAILABLE",
]
