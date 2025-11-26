"""
Faster-Whisper Service - CTranslate2 backend ile optimize edilmiş
5-10x daha hızlı, daha düşük VRAM kullanımı
"""

from faster_whisper import WhisperModel
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import torch
from app.settings import get_settings

logger = logging.getLogger(__name__)


class FasterWhisperService:
    """
    Faster-Whisper service with CTranslate2 backend
    - 5-10x faster than OpenAI Whisper
    - Lower VRAM usage
    - Better throughput for production
    """
    
    def __init__(self, model_size: str = "large-v3"):
        """
        Initialize Faster-Whisper service
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3)
        """
        self.model_size = model_size
        self.model = None
        
        # Device ve compute type ayarları
        settings = get_settings()
        self.device = getattr(settings, 'FASTER_WHISPER_DEVICE', 'auto')
        self.compute_type = getattr(settings, 'FASTER_WHISPER_COMPUTE_TYPE', 'auto')
        
        # Auto device selection
        if self.device == 'auto':
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Auto compute type selection
        if self.compute_type == 'auto':
            if self.device == "cuda":
                # CUDA - GPU'da mixed precision kullan (daha hızlı)
                self.compute_type = "float16"
            else:
                # CPU'da int8 quantization kullan (hızlı + düşük memory)
                self.compute_type = "int8"
        
        logger.info(f"🚀 FasterWhisper initializing...")
        logger.info(f"   📦 Model: {self.model_size}")
        logger.info(f"   🖥️  Device: {self.device}")
        logger.info(f"   ⚙️  Compute Type: {self.compute_type}")
    
    def load_model(self):
        """Load Faster-Whisper model with CTranslate2"""
        if self.model is None:
            logger.info(f"📥 Loading Faster-Whisper model: {self.model_size}")
            
            try:
                # Model yükle (ilk sefer Hugging Face'den indirir)
                self.model = WhisperModel(
                    model_size_or_path=self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=4,  # CPU thread sayısı
                    num_workers=1   # Parallel worker sayısı
                )
                
                logger.info(f"✅ Faster-Whisper model loaded: {self.model_size}")
                logger.info(f"   🎯 Device: {self.device}")
                logger.info(f"   ⚙️  Compute: {self.compute_type}")
                
            except Exception as e:
                logger.error(f"❌ Faster-Whisper model loading failed: {e}")
                raise
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe",
        beam_size: int = 5,
        best_of: int = 5,
        temperature: float = 0.0,  # 0.0 = greedy (en güvenilir), 0.2-0.8 = daha yaratıcı
        vad_filter: bool = True,
        vad_parameters: Optional[Dict] = None,
        # 🔥 Anti-hallucination parametreleri (dengelenmiş)
        condition_on_previous_text: bool = False,  # Tekrarları önler
        compression_ratio_threshold: float = 2.4,  # Yüksek sıkıştırma = hallucination
        log_prob_threshold: float = -1.5,          # -1.5 = daha az filtreleme (was -1.0)
        no_speech_threshold: float = 0.7           # 0.7 = daha az sessizlik atma (was 0.6)
    ) -> Dict[str, Any]:
        """
        Transcribe audio file with Faster-Whisper
        
        Args:
            audio_path: Path to audio file
            language: Language code (None for auto-detect)
            task: "transcribe" or "translate" (to English)
            beam_size: Beam search size (default: 5)
            best_of: Number of candidates (default: 5)
            temperature: Sampling temperature (0.0 = greedy, 0.2-0.8 = creative)
            vad_filter: Voice Activity Detection filter (removes silence)
            vad_parameters: Custom VAD parameters
            condition_on_previous_text: False = prevent hallucination loops (RECOMMENDED)
            compression_ratio_threshold: Max text compression ratio (2.4 = hallucination detector)
            log_prob_threshold: Min avg log probability (-1.0 = filter low confidence)
            no_speech_threshold: Speech detection threshold (0.6 = balanced)
            
        Returns:
            Dictionary with transcription results
        """
        # Model yükle (lazy loading)
        self.load_model()
        
        # Dosya kontrolü
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"🎙️  Transcribing with Faster-Whisper: {audio_file.name}")
        logger.info(f"   🌍 Language: {language or 'auto-detect'}")
        logger.info(f"   📝 Task: {task}")
        
        try:
            # VAD parametreleri (silence removal için)
            if vad_filter and vad_parameters is None:
                vad_parameters = {
                    "threshold": 0.4,           # 0.4 = daha hassas konuşma tespiti (was 0.5)
                    "min_speech_duration_ms": 200,  # 200ms = daha kısa segmentler kabul (was 250)
                    "max_speech_duration_s": float("inf"),
                    "min_silence_duration_ms": 1500,  # 1.5s = daha az kesinti (was 2000)
                    "speech_pad_ms": 300        # 300ms = daha az padding (was 400)
                }
            
            # Transcribe (generator döndürür - memory efficient)
            # Anti-hallucination parametreleri ekledik
            segments, info = self.model.transcribe(
                audio=str(audio_path),
                language=language,
                task=task,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                vad_filter=vad_filter,
                vad_parameters=vad_parameters,
                word_timestamps=False,  # Kelime seviyesi timestamp (opsiyonel)
                # 🔥 HALLUCINATION ÖNLEYİCİ PARAMETRELER
                condition_on_previous_text=condition_on_previous_text,
                compression_ratio_threshold=compression_ratio_threshold,
                log_prob_threshold=log_prob_threshold,
                no_speech_threshold=no_speech_threshold
            )
            
            # Segmentleri topla ve filtrele
            transcription_segments = []
            full_text = []
            filtered_count = 0
            
            for segment in segments:
                # 🔥 HALLUCINATION FİLTRELEME
                # 1. Çok düşük güven skorunu atar
                if segment.avg_logprob < log_prob_threshold:
                    filtered_count += 1
                    logger.debug(f"   ⚠️  Filtered segment {segment.id}: low confidence ({segment.avg_logprob:.2f})")
                    continue
                
                # 2. Sessizlik segmentlerini atar
                if segment.no_speech_prob > no_speech_threshold:
                    filtered_count += 1
                    logger.debug(f"   ⚠️  Filtered segment {segment.id}: no speech ({segment.no_speech_prob:.2f})")
                    continue
                
                # 3. Çok kısa segmentleri atar (< 1 saniye ve < 5 karakter)
                segment_duration = segment.end - segment.start
                segment_text = segment.text.strip()
                if segment_duration < 1.0 and len(segment_text) < 5:
                    filtered_count += 1
                    logger.debug(f"   ⚠️  Filtered segment {segment.id}: too short")
                    continue
                
                # 4. Aşırı tekrarlayan segmentleri algıla (hallucination pattern)
                words = segment_text.split()
                if len(words) > 5:
                    # Kelime tekrar oranını hesapla
                    unique_words = len(set(words))
                    repetition_ratio = unique_words / len(words)
                    if repetition_ratio < 0.3:  # %30'dan az benzersiz kelime = tekrar
                        filtered_count += 1
                        logger.debug(f"   ⚠️  Filtered segment {segment.id}: high repetition ({repetition_ratio:.2%})")
                        continue
                
                # Geçerli segment - ekle
                segment_dict = {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment_text,
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob
                }
                
                transcription_segments.append(segment_dict)
                full_text.append(segment_text)
                
                # Log her 10 segment
                if segment.id % 10 == 0:
                    logger.info(f"   📝 Segment {segment.id}: {segment.start:.1f}s-{segment.end:.1f}s")
            
            # Birleştirilmiş text
            combined_text = " ".join(full_text)
            
            logger.info(f"✅ Faster-Whisper transcription completed")
            logger.info(f"   🌍 Detected language: {info.language} ({info.language_probability:.2%})")
            logger.info(f"   📝 Text length: {len(combined_text)} characters")
            logger.info(f"   🎬 Segments: {len(transcription_segments)} (filtered: {filtered_count})")
            logger.info(f"   ⏱️  Duration: {info.duration:.1f}s")
            
            return {
                "text": combined_text,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": transcription_segments,
                "task": task,
                "model": self.model_size,
                "device": self.device,
                "compute_type": self.compute_type
            }
            
        except Exception as e:
            logger.error(f"❌ Faster-Whisper transcription failed: {e}")
            raise
    
    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe with detailed segment timestamps
        
        Args:
            audio_path: Path to audio file
            language: Language code
            
        Returns:
            Dictionary with segments including timestamps
        """
        result = self.transcribe(
            audio_path=audio_path,
            language=language,
            vad_filter=True  # VAD her zaman açık timestamp için
        )
        
        return {
            "text": result.get("text"),
            "language": result.get("language"),
            "duration": result.get("duration"),
            "segments": result.get("segments", [])
        }
    
    def detect_language(self, audio_path: str) -> Dict[str, float]:
        """
        Detect audio language without full transcription
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with language probabilities
        """
        self.load_model()
        
        try:
            logger.info(f"🔍 Detecting language: {audio_path}")
            
            # Sadece ilk 30 saniyeyi kullan (hızlı)
            segments, info = self.model.transcribe(
                audio=str(audio_path),
                language=None,  # Auto-detect
                beam_size=1,    # Hızlı detection için
                best_of=1,
                temperature=0.0,
                vad_filter=True
            )
            
            # İlk segment'i al (generator)
            first_segment = next(segments, None)
            
            result = {
                "language": info.language,
                "probability": info.language_probability,
                "duration": info.duration
            }
            
            logger.info(f"✅ Language detected: {info.language} ({info.language_probability:.2%})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Language detection failed: {e}")
            raise


# Singleton instance
_faster_whisper_service: Optional[FasterWhisperService] = None


def get_faster_whisper_service(model_size: str = "large-v3") -> FasterWhisperService:
    """
    Get Faster-Whisper service singleton
    
    Args:
        model_size: Model size to use
        
    Returns:
        FasterWhisperService instance
    """
    global _faster_whisper_service
    
    if _faster_whisper_service is None:
        _faster_whisper_service = FasterWhisperService(model_size=model_size)
    
    return _faster_whisper_service
