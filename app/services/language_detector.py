"""
Dil tespit (Language Detection) servisi
Whisper'ın built-in language detection'ını kullanır
AssemblyAI entegrasyonu için optimize edilmiş
"""

import torch
import whisper
import logging
import time
import os
import tempfile
import requests
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WhisperLanguageDetector:
    """
    Fast language detection using Whisper base model
    Optimized for AssemblyAI integration
    """
    
    def __init__(self, model_name: str = "base"):
        """
        Args:
            model_name: Whisper model boyutu (tiny, base, small)
                       Dil tespiti için base yeterli ve hızlı
        """
        self.model_name = model_name
        self.model = None
        
        logger.info(f"🔍 WhisperLanguageDetector başlatılıyor (model: {model_name})")
        
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"❌ WhisperLanguageDetector yüklenemedi: {e}")
            raise
    
    def _load_model(self):
        """Whisper modelini yükle (sadece dil tespiti için)"""
        # Base model - hızlı ve yeterince doğru
        self.model = whisper.load_model(self.model_name)
        logger.info(f"✅ Whisper Language Detector initialized (base model)")
        logger.info("   Supported: 99 languages with fast detection")
    
    def detect_language_from_url(self, audio_url: str) -> Dict[str, Any]:
        """
        Detect language from audio URL (downloads temporarily)
        
        Args:
            audio_url: URL to audio file (MinIO URL)
            
        Returns:
            Dict with language detection results
        """
        logger.info(f"🔍 Downloading audio for language detection...")
        logger.info(f"   URL: {audio_url[:80]}...")
        
        try:
            # Download audio temporarily
            response = requests.get(audio_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # Detect language
            result = self.detect_language_from_file(tmp_path)
            
            # Cleanup
            os.unlink(tmp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Language detection error: {e}")
            raise ValueError(f"Language detection failed: {e}")
    
    def detect_language_from_file(self, audio_path: str) -> Dict[str, Any]:
        """
        Detect language from audio file (very fast - ~1-3 seconds)
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with language code, name, and confidence
        """
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Detecting language from file: {audio_path}")
            
            # Load and process audio (first 30 seconds only)
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)
            
            # Create mel-spectrogram
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            
            # Detect language
            _, probs = self.model.detect_language(mel)
            
            # Get top language
            detected_lang = max(probs, key=probs.get)
            confidence = probs[detected_lang]
            
            elapsed = time.time() - start_time
            
            # Map AssemblyAI language codes
            assemblyai_lang_map = {
                'en': 'en',      # English
                'tr': 'tr',      # Turkish
                'es': 'es',      # Spanish
                'fr': 'fr',      # French
                'de': 'de',      # German
                'it': 'it',      # Italian
                'pt': 'pt',      # Portuguese
                'nl': 'nl',      # Dutch
                'pl': 'pl',      # Polish
                'ru': 'ru',      # Russian
                'uk': 'uk',      # Ukrainian
                'vi': 'vi',      # Vietnamese
                'hi': 'hi',      # Hindi
                'ja': 'ja',      # Japanese
                'zh': 'zh',      # Chinese
                'ko': 'ko',      # Korean
                'ar': 'ar',      # Arabic
            }
            
            # Language names
            lang_names = {
                'en': 'English',
                'tr': 'Turkish (Türkçe)',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'it': 'Italian',
                'pt': 'Portuguese',
                'nl': 'Dutch',
                'pl': 'Polish',
                'ru': 'Russian',
                'uk': 'Ukrainian',
                'vi': 'Vietnamese',
                'hi': 'Hindi',
                'ja': 'Japanese',
                'zh': 'Chinese',
                'ko': 'Korean',
                'ar': 'Arabic',
            }
            
            # Get top 5 languages
            top_languages = dict(
                sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5]
            )
            
            result = {
                'language_code': detected_lang,
                'language_name': lang_names.get(detected_lang, detected_lang.upper()),
                'confidence': float(confidence),
                'detection_time': elapsed,
                'assemblyai_code': assemblyai_lang_map.get(detected_lang, detected_lang),
                'top_languages': {
                    lang: {
                        'code': lang,
                        'name': lang_names.get(lang, lang.upper()),
                        'probability': float(prob)
                    }
                    for lang, prob in top_languages.items()
                }
            }
            
            logger.info(f"✅ Language detected: {result['language_name']} ({detected_lang})")
            logger.info(f"   Confidence: {confidence:.2%}")
            logger.info(f"   Detection time: {elapsed:.2f}s")
            logger.info(f"   Top 3: {', '.join([f'{lang}({prob:.1%})' for lang, prob in list(top_languages.items())[:3]])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Language detection error: {e}")
            raise ValueError(f"Language detection failed: {e}")
    
    def is_supported_by_assemblyai(self, language_code: str) -> bool:
        """Check if language is supported by AssemblyAI"""
        # AssemblyAI supported languages (as of 2024)
        supported = {
            'en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'hi', 'ja',
            'zh', 'fi', 'ko', 'pl', 'ru', 'tr', 'uk', 'vi'
        }
        return language_code in supported


# Singleton instance
_whisper_detector_instance = None


def get_whisper_detector() -> WhisperLanguageDetector:
    """Get or create Whisper detector singleton"""
    global _whisper_detector_instance
    if _whisper_detector_instance is None:
        _whisper_detector_instance = WhisperLanguageDetector(model_name="base")
    return _whisper_detector_instance


# Backward compatibility aliases
LanguageDetector = WhisperLanguageDetector
get_language_detector = get_whisper_detector


def detect_audio_language(audio_path: str, confidence_threshold: float = 0.7) -> str:
    """
    Convenience function: Audio dilini tespit et ve dil kodunu döndür
    
    Args:
        audio_path: Ses dosyası yolu
        confidence_threshold: Minimum güven skoru
    
    Returns:
        Dil kodu (örn: "tr", "en", "de")
    """
    detector = get_whisper_detector()
    result = detector.detect_language_from_file(audio_path)
    return result["language_code"]
