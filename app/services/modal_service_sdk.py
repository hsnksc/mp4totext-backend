"""
Modal.com Whisper Transcription Service - SDK Version
Uses Modal SDK to call deployed functions directly
"""

import logging
import time
from typing import Dict, Any, Optional
import modal
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ModalService:
    """Modal.com Whisper service client using SDK"""
    
    def __init__(self):
        self.app_name = settings.MODAL_APP_NAME
        self.function_name = settings.MODAL_FUNCTION_NAME
        self.timeout = settings.MODAL_TIMEOUT
        
        logger.info(f"✅ Modal service initialized: {self.app_name}/{self.function_name}")
    
    def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None,
        model: str = "base",
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Modal Whisper function via SDK
        """
        logger.info(f"🚀 Modal transcription started with URL: {audio_url}")
        logger.info(f"📤 App: {self.app_name}, Function: {self.function_name}")
        logger.info(f"📤 Model: {model}, Language: {language}, Task: {task}")
        
        start_time = time.time()
        
        try:
            # Get reference to deployed Modal app
            app = modal.Lookup(self.app_name, create_if_missing=False)
            
            # Get function reference
            transcribe_fn = app[self.function_name]
            
            # Call remote function
            logger.info("📡 Calling remote Modal function...")
            result = transcribe_fn.remote(
                audio_url=audio_url,
                model=model,
                language=language,
                task=task,
                return_timestamps=True,
                word_timestamps=True
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Modal transcription completed in {elapsed:.1f}s")
            
            # Result is already in correct format from Modal function
            return result
            
        except Exception as e:
            logger.error(f"❌ Modal transcription error: {e}")
            raise ValueError(f"Modal transcription failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check if Modal app and function exist"""
        try:
            app = modal.Lookup(self.app_name, create_if_missing=False)
            _ = app[self.function_name]
            return {"status": "healthy", "app": self.app_name, "function": self.function_name}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
