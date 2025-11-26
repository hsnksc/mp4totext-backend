"""
Modal.com Whisper Transcription Service
Uses Modal's serverless GPU infrastructure for fast, scalable transcription
"""

import logging
import time
from typing import Dict, Any, Optional
import modal
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ModalService:
    """
    Modal.com Whisper service client
    
    Modal provides serverless GPU infrastructure with:
    - Native URL support (no base64 needed!)
    - Auto-scaling (0 to many GPUs instantly)
    - Pay-per-second billing
    - Up to 5GB file support
    """
    
    def __init__(self):
        self.api_token = settings.MODAL_API_TOKEN
        self.app_name = settings.MODAL_APP_NAME  # e.g., "mp4totext-whisper"
        self.function_name = settings.MODAL_FUNCTION_NAME  # e.g., "transcribe"
        self.timeout = settings.MODAL_TIMEOUT
        
        if not self.api_token:
            raise ValueError("MODAL_API_TOKEN not configured in .env")
        
        logger.info(f"✅ Modal service initialized: {self.app_name}/{self.function_name}")
    
    def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None,
        model: str = "large-v3",
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Modal Whisper function
        
        Args:
            audio_url: Public URL to audio file (MinIO presigned URL or any public URL)
            language: Language code (e.g., 'en', 'tr') or None for auto-detect
            model: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            task: 'transcribe' or 'translate'
        
        Returns:
            Dict with transcription results
        """
        logger.info(f"🚀 Modal transcription started with URL: {audio_url}")
        
        # Modal function endpoint
        endpoint_url = f"https://modal.com/api/v1/apps/{self.app_name}/functions/{self.function_name}/invoke"
        
        # Prepare request payload
        payload = {
            "audio_url": audio_url,
            "model": model,
            "language": language,
            "task": task,
            "return_timestamps": True,
            "word_timestamps": True
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"📤 Sending to Modal function: {self.app_name}/{self.function_name}")
        logger.info(f"📤 Model: {model}, Language: {language}, Task: {task}")
        
        start_time = time.time()
        
        try:
            # Submit job to Modal
            response = requests.post(
                endpoint_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Modal transcription completed in {elapsed:.1f}s")
            
            # Parse result
            return self._parse_transcription_result(result)
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ Modal request timeout after {self.timeout}s")
            raise TimeoutError(f"Modal transcription timeout after {self.timeout}s")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Modal request failed: {e}")
            raise ValueError(f"Modal transcription failed: {e}")
    
    def _parse_transcription_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Modal Whisper result into standard format
        
        Expected Modal output format:
        {
            "text": "Full transcription...",
            "segments": [
                {"start": 0.0, "end": 5.2, "text": "Hello world"},
                ...
            ],
            "language": "en",
            "duration": 120.5
        }
        """
        if not result:
            raise ValueError("Empty result from Modal")
        
        # Extract fields
        full_text = result.get("text", "")
        segments = result.get("segments", [])
        language = result.get("language", "unknown")
        
        if not full_text:
            raise ValueError("No transcription text in Modal result")
        
        logger.info(f"📝 Transcription length: {len(full_text)} chars")
        logger.info(f"🔢 Segments: {len(segments)}")
        logger.info(f"🌍 Language: {language}")
        
        return {
            "text": full_text,
            "segments": segments,
            "language": language,
            "text_length": len(full_text),
            "segment_count": len(segments)
        }


# Singleton instance
_modal_service_instance = None


def get_modal_service() -> ModalService:
    """Get or create Modal service singleton"""
    global _modal_service_instance
    if _modal_service_instance is None:
        _modal_service_instance = ModalService()
    return _modal_service_instance
