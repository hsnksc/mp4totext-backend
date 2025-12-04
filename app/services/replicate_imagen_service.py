"""
Replicate Imagen-4 Service - Google's latest image generation model

FEATURES:
- Imagen-4: Google's state-of-the-art photorealistic image generation
- 16:9 aspect ratio support for video generation
- Safety filtering (block_medium_and_above)
- High quality output (better than FLUX in photorealism)

PERFORMANCE:
- Generation time: ~30-120 seconds per image (depends on queue)
- Cost: ~$0.02 per image (competitive with Modal)
- Quality: Photorealistic, cinematic

NOTE: Imagen-4 is slow due to cold starts. First image can take 2+ minutes.
"""
import os
import logging
import replicate
from typing import List, Optional
import io
import requests
import time

logger = logging.getLogger(__name__)

# Timeout settings
REPLICATE_TIMEOUT = 300  # 5 minutes for image generation
DOWNLOAD_TIMEOUT = 60    # 1 minute for downloading result


class ReplicateImagenService:
    """Service for Replicate Imagen-4 image generation"""
    
    def __init__(self):
        self.api_token = os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            logger.warning("⚠️ REPLICATE_API_TOKEN not set")
    
    def is_enabled(self) -> bool:
        """Check if service is enabled"""
        return bool(self.api_token)
    
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        safety_filter: str = "block_medium_and_above",
        seed: Optional[int] = None
    ) -> bytes:
        """
        Generate single image with Imagen-4
        
        Args:
            prompt: Text prompt for image generation
            aspect_ratio: Aspect ratio (16:9, 1:1, 9:16, etc.)
            safety_filter: Safety level (block_none, block_few, block_some, block_medium_and_above)
            seed: Random seed for reproducibility
        
        Returns:
            Image bytes (PNG format)
        """
        if not self.is_enabled():
            raise RuntimeError("Replicate Imagen service not enabled - missing API token")
        
        try:
            logger.info(f"🎨 [IMAGEN] Generating image with Replicate Imagen-4...")
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            logger.info(f"⏱️ Note: Imagen-4 can take 1-3 minutes due to cold starts")
            
            start_time = time.time()
            
            # Prepare input
            input_data = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "safety_filter_level": safety_filter
            }
            
            if seed is not None:
                input_data["seed"] = seed
            
            # Run Imagen-4 model with prediction API for better control
            logger.info(f"🚀 [IMAGEN] Starting prediction...")
            
            # Use predictions API instead of run() for timeout control
            prediction = replicate.predictions.create(
                model="google/imagen-4",
                input=input_data
            )
            
            # Wait for completion with timeout
            max_wait = REPLICATE_TIMEOUT
            poll_interval = 5  # Check every 5 seconds
            elapsed = 0
            
            while prediction.status not in ["succeeded", "failed", "canceled"]:
                if elapsed >= max_wait:
                    logger.error(f"❌ [IMAGEN] Timeout after {elapsed}s")
                    try:
                        prediction.cancel()
                    except:
                        pass
                    raise TimeoutError(f"Imagen-4 generation timed out after {max_wait} seconds")
                
                time.sleep(poll_interval)
                elapsed += poll_interval
                prediction.reload()
                logger.info(f"⏳ [IMAGEN] Status: {prediction.status} ({elapsed}s elapsed)")
            
            generation_time = time.time() - start_time
            logger.info(f"⏱️ [IMAGEN] Generation took {generation_time:.1f}s")
            
            if prediction.status == "failed":
                error_msg = prediction.error or "Unknown error"
                logger.error(f"❌ [IMAGEN] Prediction failed: {error_msg}")
                raise RuntimeError(f"Imagen-4 failed: {error_msg}")
            
            if prediction.status == "canceled":
                raise RuntimeError("Imagen-4 prediction was canceled")
            
            # Get output URL
            output = prediction.output
            
            # Handle Replicate response (can be string URL, list, or FileOutput object)
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            elif isinstance(output, str):
                image_url = output
            elif hasattr(output, 'url'):
                image_url = output.url() if callable(output.url) else output.url
            else:
                # If output is already bytes
                logger.info(f"✅ [IMAGEN] Generated image: {len(output)} bytes")
                return output
            
            logger.info(f"📥 Downloading image from: {image_url[:100]}...")
            
            response = requests.get(image_url, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            image_bytes = response.content
            logger.info(f"✅ [IMAGEN] Generated image: {len(image_bytes)} bytes ({len(image_bytes)/1024:.1f} KB)")
            
            return image_bytes
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for prompt rejection
            if "Prompt was rejected" in error_msg or "E006" in error_msg:
                logger.error(f"❌ [IMAGEN] Prompt rejected by safety filter: {prompt[:100]}...")
                logger.info("💡 Suggestion: Try simplifying the prompt or removing sensitive content")
            else:
                logger.error(f"❌ [IMAGEN] Generation failed: {e}")
            
            # Return None instead of raising exception
            return None
            raise
    
    def generate_images_sync(
        self,
        prompts: List[str],
        seeds: Optional[List[int]] = None,
        aspect_ratio: str = "16:9"
    ) -> List[bytes]:
        """
        Generate multiple images sequentially (for compatibility with existing code)
        
        Args:
            prompts: List of text prompts
            seeds: Optional list of seeds
            aspect_ratio: Aspect ratio for all images
        
        Returns:
            List of image bytes
        """
        if not self.is_enabled():
            logger.error("❌ Replicate Imagen service not enabled")
            return []
        
        if seeds is None:
            seeds = [None] * len(prompts)
        
        logger.info(f"🎨 [IMAGEN] Generating {len(prompts)} images sequentially...")
        
        images = []
        for i, (prompt, seed) in enumerate(zip(prompts, seeds)):
            try:
                logger.info(f"🎨 [IMAGEN] Generating image {i+1}/{len(prompts)}...")
                
                image_bytes = self.generate_image(
                    prompt=prompt,
                    seed=seed,
                    aspect_ratio=aspect_ratio
                )
                
                images.append(image_bytes)
                
            except Exception as e:
                logger.error(f"❌ [IMAGEN] Image {i+1} failed: {e}")
                images.append(None)
        
        successful = sum(1 for img in images if img is not None)
        logger.info(f"✅ [IMAGEN] Batch complete: {successful}/{len(prompts)} successful")
        
        return images
    
    def generate_batch_sync(
        self,
        prompts: List[str],
        seeds: Optional[List[int]] = None,
        aspect_ratio: str = "16:9"
    ) -> List[bytes]:
        """
        Batch generation (alias for generate_images_sync for consistency)
        
        Note: Imagen-4 doesn't have native batch API, processes sequentially
        but still faster than SDXL due to better optimization.
        """
        return self.generate_images_sync(
            prompts=prompts,
            seeds=seeds,
            aspect_ratio=aspect_ratio
        )


# Singleton instance
replicate_imagen = ReplicateImagenService()
