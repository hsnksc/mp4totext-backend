"""
Modal FLUX Service
FLUX.1 image generation service - Ultra quality

Uses deployed Modal app via modal.Cls.lookup (NOT app.run())
Modal app: transcript-flux-generator
"""

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# Modal imports (lazy loaded)
modal = None

try:
    import modal as modal_lib
    modal = modal_lib
    logger.info("✅ Modal library imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Modal library not installed: {e}")

# Modal app name (must match deployed app)
MODAL_APP_NAME = "transcript-flux-generator"


class ModalFluxService:
    """
    Wrapper service for Modal FLUX
    Ultra-quality image generation with FLUX.1
    """
    
    def __init__(self):
        self.modal_token = os.getenv("MODAL_TOKEN_ID")
        self.modal_secret = os.getenv("MODAL_TOKEN_SECRET")
        
        if not modal:
            logger.warning("⚠️ Modal library not installed")
            self._enabled = False
            return
        
        if not self.modal_token or not self.modal_secret:
            logger.warning("⚠️ Modal credentials not configured")
            self._enabled = False
        else:
            self._enabled = True
            logger.info("✅ Modal FLUX service initialized")
    
    def _get_inference_function(self):
        """Get remote inference function from deployed Modal app"""
        try:
            # Lookup deployed Modal function
            inference_cls = modal.Cls.lookup(MODAL_APP_NAME, "FluxInference")
            return inference_cls()
        except Exception as e:
            logger.error(f"❌ Failed to lookup Modal FLUX function: {e}")
            raise ValueError(f"Modal app '{MODAL_APP_NAME}' not found. Deploy with: modal deploy modal_flux_app.py")
    
    def is_enabled(self) -> bool:
        """Check if service is enabled"""
        return self._enabled
    
    async def generate_images(
        self,
        prompt: str,
        num_images: int = 1,
        seed: Optional[int] = None,
        guidance_scale: float = 3.5,
    ) -> List[bytes]:
        """
        Generate images with FLUX (async wrapper for sync method)
        
        Args:
            prompt: Text prompt
            num_images: Number of images
            seed: Random seed
            guidance_scale: Guidance scale (3.5 recommended)
        
        Returns:
            List of PNG image bytes
        """
        # Just call sync version (Modal calls are already synchronous)
        return self.generate_images_sync(prompt, num_images, seed, guidance_scale)
    
    def generate_images_sync(
        self,
        prompt: str,
        num_images: int = 1,
        seed: Optional[int] = None,
        guidance_scale: float = 3.5,
    ) -> List[bytes]:
        """
        Generate images with FLUX (synchronous)
        
        Args:
            prompt: Text prompt for image generation
            num_images: Number of images to generate
            seed: Random seed for reproducibility
            guidance_scale: Guidance scale (3.5 recommended for FLUX)
        
        Returns:
            List of PNG image bytes
        """
        if not self.is_enabled():
            logger.error("❌ FLUX service not enabled")
            return []
        
        try:
            logger.info(f"🎨 [FLUX] Generating {num_images} image(s) on Modal H100...")
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            
            # Call deployed Modal function
            inference = self._get_inference_function()
            images = inference.generate.remote(
                prompt=prompt,
                batch_size=num_images,
                seed=seed,
                guidance_scale=guidance_scale
            )
            
            logger.info(f"✅ [FLUX] Generated {len(images)} image(s) successfully")
            return images
            
        except Exception as e:
            logger.error(f"❌ [FLUX] Generation failed: {e}", exc_info=True)
            return []
    
    def generate_batch_sync(
        self,
        prompts: List[str],
        seeds: Optional[List[int]] = None,
        guidance_scale: float = 3.5,
    ) -> List[bytes]:
        """
        Generate multiple images with different prompts (synchronous)
        
        Optimized for video generation - batch processing.
        
        Args:
            prompts: List of text prompts (one per image)
            seeds: Optional list of seeds (same length as prompts)
            guidance_scale: Guidance scale (3.5 recommended)
        
        Returns:
            List of PNG image bytes (same order as prompts)
        """
        if not self.is_enabled():
            logger.error("❌ FLUX service not enabled")
            return []
        
        try:
            logger.info(f"🎨 [FLUX BATCH] Generating {len(prompts)} images on Modal H100...")
            
            # Call deployed Modal function
            inference = self._get_inference_function()
            images = inference.generate_batch.remote(
                prompts=prompts,
                seeds=seeds,
                guidance_scale=guidance_scale
            )
            
            logger.info(f"✅ [FLUX BATCH] Generated {len(images)} images successfully")
            
            # Validate output
            if len(images) != len(prompts):
                logger.error(f"❌ [FLUX BATCH] Expected {len(prompts)} images, got {len(images)}")
                return []
            
            return images
            
        except Exception as e:
            logger.error(f"❌ [FLUX BATCH] Generation failed: {e}", exc_info=True)
            return []


# Singleton instance
modal_flux = ModalFluxService()
