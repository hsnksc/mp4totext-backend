"""
Speaker Recognition Service
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import torch
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeakerRecognizer:
    """
    Speaker recognition and diarization service
    Supports both Silero VAD and custom trained models
    """
    
    def __init__(self, model_type: str = "silero", custom_model_path: Optional[str] = None):
        """
        Initialize speaker recognition
        
        Args:
            model_type: Model type - "silero", "resemblyzer", "custom", or "none"
            custom_model_path: Path to custom PyTorch model (.pth file)
        """
        self.model_type = model_type
        self.custom_model_path = custom_model_path
        self.model = None
        self.resemblyzer_encoder = None
        
        if model_type == "silero":
            self._load_silero_model()
        elif model_type == "resemblyzer":
            self._load_resemblyzer_model()
        elif model_type == "custom" and custom_model_path:
            self._load_custom_model(custom_model_path)
        elif model_type == "none":
            logger.info("Speaker recognition disabled")
        else:
            logger.warning(f"Unknown model type: {model_type}, using Resemblyzer as fallback")
            self.model_type = "resemblyzer"
            self._load_resemblyzer_model()
    
    def _load_silero_model(self):
        """Load Silero VAD model"""
        try:
            # Load Silero VAD model from torch hub
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            
            self.get_speech_timestamps = utils[0]
            logger.info("Silero VAD model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}", exc_info=True)
            self.model = None
    
    def _load_resemblyzer_model(self):
        """Load Resemblyzer voice encoder (no FFmpeg dependency)"""
        try:
            from resemblyzer import VoiceEncoder
            
            self.resemblyzer_encoder = VoiceEncoder()
            logger.info("Resemblyzer voice encoder loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Resemblyzer: {e}", exc_info=True)
            self.resemblyzer_encoder = None
    
    def _load_custom_model(self, model_path: str):
        """
        Load custom trained speaker recognition model
        
        Args:
            model_path: Path to .pth model file
        """
        try:
            model_file = Path(model_path)
            
            if not model_file.exists():
                logger.error(f"Custom model not found: {model_path}")
                # Fallback to Silero
                self.model_type = "silero"
                self._load_silero_model()
                return
            
            # Load custom PyTorch model
            self.model = torch.load(model_path, map_location='cpu')
            
            # Set to evaluation mode
            if hasattr(self.model, 'eval'):
                self.model.eval()
            
            logger.info(f"Custom speaker model loaded from: {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load custom model: {e}", exc_info=True)
            # Fallback to Silero
            self.model_type = "silero"
            self._load_silero_model()
    
    def recognize_speakers(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]]
    ) -> Tuple[int, List[str], List[Dict[str, Any]]]:
        """
        Perform speaker diarization on transcription segments
        
        Args:
            audio_path: Path to audio file
            segments: Transcription segments from Whisper
        
        Returns:
            Tuple of (speaker_count, speaker_names, enhanced_segments)
        """
        if self.model_type == "none" or not self.model:
            logger.info("Speaker recognition disabled or model not loaded")
            return 0, [], segments
        
        try:
            if self.model_type == "silero":
                return self._recognize_with_silero(audio_path, segments)
            elif self.model_type == "resemblyzer":
                return self._recognize_with_resemblyzer(audio_path, segments)
            elif self.model_type == "custom":
                return self._recognize_with_custom_model(audio_path, segments)
            else:
                return 0, [], segments
                
        except Exception as e:
            logger.error(f"Speaker recognition failed: {e}", exc_info=True)
            return 0, [], segments
    
    def _recognize_with_silero(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]]
    ) -> Tuple[int, List[str], List[Dict[str, Any]]]:
        """
        Perform speaker diarization using Silero VAD
        
        This is a simplified implementation. For production use,
        consider integrating with pyannote.audio or similar libraries.
        """
        try:
            import torchaudio
            
            # Load audio
            wav, sr = torchaudio.load(audio_path)
            
            # Resample to 16kHz if needed
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                wav = resampler(wav)
            
            # Convert to mono if stereo
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=True)
            
            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                wav,
                self.model,
                sampling_rate=16000
            )
            
            # Simple speaker assignment based on silence gaps
            # In production, use clustering algorithms
            speakers_detected = self._assign_speakers_simple(segments, speech_timestamps)
            
            speaker_count = len(set(s.get('speaker', 'Speaker_0') for s in speakers_detected))
            speaker_names = [f"Speaker_{i+1}" for i in range(speaker_count)]
            
            logger.info(f"Detected {speaker_count} speakers using Silero VAD")
            
            return speaker_count, speaker_names, speakers_detected
            
        except Exception as e:
            logger.error(f"Silero speaker recognition failed: {e}", exc_info=True)
            return 0, [], segments
    
    def _recognize_with_resemblyzer(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]]
    ) -> Tuple[int, List[str], List[Dict[str, Any]]]:
        """
        Perform speaker diarization using Resemblyzer (no FFmpeg dependency)
        
        Resemblyzer uses voice embeddings to cluster speakers.
        More lightweight than Silero but requires librosa for audio loading.
        """
        try:
            from resemblyzer import preprocess_wav
            from sklearn.cluster import AgglomerativeClustering
            import librosa
            
            if not self.resemblyzer_encoder:
                logger.error("Resemblyzer encoder not loaded")
                return 0, [], segments
            
            # Load audio with librosa (no FFmpeg dependency)
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            
            # Preprocess for Resemblyzer
            wav = preprocess_wav(audio, source_sr=sr)
            
            # Extract embeddings for each segment
            embeddings = []
            valid_segments = []
            
            for segment in segments:
                start = segment.get('start', 0)
                end = segment.get('end', start + 1)
                
                # Extract segment audio
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                segment_audio = audio[start_sample:end_sample]
                
                # Skip very short segments (< 0.3 seconds)
                if len(segment_audio) < sr * 0.3:
                    continue
                
                # Preprocess and encode
                try:
                    segment_wav = preprocess_wav(segment_audio, source_sr=sr)
                    embedding = self.resemblyzer_encoder.embed_utterance(segment_wav)
                    embeddings.append(embedding)
                    valid_segments.append(segment)
                except Exception as e:
                    logger.warning(f"Failed to embed segment at {start}s-{end}s: {e}")
                    continue
            
            if not embeddings:
                logger.warning("No valid embeddings extracted")
                return 0, [], segments
            
            # Cluster embeddings to identify speakers
            embeddings_array = np.array(embeddings)
            
            # Use agglomerative clustering (distance threshold = 0.7)
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=0.7,
                linkage='average'
            )
            speaker_labels = clustering.fit_predict(embeddings_array)
            
            # Assign speaker labels to segments
            enhanced_segments = []
            segment_idx = 0
            
            for segment in segments:
                if segment_idx < len(valid_segments) and segment == valid_segments[segment_idx]:
                    enhanced_segment = segment.copy()
                    enhanced_segment['speaker'] = f"Speaker_{speaker_labels[segment_idx] + 1}"
                    enhanced_segments.append(enhanced_segment)
                    segment_idx += 1
                else:
                    # Segment too short, use previous speaker or default
                    enhanced_segment = segment.copy()
                    if enhanced_segments:
                        enhanced_segment['speaker'] = enhanced_segments[-1].get('speaker', 'Speaker_1')
                    else:
                        enhanced_segment['speaker'] = 'Speaker_1'
                    enhanced_segments.append(enhanced_segment)
            
            speaker_count = len(set(speaker_labels)) if len(speaker_labels) > 0 else 0
            speaker_names = [f"Speaker_{i+1}" for i in range(speaker_count)]
            
            logger.info(f"Detected {speaker_count} speakers using Resemblyzer")
            
            return speaker_count, speaker_names, enhanced_segments
            
        except Exception as e:
            logger.error(f"Resemblyzer speaker recognition failed: {e}", exc_info=True)
            return 0, [], segments
    
    def _recognize_with_custom_model(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]]
    ) -> Tuple[int, List[str], List[Dict[str, Any]]]:
        """
        Perform speaker recognition using custom trained model
        
        This is a placeholder for custom model integration.
        Implement based on your model's architecture and requirements.
        """
        try:
            logger.info("Using custom speaker recognition model")
            
            # TODO: Implement custom model inference
            # This depends on your model architecture
            # For now, use a simple speaker assignment
            
            enhanced_segments = []
            current_speaker = 1
            
            for i, segment in enumerate(segments):
                # Simple heuristic: change speaker every 5 segments
                # Replace with actual model inference
                if i > 0 and i % 5 == 0:
                    current_speaker += 1
                
                enhanced_segment = segment.copy()
                enhanced_segment['speaker'] = f"Speaker_{current_speaker}"
                enhanced_segments.append(enhanced_segment)
            
            speaker_count = current_speaker
            speaker_names = [f"Speaker_{i+1}" for i in range(speaker_count)]
            
            logger.info(f"Custom model detected {speaker_count} speakers")
            
            return speaker_count, speaker_names, enhanced_segments
            
        except Exception as e:
            logger.error(f"Custom speaker recognition failed: {e}", exc_info=True)
            return 0, [], segments
    
    def _assign_speakers_simple(
        self,
        segments: List[Dict[str, Any]],
        speech_timestamps: List[Dict[str, int]]
    ) -> List[Dict[str, Any]]:
        """
        Simple speaker assignment based on silence gaps
        
        This is a basic implementation. For better results,
        use speaker embedding clustering.
        """
        enhanced_segments = []
        current_speaker = 1
        last_end_time = 0
        
        for segment in segments:
            start_time = segment.get('start', 0)
            
            # If there's a gap > 2 seconds, change speaker
            if start_time - last_end_time > 2.0:
                current_speaker += 1
            
            enhanced_segment = segment.copy()
            enhanced_segment['speaker'] = f"Speaker_{current_speaker}"
            enhanced_segments.append(enhanced_segment)
            
            last_end_time = segment.get('end', start_time)
        
        return enhanced_segments


def create_speaker_recognizer(
    model_type: str = "silero",
    custom_model_path: Optional[str] = None
) -> SpeakerRecognizer:
    """
    Factory function to create speaker recognizer
    
    Args:
        model_type: "silero", "custom", or "none"
        custom_model_path: Path to custom model file
    
    Returns:
        SpeakerRecognizer instance
    """
    return SpeakerRecognizer(model_type=model_type, custom_model_path=custom_model_path)
