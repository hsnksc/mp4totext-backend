"""
wav2vec2-turkish Service
Türkçe audio transcription için optimize edilmiş
"""

import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import librosa
import numpy as np
from typing import Optional, Dict, List
import logging
from pathlib import Path
from app.settings import get_settings

logger = logging.getLogger(__name__)


class Wav2Vec2Service:
    """
    wav2vec2-turkish model servisi
    Türkçe ses tanıma için optimize edilmiş - Whisper'dan daha hızlı
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Args:
            model_name: Hugging Face model ismi veya local path
                       Default: mpoyraz/wav2vec2-xls-r-300m-cv7-turkish
        """
        settings = get_settings()
        self.model_name = model_name or getattr(settings, 'WAV2VEC2_MODEL_NAME', 'mpoyraz/wav2vec2-xls-r-300m-cv7-turkish')
        self.processor = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.enabled = False
        
        logger.info(f"🎯 wav2vec2 Service başlatılıyor...")
        logger.info(f"📦 Model: {self.model_name}")
        logger.info(f"🖥️ Device: {self.device}")
        
        try:
            self._load_model()
            self.enabled = True
        except Exception as e:
            logger.warning(f"⚠️ wav2vec2 yüklenemedi (Whisper fallback kullanılacak): {e}")
            self.enabled = False
    
    def _load_model(self):
        """Model ve processor'ı yükle"""
        # Local path kontrolü
        local_model_path = Path("models/wav2vec2-turkish")
        
        if local_model_path.exists():
            logger.info(f"📂 Local model yükleniyor: {local_model_path}")
            model_path = str(local_model_path)
        else:
            logger.info(f"🌐 Hugging Face'den model yükleniyor...")
            model_path = self.model_name
        
        # Processor ve model yükle
        self.processor = Wav2Vec2Processor.from_pretrained(model_path)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_path)
        
        # GPU'ya taşı ve optimize et
        self.model.to(self.device)
        self.model.eval()  # Evaluation mode
        
        # GPU memory optimization
        if self.device == "cuda":
            self.model.half()  # FP16 for speed
            torch.cuda.empty_cache()
        
        logger.info(f"✅ wav2vec2-turkish model yüklendi: {self.device}")
    
    def is_available(self) -> bool:
        """Model kullanıma hazır mı?"""
        return self.enabled and self.model is not None
    
    def transcribe(
        self, 
        audio_path: str, 
        chunk_length_s: int = 30,
        return_timestamps: bool = False
    ) -> Dict:
        """
        Ses dosyasını metne çevir
        
        Args:
            audio_path: Ses dosyası yolu
            chunk_length_s: Chunk uzunluğu (saniye)
            return_timestamps: Timestamp döndür mü? (şimdilik desteklenmiyor)
        
        Returns:
            {
                "text": "transkripsiyon metni",
                "language": "tr",
                "duration": 125.5,
                "segments": [] (opsiyonel)
            }
        """
        if not self.is_available():
            raise RuntimeError("wav2vec2 model yüklü değil!")
        
        try:
            # Ses yükle (16kHz - wav2vec2 standardı)
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            duration = len(audio) / sr
            
            logger.info(f"🎵 Audio yüklendi: {duration:.2f}s")
            
            # Uzun ses için chunk'lara böl
            if duration > chunk_length_s:
                transcription, segments = self._transcribe_long_audio(audio, chunk_length_s)
            else:
                transcription = self._transcribe_chunk(audio)
                segments = [{"text": transcription, "start": 0.0, "end": duration}]
            
            return {
                "text": transcription,
                "language": "tr",  # wav2vec2-turkish always Turkish
                "duration": duration,
                "segments": segments if return_timestamps else []
            }
            
        except Exception as e:
            logger.error(f"❌ Transkripsiyon hatası: {e}")
            raise
    
    def _transcribe_chunk(self, audio: np.ndarray) -> str:
        """Tek bir ses chunk'ını transkripsiyonla"""
        # Input hazırla
        inputs = self.processor(
            audio, 
            sampling_rate=16000, 
            return_tensors="pt", 
            padding=True
        )
        
        # GPU'ya taşı
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        
        # Inference
        with torch.no_grad():
            logits = self.model(**inputs).logits
        
        # Decode
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)[0]
        
        # Post-processing: normalize whitespace
        transcription = " ".join(transcription.split())
        
        return transcription
    
    def _transcribe_long_audio(
        self, 
        audio: np.ndarray, 
        chunk_length_s: int
    ) -> tuple[str, List[Dict]]:
        """
        Uzun ses dosyasını chunk'lara bölerek transkripsiyonla
        
        Returns:
            (full_transcription, segments_with_timestamps)
        """
        sample_rate = 16000
        chunk_length_samples = chunk_length_s * sample_rate
        
        transcriptions = []
        segments = []
        
        # Chunk'lara böl
        for i in range(0, len(audio), chunk_length_samples):
            chunk = audio[i:i + chunk_length_samples]
            
            # Çok kısa chunk'ları atla
            if len(chunk) < sample_rate:  # 1 saniyeden kısa
                continue
            
            # Timestamp hesapla
            start_time = i / sample_rate
            end_time = min((i + len(chunk)) / sample_rate, len(audio) / sample_rate)
            
            # Transkripsiyonla
            chunk_text = self._transcribe_chunk(chunk)
            
            if chunk_text.strip():
                transcriptions.append(chunk_text)
                segments.append({
                    "text": chunk_text,
                    "start": start_time,
                    "end": end_time
                })
                
                logger.info(f"  📝 Chunk {len(segments)}: {start_time:.1f}s-{end_time:.1f}s ({len(chunk_text)} chars)")
        
        # Birleştir
        full_transcription = " ".join(transcriptions)
        
        logger.info(f"✅ Transcription tamamlandı: {len(full_transcription)} chars, {len(segments)} segments")
        
        return full_transcription, segments
    
    def download_model(self, output_dir: str = "models/wav2vec2-turkish"):
        """
        Modeli local'e indir (opsiyonel - offline kullanım için)
        
        Args:
            output_dir: Model kayıt klasörü
        """
        import os
        
        logger.info(f"📥 Model indiriliyor: {self.model_name}")
        logger.info(f"📂 Hedef: {output_dir}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Processor ve model'i indir
        processor = Wav2Vec2Processor.from_pretrained(self.model_name)
        model = Wav2Vec2ForCTC.from_pretrained(self.model_name)
        
        # Kaydet
        processor.save_pretrained(output_dir)
        model.save_pretrained(output_dir)
        
        logger.info(f"✅ Model indirildi: {output_dir}")
        logger.info(f"💡 .env dosyasına ekleyin: WAV2VEC2_MODEL_NAME={output_dir}")


# Singleton instance
_wav2vec2_service: Optional[Wav2Vec2Service] = None


def get_wav2vec2_service() -> Wav2Vec2Service:
    """Wav2Vec2 service singleton instance'ını al"""
    global _wav2vec2_service
    
    if _wav2vec2_service is None:
        _wav2vec2_service = Wav2Vec2Service()
    
    return _wav2vec2_service
