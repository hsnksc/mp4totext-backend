"""
Replicate API Integration for Whisper Transcription
Native URL support, better for large files
"""

import logging
import time
import replicate
from typing import Dict, Any, Optional, List

from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ReplicateService:
    """Replicate Whisper Transcription Service"""
    
    def __init__(self):
        self.api_token = settings.REPLICATE_API_TOKEN
        
        if not self.api_token:
            raise ValueError("Replicate API token is required. Get one at: https://replicate.com/account/api-tokens")
        
        # Set API token for replicate client
        import os
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        
        logger.info("✅ Replicate client initialized")
    
    def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None,
        model: str = "large-v3",
        task: str = "transcribe",
        temperature: float = 0.0,
        batch_size: int = 24
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using Replicate Whisper endpoint
        
        Args:
            audio_url: Public URL to audio file (required)
            language: Language code (e.g., 'tr', 'en', None for auto-detect)
            model: Whisper model size (large-v3, large-v2, medium, etc.)
            task: 'transcribe' or 'translate'
            temperature: Sampling temperature (0.0 = deterministic)
            batch_size: Batch size for processing (16-32 recommended)
            
        Returns:
            dict: {
                "text": "full transcript",
                "segments": [...],
                "language": "detected_language"
            }
        """
        try:
            logger.info(f"🚀 Replicate transcription started")
            logger.info(f"📤 URL: {audio_url}")
            logger.info(f"📤 Model: {model}, Language: {language}, Task: {task}")
            
            start_time = time.time()
            
            # Replicate Whisper model: incredibly-fast-whisper by vaibhavs10
            # https://replicate.com/vaibhavs10/incredibly-fast-whisper
            input_params = {
                "audio": audio_url,
                "task": task,
                "batch_size": batch_size,
                "timestamp": "chunk",  # Get word-level timestamps
                "diarise_audio": False  # We do our own diarization
            }
            
            # Add language if specified
            if language:
                input_params["language"] = language
            
            logger.info(f"📋 Input params: {list(input_params.keys())}")
            
            # Run prediction
            output = replicate.run(
                "vaibhavs10/incredibly-fast-whisper:3ab86df6c8f54c11309d4d1f930ac292bad43ace52d10c80d87eb258b3c9f79c",
                input=input_params
            )
            
            processing_time = time.time() - start_time
            logger.info(f"⏱️ Replicate processing time: {processing_time:.2f}s")
            
            # Parse output
            result = self._parse_transcription_result(output)
            
            logger.info(f"✅ Replicate transcription completed")
            logger.info(f"📊 Transcript length: {len(result.get('text', ''))} chars")
            logger.info(f"📊 Segments: {len(result.get('segments', []))}")
            logger.info(f"🌍 Detected language: {result.get('language', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Replicate transcription failed: {str(e)}")
            raise
    
    def _parse_transcription_result(self, output: Any) -> Dict[str, Any]:
        """
        Parse Replicate output into standardized format
        
        Output format from incredibly-fast-whisper:
        {
            "text": "full transcript",
            "chunks": [
                {
                    "text": "segment text",
                    "timestamp": [start, end]
                }
            ]
        }
        """
        try:
            logger.info(f"🔍 Replicate output type: {type(output)}")
            
            if isinstance(output, dict):
                full_text = output.get("text", "")
                chunks = output.get("chunks", [])
                
                # Convert chunks to segments format
                segments = []
                for i, chunk in enumerate(chunks):
                    timestamp = chunk.get("timestamp", [0.0, 0.0])
                    segments.append({
                        "id": i,
                        "start": timestamp[0] if len(timestamp) > 0 else 0.0,
                        "end": timestamp[1] if len(timestamp) > 1 else 0.0,
                        "text": chunk.get("text", "").strip()
                    })
                
                result = {
                    "text": full_text,
                    "segments": segments,
                    "language": "unknown"  # Replicate doesn't return language detection
                }
                
                logger.info(f"✅ Parsed {len(segments)} segments from Replicate output")
                return result
            
            else:
                logger.error(f"❌ Unexpected output format from Replicate: {type(output)}")
                raise ValueError(f"Unexpected output format: {type(output)}")
                
        except Exception as e:
            logger.error(f"❌ Failed to parse Replicate result: {e}")
            raise ValueError(f"Failed to parse transcription result: {e}")
    
    def check_health(self) -> bool:
        """Check if Replicate API is accessible"""
        try:
            # Simple test: list models
            replicate.models.list()
            return True
        except Exception as e:
            logger.error(f"❌ Replicate health check failed: {e}")
            return False


# Singleton instance
_replicate_service = None

def get_replicate_service() -> ReplicateService:
    """Get or create ReplicateService singleton"""
    global _replicate_service
    if _replicate_service is None:
        _replicate_service = ReplicateService()
    return _replicate_service
