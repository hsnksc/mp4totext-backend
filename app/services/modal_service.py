"""
Modal.com Whisper Transcription Service - Client Version
Uses Modal Client to invoke deployed functions
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
        # OPENAI WHISPER: PyTorch native, cuDNN-free
        self.whisper_app = "mp4totext-openai-whisper"
        
        self.function_name = settings.MODAL_FUNCTION_NAME
        self.timeout = settings.MODAL_TIMEOUT
        self._whisper_cls = None  # Cache for Whisper model
        
        logger.info(f"✅ Modal service initialized")
        logger.info(f"   APP: {self.whisper_app} (OpenAI Whisper)")
        logger.info(f"   GPU: T4 ($0.36/hour)")
        logger.info(f"   Model: Whisper Large V3")
    
    def _get_whisper_class(self):
        """Get OpenAI Whisper transcriber class"""
        if self._whisper_cls is None:
            logger.info("🔍 Looking up OpenAIWhisperTranscriber from Modal...")
            self._whisper_cls = modal.Cls.from_name(self.whisper_app, "OpenAIWhisperTranscriber")
            logger.info("✅ OpenAIWhisperTranscriber class reference cached")
        return self._whisper_cls
    
    def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Modal OpenAI Whisper (transcription-only, no diarization)
        Uses PyTorch native CUDA (cuDNN-free)
        T4 GPU, cost-optimized for pure transcription
        """
        logger.info(f"🚀 Modal OpenAI Whisper transcription started")
        logger.info(f"📤 URL: {audio_url[:80]}...")
        logger.info(f"📤 Language: {language}")
        
        start_time = time.time()
        
        try:
            logger.info("⚡ Using OpenAI Whisper (cuDNN-free, PyTorch native)")
            
            TranscriberCls = self._get_whisper_class()
            instance = TranscriberCls()
            result = instance.transcribe.remote(
                audio_url=audio_url,
                language=language
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Transcription completed in {elapsed:.1f}s")
            logger.info(f"📊 Segments: {result.get('segments_count', 0)}")
            logger.info(f"🌍 Language: {result.get('language', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Modal transcription error: {e}")
            raise ValueError(f"Modal transcription failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Modal app availability"""
        try:
            whisper_status = "unknown"
            try:
                modal.Cls.from_name(self.whisper_app, "OpenAIWhisperTranscriber")
                whisper_status = "healthy"
            except:
                whisper_status = "not deployed"
            
            return {
                "status": "healthy" if whisper_status == "healthy" else "unhealthy",
                "whisper": {
                    "app": self.whisper_app,
                    "status": whisper_status,
                    "gpu": "T4",
                    "cost": "$0.36/hour",
                    "model": "OpenAI Whisper Large V3 (cuDNN-free)"
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton instance
_modal_service_instance = None


def get_modal_service() -> ModalService:
    """Get or create Modal service singleton"""
    global _modal_service_instance
    if _modal_service_instance is None:
        _modal_service_instance = ModalService()
    return _modal_service_instance
