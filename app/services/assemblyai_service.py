"""
AssemblyAI Transcription Service - FULL FEATURED
Speech Understanding + LLM Gateway (modern replacement for LeMUR)
Provides transcription with built-in speaker diarization
Enhanced with Whisper language detection
"""

import logging
import time
from typing import Dict, Any, Optional, List
import assemblyai as aai
from app.settings import get_settings
from app.services.language_detector import get_whisper_detector
from app.services.assemblyai.config import TranscriptionFeatures, SpeechUnderstandingConfig, LLMGatewayConfig
from app.services.assemblyai.speech_understanding import SpeechUnderstandingParser
from app.services.assemblyai.llm_gateway import LLMGatewayService

logger = logging.getLogger(__name__)
settings = get_settings()


class AssemblyAIService:
    """
    Full-featured AssemblyAI transcription service
    
    Features:
    - Speech-to-Text with speaker diarization
    - Sentiment Analysis
    - Auto Chapters
    - Entity Detection
    - Topic Detection (IAB)
    - Content Moderation
    - Auto Highlights
    - PII Redaction (optional)
    - LLM Gateway (Summary, Q&A, Action Items) - Modern, multi-model
    - Whisper-based language detection
    """
    
    def __init__(self):
        self.api_key = settings.ASSEMBLYAI_API_KEY
        
        if not self.api_key:
            logger.warning("⚠️ ASSEMBLYAI_API_KEY not configured")
            self._enabled = False
        else:
            aai.settings.api_key = self.api_key
            self._enabled = True
            
            # Initialize language detector
            try:
                self.language_detector = get_whisper_detector()
                logger.info("✅ AssemblyAI Full Service initialized")
                logger.info("   Features: ALL Speech Understanding + LLM Gateway")
            except Exception as e:
                logger.warning(f"⚠️ Language detector not available: {e}")
                self.language_detector = None
    
    def is_enabled(self) -> bool:
        """Check if service is enabled"""
        return self._enabled
    
    def transcribe_audio(
        self,
        audio_url: str,
        language: Optional[str] = None,
        enable_diarization: bool = True,
        speakers_expected: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        auto_detect_language: bool = True,
        features: Optional[TranscriptionFeatures] = None,
        llm_context: Optional[str] = None,
        llm_questions: Optional[List[str]] = None,
        llm_custom_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Full-featured audio transcription with Speech Understanding + LLM Gateway
        
        Args:
            audio_url: Public URL to audio file (MinIO URL)
            language: Language code (optional, auto-detect if None)
            enable_diarization: Enable speaker diarization
            speakers_expected: Exact number of speakers expected
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            auto_detect_language: Use Whisper to detect language first
            features: TranscriptionFeatures config (None = default, only diarization)
            llm_context: Context for LLM Gateway summary
            llm_questions: Questions for LLM Gateway Q&A
            llm_custom_prompts: Custom LLM Gateway prompts
        
        Returns:
            Comprehensive transcription results with Speech Understanding + LLM Gateway
        """
        if not self._enabled:
            raise ValueError("AssemblyAI service not enabled (API key missing)")
        
        # Default features (only diarization for backward compatibility)
        if features is None:
            features = TranscriptionFeatures()
            features.speech_understanding.speaker_labels = enable_diarization
            features.speech_understanding.speakers_expected = speakers_expected
        
        total_start = time.time()
        
        # === STEP 1: LANGUAGE DETECTION ===
        detected_language = None
        language_confidence = None
        language_detection_time = None
        
        if auto_detect_language and not language and self.language_detector:
            logger.info("=" * 80)
            logger.info("🔍 STEP 1: LANGUAGE DETECTION (Whisper)")
            logger.info("=" * 80)
            
            try:
                lang_result = self.language_detector.detect_language_from_url(audio_url)
                detected_language = lang_result['language_code']
                language_confidence = lang_result['confidence']
                language_detection_time = lang_result['detection_time']
                
                logger.info(f"✅ Language detected: {lang_result['language_name']}")
                logger.info(f"   Code: {detected_language}")
                logger.info(f"   Confidence: {language_confidence:.2%}")
                logger.info(f"   Detection time: {language_detection_time:.2f}s")
                
                # Set language for AssemblyAI
                if self.language_detector.is_supported_by_assemblyai(detected_language):
                    language = lang_result['assemblyai_code']
                    features.speech_understanding.language_code = language
                    logger.info(f"✅ Using detected language: {language}")
                    
                    # ⚠️ CRITICAL: Some features are English-only
                    if language != 'en':
                        logger.warning(f"⚠️ Language '{language}' detected - disabling English-only features")
                        logger.warning("   Disabling: sentiment_analysis, auto_chapters, auto_highlights")
                        features.speech_understanding.sentiment_analysis = False
                        features.speech_understanding.auto_chapters = False
                        features.speech_understanding.auto_highlights = False
                else:
                    logger.warning(f"⚠️ Language '{detected_language}' not supported by AssemblyAI")
                    
            except Exception as e:
                logger.error(f"❌ Language detection failed: {e}")
        
        # === STEP 2: TRANSCRIPTION + SPEECH UNDERSTANDING ===
        logger.info("=" * 80)
        logger.info("🚀 STEP 2: TRANSCRIPTION + SPEECH UNDERSTANDING")
        logger.info("=" * 80)
        logger.info(f"📤 Audio URL: {audio_url[:80]}...")
        logger.info(f"🌍 Language: {language or 'auto-detect'}")
        
        transcription_start = time.time()
        
        try:
            # Build AssemblyAI config from features
            config_dict = features.to_assemblyai_config()
            
            # Override with explicit parameters if provided
            if speakers_expected:
                config_dict["speakers_expected"] = speakers_expected
            if min_speakers or max_speakers:
                speaker_options = {}
                if min_speakers:
                    speaker_options["min_speakers_expected"] = min_speakers
                if max_speakers:
                    speaker_options["max_speakers_expected"] = max_speakers
                config_dict["speaker_options"] = aai.SpeakerOptions(**speaker_options)
            
            config = aai.TranscriptionConfig(**config_dict)
            
            # Log enabled features
            logger.info("📊 Enabled features:")
            logger.info(f"   ✓ Speaker Diarization: {config_dict.get('speaker_labels', False)}")
            logger.info(f"   ✓ Sentiment Analysis: {config_dict.get('sentiment_analysis', False)}")
            logger.info(f"   ✓ Auto Chapters: {config_dict.get('auto_chapters', False)}")
            logger.info(f"   ✓ Entity Detection: {config_dict.get('entity_detection', False)}")
            logger.info(f"   ✓ Topic Detection: {config_dict.get('iab_categories', False)}")
            logger.info(f"   ✓ Content Safety: {config_dict.get('content_safety_labels', False)}")
            logger.info(f"   ✓ Auto Highlights: {config_dict.get('auto_highlights', False)}")
            logger.info(f"   ✓ PII Redaction: {config_dict.get('redact_pii', False)}")
            
            # Transcribe
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(audio_url, config)
            
            # Check for errors
            if transcript.status == aai.TranscriptStatus.error:
                raise ValueError(f"Transcription failed: {transcript.error}")
            
            transcription_time = time.time() - transcription_start
            
            logger.info(f"✅ Transcription completed in {transcription_time:.1f}s")
            
            # Parse Speech Understanding results
            speech_understanding_results = SpeechUnderstandingParser.parse_all(transcript)
            
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}")
            raise ValueError(f"AssemblyAI transcription failed: {e}")
        
        # === STEP 3: LLM GATEWAY PROCESSING ===
        llm_results = {}
        llm_processing_time = 0
        
        if features.llm_gateway.enabled:
            logger.info("=" * 80)
            logger.info("🧠 STEP 3: LLM GATEWAY PROCESSING")
            logger.info("=" * 80)
            
            llm_start = time.time()
            
            try:
                llm_service = LLMGatewayService(features.llm_gateway)
                llm_results = llm_service.process_all(
                    transcript_text=transcript.text,  # 🔑 KEY: Send text, not transcript object
                    custom_context=llm_context,
                    custom_questions=llm_questions,
                    custom_prompts=llm_custom_prompts
                )
                
                llm_processing_time = time.time() - llm_start
                logger.info(f"✅ LLM Gateway processing completed in {llm_processing_time:.1f}s")
                
            except Exception as e:
                logger.error(f"❌ LLM Gateway processing error: {e}")
                # Continue without LLM results
        
        # === BUILD FINAL RESULT ===
        total_time = time.time() - total_start
        
        # Parse basic results for backward compatibility
        segments = []
        utterances = []
        if transcript.words:
            for word in transcript.words:
                segments.append({
                    "start": word.start / 1000.0,
                    "end": word.end / 1000.0,
                    "text": word.text,
                    "speaker": getattr(word, 'speaker', None)
                })
        
        if transcript.utterances:
            for utt in transcript.utterances:
                utterances.append({
                    "speaker": utt.speaker,
                    "start": utt.start / 1000.0,
                    "end": utt.end / 1000.0,
                    "text": utt.text,
                    "confidence": utt.confidence
                })
        
        result = {
            # Basic info
            "text": transcript.text,
            "language": language or "auto",
            "duration": (transcript.words[-1].end / 1000.0) if transcript.words else 0,
            "confidence": getattr(transcript, 'confidence', None),
            
            # Language detection
            "language_detection": {
                "detected_language": detected_language,
                "confidence": language_confidence,
                "detection_time": language_detection_time
            } if detected_language else None,
            
            # Speech Understanding results (NEW!)
            "speech_understanding": speech_understanding_results,
            
            # LLM Gateway results (NEW!)
            "llm_gateway": llm_results if llm_results else None,
            
            # Timing
            "processing_time": {
                "total": total_time,
                "language_detection": language_detection_time or 0,
                "transcription": transcription_time,
                "llm_gateway": llm_processing_time
            },
            
            # Legacy fields (backward compatibility)
            "segments": utterances,  # Use utterances as segments for mobile app
            "utterances": utterances,
            "speaker_count": len(speech_understanding_results.get("speakers", [])),
            "speakers": speech_understanding_results.get("speakers", []),
            "segments_count": len(segments),
            "language_detected_by_whisper": detected_language,
            "language_confidence": language_confidence,
            "language_detection_time": language_detection_time
        }
        
        # === FINAL LOG ===
        logger.info("=" * 80)
        logger.info("✅ COMPLETE TRANSCRIPTION FINISHED")
        logger.info("=" * 80)
        logger.info(f"📊 Results:")
        logger.info(f"   Total time: {total_time:.1f}s")
        logger.info(f"   Text length: {len(result['text'])} chars")
        logger.info(f"   Speakers: {len(speech_understanding_results['speakers'])}")
        logger.info(f"   Chapters: {len(speech_understanding_results['chapters']) if speech_understanding_results['chapters'] else 0}")
        logger.info(f"   Entities: {len(speech_understanding_results['entities']) if speech_understanding_results['entities'] else 0}")
        logger.info(f"   Topics: {len(speech_understanding_results['topics']) if speech_understanding_results['topics'] else 0}")
        logger.info(f"   Highlights: {len(speech_understanding_results['highlights']) if speech_understanding_results['highlights'] else 0}")
        if llm_results:
            logger.info(f"   LLM Gateway summary: {'✓' if 'summary' in llm_results else '✗'}")
            logger.info(f"   LLM Gateway Q&A: {len(llm_results.get('questions_and_answers', []))} answers")
            logger.info(f"   Action items: {len(llm_results.get('action_items', {}).get('items', []))}")
        logger.info("=" * 80)
        
        return result

    
    def health_check(self) -> Dict[str, Any]:
        """Check AssemblyAI service availability"""
        try:
            if not self._enabled:
                return {
                    "status": "disabled",
                    "reason": "API key not configured"
                }
            
            return {
                "status": "healthy",
                "service": "AssemblyAI Full Featured",
                "features": {
                    "speech_to_text": True,
                    "speaker_diarization": True,
                    "sentiment_analysis": True,
                    "auto_chapters": True,
                    "entity_detection": True,
                    "topic_detection": True,
                    "content_safety": True,
                    "auto_highlights": True,
                    "pii_redaction": True,
                    "lemur_summary": True,
                    "lemur_qa": True,
                    "lemur_action_items": True,
                    "whisper_language_detection": self.language_detector is not None,
                    "multi_language": True,
                    "languages_supported": 99
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton instance
_assemblyai_service_instance = None


def get_assemblyai_service() -> AssemblyAIService:
    """Get or create AssemblyAI service singleton"""
    global _assemblyai_service_instance
    if _assemblyai_service_instance is None:
        _assemblyai_service_instance = AssemblyAIService()
    return _assemblyai_service_instance
