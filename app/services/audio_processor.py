"""
Complete audio processing service combining Whisper + Speaker Recognition
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import librosa
import soundfile as sf
import numpy as np

from app.services.whisper_service import WhisperService
from app.services.speaker_service import SpeakerRecognitionService

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Complete audio processing pipeline:
    1. Whisper transcription
    2. Speaker recognition (if available)
    3. Segment processing
    """
    
    def __init__(
        self,
        whisper_model_size: str = "large-v3",
        speaker_model_path: Optional[str] = None,
        speaker_mapping_path: Optional[str] = None,
        speaker_threshold: float = 0.7,
        use_faster_whisper: bool = True
    ):
        """
        Initialize audio processor
        
        Args:
            whisper_model_size: Whisper model size (tiny/base/small/medium/large/large-v3)
            speaker_model_path: Path to speaker model
            speaker_mapping_path: Path to speaker mapping
            speaker_threshold: Confidence threshold for speaker recognition
            use_faster_whisper: Use Faster-Whisper (CTranslate2) backend for 5-10x speedup
        """
        self.whisper_service = WhisperService(
            model_size=whisper_model_size,
            use_faster_whisper=use_faster_whisper
        )
        
        self.speaker_service = SpeakerRecognitionService(
            model_path=speaker_model_path,
            mapping_path=speaker_mapping_path,
            threshold=speaker_threshold
        )
        
        self.speaker_enabled = self.speaker_service.is_available()
        
        logger.info(f"🎵 AudioProcessor initialized (speaker_enabled={self.speaker_enabled})")
    
    def process_file(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process audio file: transcription + speaker recognition
        
        Args:
            audio_path: Path to audio file
            language: Language code (auto-detect if None)
            
        Returns:
            {
                "text": "full transcription",
                "language": "en",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 2.5,
                        "text": "Hello world",
                        "speaker": "Speaker_1",
                        "speaker_confidence": 0.92
                    },
                    ...
                ],
                "speakers": ["Speaker_1", "Speaker_2"],
                "speaker_count": 2
            }
        """
        logger.info(f"🎬 Processing audio file: {audio_path}")
        
        try:
            # Step 1: Transcribe with Whisper
            logger.info("📝 Step 1: Transcribing with Whisper...")
            whisper_result = self.whisper_service.transcribe(audio_path, language)
            
            result = {
                "text": whisper_result["text"],
                "language": whisper_result.get("language", language),
                "segments": [],
                "speakers": [],
                "speaker_count": 0
            }
            
            # Step 2: Speaker recognition (if enabled)
            if self.speaker_enabled and "segments" in whisper_result:
                logger.info("👤 Step 2: Identifying speakers...")
                result["segments"] = self._process_segments_with_speakers(
                    audio_path,
                    whisper_result["segments"]
                )
                
                # Extract unique speakers
                speakers = set()
                for segment in result["segments"]:
                    if segment.get("speaker"):
                        speakers.add(segment["speaker"])
                
                result["speakers"] = sorted(list(speakers))
                result["speaker_count"] = len(speakers)
            else:
                # No speaker recognition - just copy segments
                result["segments"] = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"]
                    }
                    for seg in whisper_result.get("segments", [])
                ]
            
            logger.info(f"✅ Processing complete: {len(result['text'])} chars, {result['speaker_count']} speakers")
            return result
            
        except Exception as e:
            logger.error(f"❌ Audio processing failed: {e}", exc_info=True)
            raise
    
    def _process_segments_with_speakers(
        self,
        audio_path: str,
        whisper_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Add speaker identification to Whisper segments
        
        Args:
            audio_path: Path to audio file
            whisper_segments: Segments from Whisper
            
        Returns:
            Enhanced segments with speaker info
        """
        # Load full audio
        try:
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        except Exception as e:
            logger.error(f"Failed to load audio for speaker recognition: {e}")
            return whisper_segments
        
        enhanced_segments = []
        
        for segment in whisper_segments:
            start_time = segment["start"]
            end_time = segment["end"]
            text = segment["text"]
            
            # Extract audio segment
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            segment_audio = audio[start_sample:end_sample]
            
            # Identify speaker
            speaker_name, confidence = self.speaker_service.identify_speaker(
                segment_audio, sr
            )
            
            enhanced_segment = {
                "start": start_time,
                "end": end_time,
                "text": text,
                "speaker": speaker_name if speaker_name else "Unknown",
                "speaker_confidence": round(confidence, 3)
            }
            
            enhanced_segments.append(enhanced_segment)
        
        return enhanced_segments
    
    def extract_audio_from_video(self, video_path: str) -> str:
        """
        Extract audio from video file
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to extracted audio file (temporary)
        """
        try:
            import ffmpeg
            
            # Create temporary file for audio
            temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_audio.close()
            
            logger.info(f"🎞️ Extracting audio from video: {video_path}")
            
            # Extract audio with ffmpeg
            (
                ffmpeg
                .input(video_path)
                .output(temp_audio.name, acodec='pcm_s16le', ac=1, ar='16000')
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"✅ Audio extracted to: {temp_audio.name}")
            return temp_audio.name
            
        except Exception as e:
            logger.error(f"❌ Audio extraction failed: {e}")
            raise
    
    def cleanup_temp_audio(self, audio_path: str):
        """Delete temporary audio file"""
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp audio: {e}")


# Singleton instance
_audio_processor: Optional[AudioProcessor] = None


def get_audio_processor(
    whisper_model_size: str = "large-v3",
    speaker_model_path: Optional[str] = None,
    speaker_mapping_path: Optional[str] = None,
    speaker_threshold: float = 0.7,
    use_faster_whisper: bool = True
) -> AudioProcessor:
    """
    Get audio processor singleton
    
    Args:
        whisper_model_size: Whisper model size (default: large-v3 for best quality)
        speaker_model_path: Path to speaker model
        speaker_mapping_path: Path to speaker mapping
        speaker_threshold: Confidence threshold
        use_faster_whisper: Use Faster-Whisper (CTranslate2) backend (default: True for 5-10x speedup)
        
    Returns:
        AudioProcessor instance
    """
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor(
            whisper_model_size=whisper_model_size,
            speaker_model_path=speaker_model_path,
            speaker_mapping_path=speaker_mapping_path,
            speaker_threshold=speaker_threshold,
            use_faster_whisper=use_faster_whisper
        )
    return _audio_processor
