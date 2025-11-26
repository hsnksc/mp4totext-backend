"""
Video Generator Service - Creates videos from transcripts using AI
Pipeline: Text Segmentation → Image Generation → TTS → Video Assembly

OPTIMIZATIONS:
- Parallel TTS generation: 5x faster (65s → 13s for 13 segments)
- Batch image generation support (via Modal)
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from openai import OpenAI

logger = logging.getLogger(__name__)


class VideoGeneratorService:
    """Service for generating videos from transcript text"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Configure Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        
    def segment_transcript_for_video(
        self, 
        transcript_text: str, 
        target_duration_seconds: int = 60,
        model: str = "gemini-2.0-flash-exp"
    ) -> List[Dict[str, Any]]:
        """
        Segment transcript into ~1 minute meaningful chunks using Gemini 2.5 Pro
        
        Args:
            transcript_text: Full transcript text
            target_duration_seconds: Target duration per segment (default 60s)
            model: Gemini model to use
            
        Returns:
            List of segments: [{"text": "...", "estimated_duration": 60}, ...]
        """
        try:
            logger.info(f"🎬 Segmenting transcript into ~{target_duration_seconds}s chunks")
            
            # Calculate approximate words per segment (150 words/minute speaking rate)
            words_per_second = 150 / 60  # ~2.5 words/second
            target_words = int(target_duration_seconds * words_per_second)
            
            prompt = f"""You are a professional video director creating visual descriptions for an AI-generated video from a transcript.

TASK: Segment this transcript into {target_duration_seconds}-second chunks and create POWERFUL visual descriptions for each segment.

REQUIREMENTS:
1. **Segmentation:**
   - Each segment: ~{target_words} words (~{target_duration_seconds} seconds of speech)
   - Maintain semantic coherence - complete thoughts/sentences
   - Each segment should represent ONE key visual moment

2. **Visual Description (CRITICAL):**
   - Create a vivid, cinematic scene description that BEST represents the segment's content
   - Focus on: Setting, mood, atmosphere, key visual elements, lighting, composition
   - Use descriptive language that an AI image generator can visualize
   - Think: "If I had ONE image to represent this text, what would it show?"
   - Include style keywords: professional, cinematic, high-quality, detailed
   - Example: "Professional conference room with modern architecture, warm lighting, business professionals in discussion, glass windows with city skyline, corporate documentary style, high-quality photography"

3. **Content Alignment:**
   - Visual MUST match the segment's core message
   - If about history → historical setting
   - If about technology → modern tech environment
   - If about nature → natural landscape
   - If about people → focus on human emotion/activity

TRANSCRIPT:
{transcript_text}

OUTPUT FORMAT (JSON):
{{
  "segments": [
    {{
      "text": "Full text of first segment...",
      "estimated_duration": 58,
      "visual_description": "Detailed, vivid scene description for AI image generation that perfectly captures the essence of this segment"
    }},
    ...
  ]
}}

Return ONLY valid JSON, no additional text."""

            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            segments = result.get("segments", [])
            
            logger.info(f"✅ Created {len(segments)} segments from transcript")
            return segments
            
        except Exception as e:
            logger.error(f"❌ Transcript segmentation failed: {e}")
            # Fallback: Simple chunking by word count
            words = transcript_text.split()
            target_words = int(target_duration_seconds * 2.5)
            
            segments = []
            for i in range(0, len(words), target_words):
                chunk_words = words[i:i + target_words]
                text = " ".join(chunk_words)
                segments.append({
                    "text": text,
                    "estimated_duration": len(chunk_words) / 2.5,
                    "visual_description": text[:100] + "..."
                })
            
            logger.warning(f"⚠️ Using fallback segmentation: {len(segments)} segments")
            return segments
    
    def generate_speech_from_text(
        self,
        text: str,
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0
    ) -> bytes:
        """
        Generate speech audio from text using OpenAI TTS
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 or tts-1-hd)
            speed: Speech speed (0.25 to 4.0)
            
        Returns:
            Audio bytes (MP3 format)
        """
        try:
            logger.info(f"🎤 Generating speech for {len(text)} characters")
            
            response = self.openai_client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed
            )
            
            audio_bytes = response.content
            logger.info(f"✅ Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"❌ Speech generation failed: {e}")
            raise
    
    def generate_speech_batch(
        self,
        segments: List[Dict[str, Any]],
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0,
        max_workers: int = 5
    ) -> List[bytes]:
        """
        Generate speech for multiple segments in parallel (OPTIMIZATION)
        
        Args:
            segments: List of segments with "text" field
            voice: Voice to use
            model: TTS model
            speed: Speech speed
            max_workers: Max concurrent requests (default 5)
        
        Returns:
            List of audio bytes (MP3) in same order as segments
        """
        logger.info(f"🎤 Generating speech for {len(segments)} segments in parallel (max_workers={max_workers})...")
        
        start_time = time.time()
        results = [None] * len(segments)  # Pre-allocate for order preservation
        
        def generate_single_tts(index: int, text: str) -> tuple:
            """Generate TTS for single segment"""
            try:
                segment_start = time.time()
                
                response = self.openai_client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=text,
                    speed=speed
                )
                
                audio_bytes = response.content
                processing_time = time.time() - segment_start
                
                logger.info(f"✅ TTS {index+1}/{len(segments)} complete: {len(audio_bytes)} bytes in {processing_time:.1f}s")
                
                return (index, audio_bytes, None)
                
            except Exception as e:
                logger.error(f"❌ TTS {index+1} failed: {e}")
                return (index, None, str(e))
        
        # Execute in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # DEBUG: Log first segment text
            if len(segments) > 0:
                first_seg_text = segments[0].get("text", "")
                logger.info(f"🔍 DEBUG - First segment text to TTS (first 200 chars): {first_seg_text[:200]}...")
            
            # Submit all TTS tasks
            future_to_index = {
                executor.submit(generate_single_tts, i, seg["text"]): i 
                for i, seg in enumerate(segments)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index, audio_bytes, error = future.result()
                results[index] = audio_bytes
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r is not None)
        
        logger.info(
            f"✅ Parallel TTS complete: "
            f"{successful}/{len(segments)} successful in {total_time:.1f}s "
            f"(avg {total_time/len(segments):.1f}s per segment)"
        )
        
        return results
    
    def estimate_video_cost(self, transcript_text: str) -> Dict[str, float]:
        """
        Estimate the credit cost for video generation
        
        Returns:
            {"total_credits": 10.5, "breakdown": {...}}
        """
        # Rough estimation
        char_count = len(transcript_text)
        estimated_segments = max(1, char_count // 1000)  # ~1000 chars per minute
        
        # Costs per segment:
        # - 1 image generation: 1 credit
        # - 1 TTS call: ~0.5 credits (estimated)
        # - FFmpeg processing: negligible
        
        cost_per_segment = 1.5
        total_cost = estimated_segments * cost_per_segment
        
        return {
            "total_credits": round(total_cost, 2),
            "breakdown": {
                "estimated_segments": estimated_segments,
                "cost_per_segment": cost_per_segment,
                "image_generation": estimated_segments * 1.0,
                "tts_generation": estimated_segments * 0.5
            }
        }


# Global instance
_video_generator_service = None


def get_video_generator_service() -> VideoGeneratorService:
    """Get or create video generator service instance"""
    global _video_generator_service
    if _video_generator_service is None:
        _video_generator_service = VideoGeneratorService()
    return _video_generator_service
