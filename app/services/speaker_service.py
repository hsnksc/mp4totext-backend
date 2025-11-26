"""
Speaker recognition service using Global Model
"""

import torch
import torch.nn as nn
import numpy as np
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import librosa

logger = logging.getLogger(__name__)

# Try to import resemblyzer
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Resemblyzer not available. Install with: pip install resemblyzer")
    RESEMBLYZER_AVAILABLE = False


class MultiSpeakerClassifier(nn.Module):
    """
    Multi-speaker classification neural network
    Same architecture as desktop app's global model
    """
    
    def __init__(self, num_speakers: int, input_dim: int = 256):
        super(MultiSpeakerClassifier, self).__init__()
        
        self.classifier = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(256, num_speakers)
        )
        
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Xavier/Glorot initialization"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(x)


class SpeakerRecognitionService:
    """
    Speaker recognition service using global model
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        mapping_path: Optional[str] = None,
        threshold: float = 0.7
    ):
        """
        Initialize speaker recognition service
        
        Args:
            model_path: Path to trained model (.pth file)
            mapping_path: Path to speaker mapping (.json file)
            threshold: Confidence threshold for recognition
        """
        self.model_path = model_path
        self.mapping_path = mapping_path
        self.threshold = threshold
        
        self.model = None
        self.speaker_mapping = None
        self.voice_encoder = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"👤 Speaker recognition service initialized (device: {self.device})")
    
    def load_model(self):
        """Load global speaker model and mapping"""
        if not self.model_path or not self.mapping_path:
            logger.warning("⚠️ No model/mapping path provided. Speaker recognition disabled.")
            return False
        
        model_file = Path(self.model_path)
        mapping_file = Path(self.mapping_path)
        
        if not model_file.exists() or not mapping_file.exists():
            logger.warning(f"⚠️ Model or mapping file not found. Speaker recognition disabled.")
            return False
        
        try:
            # Load speaker mapping
            with open(mapping_file, 'r', encoding='utf-8') as f:
                self.speaker_mapping = json.load(f)
            
            num_speakers = len(self.speaker_mapping)
            logger.info(f"📋 Loaded speaker mapping: {num_speakers} speakers")
            
            # Initialize model
            self.model = MultiSpeakerClassifier(num_speakers=num_speakers)
            
            # Load weights
            checkpoint = torch.load(model_file, map_location=self.device)
            
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.to(self.device)
            self.model.eval()
            
            # Load Resemblyzer encoder
            if RESEMBLYZER_AVAILABLE:
                self.voice_encoder = VoiceEncoder(device=self.device)
                logger.info("✅ Resemblyzer encoder loaded")
            
            logger.info(f"✅ Global speaker model loaded: {num_speakers} speakers")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load speaker model: {e}")
            return False
    
    def extract_embedding(self, audio_array: np.ndarray, sr: int = 16000) -> Optional[np.ndarray]:
        """
        Extract voice embedding from audio
        
        Args:
            audio_array: Audio samples
            sr: Sample rate
            
        Returns:
            256-dim embedding or None if failed
        """
        if not RESEMBLYZER_AVAILABLE or self.voice_encoder is None:
            return None
        
        try:
            # Resample if needed
            if sr != 16000:
                audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=16000)
            
            # Preprocess
            processed_wav = preprocess_wav(audio_array)
            
            # Extract embedding
            embedding = self.voice_encoder.embed_utterance(processed_wav)
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Embedding extraction failed: {e}")
            return None
    
    def identify_speaker(
        self,
        audio_array: np.ndarray,
        sr: int = 16000
    ) -> Tuple[Optional[str], float]:
        """
        Identify speaker from audio
        
        Args:
            audio_array: Audio samples
            sr: Sample rate
            
        Returns:
            Tuple of (speaker_name, confidence)
        """
        # Check if model is loaded
        if self.model is None:
            loaded = self.load_model()
            if not loaded:
                return None, 0.0
        
        # Extract embedding
        embedding = self.extract_embedding(audio_array, sr)
        if embedding is None:
            return None, 0.0
        
        try:
            # Convert to tensor
            embedding_tensor = torch.FloatTensor(embedding).unsqueeze(0).to(self.device)
            
            # Predict
            with torch.no_grad():
                logits = self.model(embedding_tensor)
                probabilities = torch.softmax(logits, dim=1)
                confidence, predicted_idx = torch.max(probabilities, dim=1)
            
            confidence = confidence.item()
            predicted_idx = predicted_idx.item()
            
            # Get speaker name
            speaker_name = self.speaker_mapping.get(str(predicted_idx), f"Speaker_{predicted_idx}")
            
            # Check threshold
            if confidence < self.threshold:
                return "Unknown", confidence
            
            return speaker_name, confidence
            
        except Exception as e:
            logger.error(f"❌ Speaker identification failed: {e}")
            return None, 0.0
    
    def is_available(self) -> bool:
        """Check if speaker recognition is available"""
        return (
            RESEMBLYZER_AVAILABLE and
            self.model_path is not None and
            self.mapping_path is not None and
            Path(self.model_path).exists() and
            Path(self.mapping_path).exists()
        )


# Singleton instance
_speaker_service: Optional[SpeakerRecognitionService] = None


def get_speaker_service(
    model_path: Optional[str] = None,
    mapping_path: Optional[str] = None,
    threshold: float = 0.7
) -> SpeakerRecognitionService:
    """
    Get speaker recognition service singleton
    
    Args:
        model_path: Path to model file
        mapping_path: Path to mapping file
        threshold: Confidence threshold
        
    Returns:
        SpeakerRecognitionService instance
    """
    global _speaker_service
    if _speaker_service is None:
        _speaker_service = SpeakerRecognitionService(
            model_path=model_path,
            mapping_path=mapping_path,
            threshold=threshold
        )
    return _speaker_service
