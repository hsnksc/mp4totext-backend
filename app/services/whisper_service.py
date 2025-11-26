"""
Whisper transcription service with Faster-Whisper backend
- Uses faster-whisper (CTranslate2) for 5-10x speedup
- Fallback to original OpenAI Whisper if needed
- Language-specific routing: Turkish → wav2vec2, Others → Whisper
"""

import whisper
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import torch

logger = logging.getLogger(__name__)


class WhisperService:
    """
    Whisper transcription service with Faster-Whisper backend
    - Primary: faster-whisper (CTranslate2) - 5-10x faster
    - Fallback: OpenAI Whisper (original)
    - Language routing: Turkish → wav2vec2, Others → faster-whisper
    """
    
    def __init__(self, model_size: str = "large-v3", use_faster_whisper: bool = True):
        """
        Initialize Whisper service
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3)
            use_faster_whisper: Use faster-whisper (CTranslate2) backend
        """
        self.model_size = model_size
        self.use_faster_whisper = use_faster_whisper
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"🎤 Whisper service initialized")
        logger.info(f"   Backend: {'Faster-Whisper (CTranslate2)' if use_faster_whisper else 'OpenAI Whisper'}")
        logger.info(f"   Device: {self.device}")
    
    def load_model(self):
        """Load Whisper model (Faster-Whisper or OpenAI)"""
        if self.model is None:
            if self.use_faster_whisper:
                # Use Faster-Whisper (CTranslate2)
                try:
                    from app.services.faster_whisper_service import get_faster_whisper_service
                    logger.info(f"📥 Loading Faster-Whisper model: {self.model_size}")
                    self.model = get_faster_whisper_service(model_size=self.model_size)
                    logger.info(f"✅ Faster-Whisper model loaded: {self.model_size}")
                except Exception as e:
                    logger.warning(f"⚠️ Faster-Whisper failed, falling back to OpenAI Whisper: {e}")
                    self.use_faster_whisper = False
            
            if not self.use_faster_whisper:
                # Fallback to OpenAI Whisper
                logger.info(f"📥 Loading OpenAI Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size, device=self.device)
                logger.info(f"✅ OpenAI Whisper model loaded: {self.model_size}")
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Faster-Whisper Large-v3 (all languages)
        
        Args:
            audio_path: Path to audio file
            language: Language code (auto-detect if None)
            task: "transcribe" or "translate" (to English)
            
        Returns:
            Dictionary with transcription results
        """
        # Load model if not loaded
        self.load_model()
        
        # Verify file exists
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"🎙️  Transcribing: {audio_file.name}")
        logger.info(f"   Language: {language or 'auto-detect'}")
        logger.info(f"   Task: {task}")
        logger.info(f"   Backend: {'Faster-Whisper Large-v3' if self.use_faster_whisper else 'OpenAI Whisper'}")
        
        try:
            # Transcribe with selected backend
            if self.use_faster_whisper:
                # Faster-Whisper (CTranslate2) - ALL LANGUAGES including Turkish
                result = self.model.transcribe(
                    audio_path=str(audio_path),
                    language=language,
                    task=task,
                    beam_size=5,
                    vad_filter=True  # Voice Activity Detection for better quality
                )
                
                # Format result for compatibility
                text = result.get("text", "")
                result_language = result.get("language", language or "unknown")
                segments = result.get("segments", [])
                
                logger.info(f"✅ Faster-Whisper transcription completed")
                logger.info(f"   Language: {result_language}")
                logger.info(f"   Text length: {len(text)} characters")
                logger.info(f"   Segments: {len(segments)}")
                
                return {
                    "text": text.strip(),
                    "language": result_language,
                    "segments": segments,
                    "task": task,
                    "backend": "faster-whisper"
                }
            else:
                # OpenAI Whisper (original) - fallback only
                result = self.model.transcribe(
                    str(audio_path),
                    language=language,
                    task=task,
                    fp16=False,  # Windows CPU compatibility
                    verbose=False,
                    # 🔥 Anti-hallucination parametreleri
                    condition_on_previous_text=False,  # Tekrarları önler
                    compression_ratio_threshold=2.4,   # Yüksek sıkıştırma = hallucination
                    logprob_threshold=-1.0,            # Düşük güven segmentleri atar
                    no_speech_threshold=0.6,           # Sessizlik tespiti
                    temperature=0.0                    # Greedy decoding (en güvenilir)
                )
                
                # Extract info
                text = result.get("text", "")
                result_language = result.get("language", language or "unknown")
                segments = result.get("segments", [])
                
                logger.info(f"✅ OpenAI Whisper transcription completed")
                logger.info(f"   Language: {result_language}")
                logger.info(f"   Text length: {len(text)} characters")
                logger.info(f"   Segments: {len(segments)}")
                
                return {
                    "text": text.strip(),
                    "language": result_language,
                    "segments": segments,
                    "task": task,
                    "backend": "openai-whisper"
                }
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            raise
    
    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe with detailed timestamps
        
        Args:
            audio_path: Path to audio file
            language: Language code
            
        Returns:
            Dictionary with segments including timestamps
        """
        result = self.transcribe(audio_path, language)
        
        # Format segments with timestamps
        formatted_segments = []
        for segment in result.get("segments", []):
            formatted_segments.append({
                "id": segment.get("id"),
                "start": segment.get("start"),
                "end": segment.get("end"),
                "text": segment.get("text", "").strip(),
                "confidence": segment.get("no_speech_prob", 0.0)
            })
        
        return {
            "text": result.get("text"),
            "language": result.get("language"),
            "segments": formatted_segments
        }


# Singleton instance
_whisper_service: Optional[WhisperService] = None


def get_whisper_service(model_size: str = "large-v3", use_faster_whisper: bool = True) -> WhisperService:
    """
    Get Whisper service singleton
    
    Args:
        model_size: Model size to use (default: large-v3 for best quality)
        use_faster_whisper: Use Faster-Whisper (CTranslate2) for 5-10x speedup
        
    Returns:
        WhisperService instance
    """
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService(
            model_size=model_size,
            use_faster_whisper=use_faster_whisper
        )
    return _whisper_service
