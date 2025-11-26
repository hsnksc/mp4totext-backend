"""
Modal Stable Diffusion Service
Transcript'ten görsel oluşturma - Modal.com T4 GPU

NOTE: Modal app defined in modal_sd_app.py (standalone, no backend dependencies)
"""

import logging
import os
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Modal imports (lazy loaded)
modal = None
app = None
StableDiffusionInference = None

try:
    import modal as modal_lib
    modal = modal_lib
    
    # Import from standalone modal app file (no backend dependencies)
    # Add backend root to sys.path for Celery workers
    import sys
    from pathlib import Path
    backend_root = Path(__file__).parent.parent.parent
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    
    from modal_sd_app import app, StableDiffusionInference
    
except ImportError as e:
    logger.warning(f"⚠️ Modal library not installed or modal_sd_app.py not found: {e}")


class ModalStableDiffusionService:
    """
    Wrapper service for Modal Stable Diffusion
    Production-ready with error handling
    """
    
    def __init__(self):
        self.modal_token = os.getenv("MODAL_TOKEN_ID")
        self.modal_secret = os.getenv("MODAL_TOKEN_SECRET")
        
        if not modal or not app:
            logger.warning("⚠️ Modal library not installed")
            self._enabled = False
            return
        
        if not self.modal_token or not self.modal_secret:
            logger.warning("⚠️ Modal credentials not configured")
            self._enabled = False
        else:
            self._enabled = True
            logger.info("✅ Modal Stable Diffusion service initialized")
    
    def is_enabled(self) -> bool:
        """Check if service is enabled"""
        return self._enabled
    
    async def generate_images(
        self,
        prompt: str,
        num_images: int = 1,
        seed: Optional[int] = None
    ) -> List[bytes]:
        """
        Generate images using Modal
        
        Args:
            prompt: Image generation prompt
            num_images: Number of images (1-4)
            seed: Random seed
        
        Returns:
            List of image bytes
        """
        if not self._enabled:
            raise ValueError("Modal service not enabled - check credentials")
        
        logger.info(f"🎨 Generating {num_images} image(s) on Modal...")
        logger.info(f"   Prompt: {prompt[:100]}...")
        
        try:
            # Run app in context manager to hydrate functions
            with app.run():
                inference = StableDiffusionInference()
                images = inference.generate.remote(
                    prompt=prompt,
                    batch_size=num_images,
                    seed=seed
                )
            
            logger.info(f"✅ Generated {len(images)} image(s)")
            return images
            
        except Exception as e:
            logger.error(f"❌ Modal image generation error: {e}")
            raise ValueError(f"Image generation failed: {e}")
    
    def generate_images_sync(
        self,
        prompt: str,
        num_images: int = 1,
        seed: Optional[int] = None
    ) -> List[bytes]:
        """
        Synchronous version for Celery workers
        
        Args:
            prompt: Image generation prompt
            num_images: Number of images (1-4)
            seed: Random seed
        
        Returns:
            List of image bytes
        """
        if not self._enabled:
            raise ValueError("Modal service not enabled - check credentials")
        
        logger.info(f"🎨 [SYNC] Generating {num_images} image(s) on Modal...")
        logger.info(f"   Prompt: {prompt[:100]}...")
        
        try:
            # Run app in context manager to hydrate functions
            with app.run():
                inference = StableDiffusionInference()
                images = inference.generate.remote(
                    prompt=prompt,
                    batch_size=num_images,
                    seed=seed
                )
            
            logger.info(f"✅ Generated {len(images)} image(s)")
            return images
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Try to get more details from RemoteError
            if hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args[0] else error_msg
            
            logger.error(f"❌ Modal image generation error ({error_type}): {error_msg}")
            
            # Include error type in message for better debugging
            raise ValueError(f"Image generation failed ({error_type}): {error_msg}")
    
    def generate_batch_sync(
        self,
        prompts: List[str],
        seeds: Optional[List[int]] = None,
        high_quality: bool = True
    ) -> List[bytes]:
        """
        BATCH Image Generation - Multiple prompts at once
        
        Optimized for video generation where you need multiple segment images.
        Uses A10G GPU for faster processing.
        
        Args:
            prompts: List of prompts (one per image)
            seeds: Optional list of seeds (same length as prompts)
            high_quality: Use 50 steps (True) vs 25 steps (False)
        
        Returns:
            List of image bytes (same order as prompts)
        """
        if not self._enabled:
            raise ValueError("Modal service not enabled - check credentials")
        
        logger.info(f"🎨 [BATCH] Generating {len(prompts)} images on Modal A10G...")
        logger.info(f"   Quality: {'HIGH (50 steps)' if high_quality else 'STANDARD (25 steps)'}")
        
        try:
            with app.run():
                inference = StableDiffusionInference()
                images = inference.generate_batch.remote(
                    prompts=prompts,
                    seeds=seeds,
                    high_quality=high_quality
                )
            
            logger.info(f"✅ Generated {len(images)} images in batch")
            return images
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            if hasattr(e, 'args') and e.args:
                error_msg = str(e.args[0]) if e.args[0] else error_msg
            
            logger.error(f"❌ Modal batch generation error ({error_type}): {error_msg}")
            raise ValueError(f"Batch generation failed ({error_type}): {error_msg}")
    
    def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        if not modal:
            return {
                "status": "disabled",
                "reason": "Modal library not installed"
            }
        
        if not self._enabled:
            return {
                "status": "disabled",
                "reason": "Modal credentials not configured"
            }
        
        return {
            "status": "healthy",
            "service": "Modal Stable Diffusion",
            "model": MODEL_ID,
            "gpu": "T4",
            "estimated_cost_per_image": "$0.01"
        }


# Singleton instance
_modal_sd_service_instance = None


def get_modal_sd_service() -> ModalStableDiffusionService:
    """Get or create Modal SD service singleton"""
    global _modal_sd_service_instance
    if _modal_sd_service_instance is None:
        _modal_sd_service_instance = ModalStableDiffusionService()
    return _modal_sd_service_instance
