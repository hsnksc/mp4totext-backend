"""
Image Generator Service
Transcript → AI Prompt → Image Generation Pipeline (SDXL/FLUX/IMAGEN)

SUPPORTED MODELS:
- SDXL: Stable Diffusion XL (A10G, 50 steps, high quality)
- FLUX: FLUX.1-schnell (H100, 4 steps, ultra fast & quality)
- IMAGEN: Google Imagen-4 (Replicate, photorealistic, cinematic)
"""

import logging
from typing import List, Optional, Dict, Any
from app.services.modal_sd_service import get_modal_sd_service
from app.services.modal_flux_service import modal_flux
from app.services.replicate_imagen_service import replicate_imagen
from app.services.together_service import get_together_service

logger = logging.getLogger(__name__)


# Predefined image style prompts
IMAGE_STYLES = {
    "professional": {
        "suffix": "professional business setting, clean modern aesthetic, high quality, 4k",
        "negative": "cartoon, anime, low quality, blurry"
    },
    "artistic": {
        "suffix": "artistic illustration, creative concept art, vibrant colors, detailed",
        "negative": "photograph, realistic, plain"
    },
    "technical": {
        "suffix": "technical diagram, infographic style, clear labels, educational",
        "negative": "artistic, abstract, decorative"
    },
    "minimalist": {
        "suffix": "minimalist design, clean simple composition, white background, elegant",
        "negative": "complex, cluttered, busy"
    },
    "cinematic": {
        "suffix": "cinematic lighting, dramatic mood, film photography, depth of field",
        "negative": "flat, amateur, overexposed"
    }
}


class ImageGeneratorService:
    """
    Transcript → Prompt → Image pipeline
    """
    
    def __init__(self):
        self.modal_sd = get_modal_sd_service()  # SDXL (A10G)
        self.modal_flux = modal_flux  # FLUX (H100)
        self.replicate_imagen = replicate_imagen  # Imagen-4 (Replicate)
        self.together = get_together_service()  # Together AI for prompt generation
        
        logger.info("✅ Image Generator service initialized (SDXL + FLUX + IMAGEN)")
    
    async def generate_prompt_from_transcript(
        self,
        transcript_text: str,
        style: str = "professional",
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Transcript'ten görsel prompt oluştur (AI ile)
        
        Args:
            transcript_text: Full transcript
            style: Image style (professional, artistic, etc.)
            custom_instructions: Kullanıcının özel talimatları
        
        Returns:
            Stable Diffusion prompt
        """
        logger.info("🎨 Generating image prompt from transcript...")
        
        # Style config
        style_config = IMAGE_STYLES.get(style, IMAGE_STYLES["professional"])
        
        # System prompt for AI
        system_prompt = f"""You are an expert at creating Stable Diffusion image prompts.
Given a transcript, create a detailed, visual prompt that captures the essence of the content.

Style: {style}
Additional guidance: {style_config['suffix']}

Rules:
- Be specific and descriptive
- Include colors, mood, composition, and key visual elements
- Keep it concise (under 250 characters)
- Focus on what CAN be visualized (not abstract concepts)
- Make it suitable for the chosen style
- DO NOT include text or words in the image
- Output ONLY the prompt, no explanation"""
        
        # Custom instructions
        if custom_instructions:
            system_prompt += f"\n\nUser's custom instructions: {custom_instructions}"
        
        # Transcript summary (first 2000 chars)
        transcript_sample = transcript_text[:2000] if len(transcript_text) > 2000 else transcript_text
        
        user_prompt = f"""Create a Stable Diffusion prompt for this transcript:

{transcript_sample}

Generate ONLY the visual prompt."""
        
        try:
            # Together AI call (or fallback to simple extraction)
            if self.together.is_available():
                response = await self.together.generate_async(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model="openai/gpt-oss-120b",
                    max_tokens=200,
                    temperature=0.7
                )
                
                prompt = response.strip()
            else:
                # Fallback: Simple extraction
                prompt = self._simple_prompt_extraction(transcript_text, style)
            
            # Add style suffix
            full_prompt = f"{prompt}, {style_config['suffix']}"
            
            logger.info(f"✅ Generated prompt: {full_prompt[:100]}...")
            return full_prompt
            
        except Exception as e:
            logger.error(f"❌ Prompt generation error: {e}")
            # Fallback
            return self._simple_prompt_extraction(transcript_text, style)
    
    def _simple_prompt_extraction(self, text: str, style: str = "professional", custom_instructions: Optional[str] = None) -> str:
        """AI-powered prompt extraction (sync fallback)"""
        style_config = IMAGE_STYLES.get(style, IMAGE_STYLES["professional"])
        
        # System prompt for AI
        system_prompt = f"""You are an expert at creating image generation prompts from text.
Transform the given text into a detailed, visual prompt suitable for AI image generation (Stable Diffusion/FLUX/Imagen).

Style: {style}
Visual guidelines: {style_config['suffix']}

Rules:
- Extract the main visual scene or concept from the text
- Be specific about setting, mood, lighting, composition
- Include relevant historical/cultural context if applicable
- Keep it concise (under 200 characters)
- Focus on what CAN be visualized (not abstract concepts)
- Use descriptive adjectives and artistic terms
- DO NOT include text/words in the image
- DO NOT mention specific people, politicians, or controversial figures
- Focus on settings, atmosphere, time period, and visual elements
- Keep it safe and neutral for content filters
- Output ONLY the visual prompt, no explanation"""

        # Append custom instructions if provided
        if custom_instructions:
            system_prompt += f"\n\nUser's custom instructions: {custom_instructions}"
        
        # Transcript sample (first 500 chars for speed)
        text_sample = text[:500] if len(text) > 500 else text
        
        user_prompt = f"""Transform this text into a visual image prompt:

{text_sample}

Generate ONLY the visual prompt."""
        
        import requests
        import os
        
        try:
            # Try Together AI first
            logger.info(f"🔍 Checking Together AI availability: {self.together.is_available()}")
            
            if self.together.is_available():
                logger.info("✅ Together AI available, making API call...")
                response = requests.post(
                    "https://api.together.xyz/v1/chat/completions",
                    json={
                        "model": "openai/gpt-oss-120b",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": 150,
                        "temperature": 0.7
                    },
                    headers={
                        "Authorization": f"Bearer {self.together.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    prompt = data['choices'][0]['message']['content'].strip()
                    
                    # Validate prompt is not empty
                    if not prompt or len(prompt) < 10:
                        logger.warning(f"⚠️ Together AI returned invalid prompt: '{prompt}'")
                        raise Exception("Empty or too short prompt from Together AI")
                    
                    logger.info(f"🎨 Together AI prompt: {prompt}")
                    return prompt
                else:
                    logger.warning(f"⚠️ Together AI failed ({response.status_code}), trying Groq...")
                    raise Exception(f"Together API error: {response.status_code}")
            else:
                logger.warning("⚠️ Together AI not available, trying Groq...")
                raise Exception("Together AI not available")
                
        except Exception as e:
            logger.warning(f"⚠️ Together AI failed: {e}, trying Groq GPT-OSS-120B...")
            
            # Fallback to Groq
            try:
                groq_api_key = os.getenv("GROQ_API_KEY")
                if groq_api_key:
                    logger.info("✅ Groq available, making API call...")
                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "max_tokens": 150,
                            "temperature": 0.7
                        },
                        headers={
                            "Authorization": f"Bearer {groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        prompt = data['choices'][0]['message']['content'].strip()
                        
                        # Validate prompt is not empty
                        if not prompt or len(prompt) < 10:
                            logger.warning(f"⚠️ Groq returned invalid prompt: '{prompt}'")
                            raise Exception("Empty or too short prompt from Groq")
                        
                        logger.info(f"🎨 Groq AI prompt: {prompt}")
                        return prompt
                    else:
                        logger.warning(f"⚠️ Groq API returned {response.status_code}: {response.text[:200]}")
                else:
                    logger.warning("⚠️ GROQ_API_KEY not found")
            except Exception as groq_error:
                logger.warning(f"⚠️ Groq also failed: {groq_error}")
        
        # Fallback: Better context extraction
        logger.info("⚠️ Using fallback prompt extraction (no AI)")
        
        # Extract key context from full text (not just first sentence)
        # Look for historical dates, locations, events
        import re
        
        # Check for dates (1900s-2000s)
        dates = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
        date_context = f"{dates[0]}s era" if dates else ""
        
        # Check for locations/countries
        locations = re.findall(r'\b(Türkiye|Turkey|Almanya|Germany|İstanbul|Ankara|Berlin)\b', text, re.IGNORECASE)
        location_context = f"in {locations[0]}" if locations else ""
        
        # Check for historical keywords
        historical_keywords = ['savaş', 'war', 'treaty', 'antlaşma', 'politik', 'political', 'tarih', 'history']
        is_historical = any(keyword in text.lower() for keyword in historical_keywords)
        
        # Build contextual prompt
        if is_historical and date_context:
            base_prompt = f"Historical scene from {date_context} {location_context}".strip()
        elif date_context:
            base_prompt = f"Scene from {date_context} {location_context}".strip()
        else:
            # Last resort: first meaningful sentence
            sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
            base_prompt = sentences[0][:100] if sentences else text[:100]
        
        return f"{base_prompt}, {style_config['suffix']}"
    
    async def generate_images_from_transcript(
        self,
        transcript_text: str,
        num_images: int = 1,
        style: str = "professional",
        model_type: str = "sdxl",
        custom_prompt: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Transcript'ten görsel oluştur (full pipeline)
        
        Args:
            transcript_text: Full transcript
            num_images: Number of images (1-4)
            style: Image style
            model_type: Model (sdxl/flux)
            custom_prompt: Custom prompt (override AI-generated)
            custom_instructions: Custom instructions for prompt generation
            seed: Random seed
        
        Returns:
            {
                "prompt": str,
                "images": List[bytes],
                "count": int,
                "style": str,
                "model_type": str
            }
        """
        logger.info("=" * 80)
        logger.info(f"🎨 IMAGE GENERATION FROM TRANSCRIPT - Model: {model_type.upper()}")
        logger.info("=" * 80)
        
        # 1. Smart prompt handling - Real custom prompts are short (< 100 chars)
        # Longer text is transcript that needs AI transformation
        if custom_prompt and len(custom_prompt.strip()) < 100:
            prompt = custom_prompt.strip()
            logger.info(f"📝 Using custom prompt ({len(prompt)} chars): {prompt[:100]}...")
        else:
            if custom_prompt and len(custom_prompt.strip()) >= 100:
                logger.info(f"⚠️ Custom prompt is transcript ({len(custom_prompt)} chars), will transform with AI")
                text_to_transform = custom_prompt
            else:
                logger.info(f"🤖 No custom prompt, using transcript")
                text_to_transform = transcript_text
            
            logger.info(f"🤖 Calling AI prompt transformation for style '{style}'...")
            prompt = await self.generate_prompt_from_transcript(
                text_to_transform, 
                style,
                custom_instructions
            )
        
        # 2. Model seçimine göre görsel oluştur
        if model_type.lower() == "flux":
            # FLUX (H100, ultra quality)
            images = await self.modal_flux.generate_images(
                prompt=prompt,
                num_images=num_images,
                seed=seed
            )
        elif model_type.lower() == "imagen":
            # Imagen-4 (Replicate, photorealistic)
            logger.info("🎨 Using Replicate Imagen-4 (photorealistic)...")
            images = self.replicate_imagen.generate_batch_sync(
                prompts=[prompt] * num_images,
                seeds=[seed + i for i in range(num_images)] if seed else None,
                aspect_ratio="16:9"
            )
        else:
            # SDXL (A10G, balanced)
            images = await self.modal_sd.generate_images(
                prompt=prompt,
                num_images=num_images,
                seed=seed
            )
        
        result = {
            "prompt": prompt,
            "images": images,
            "count": len(images),
            "style": style,
            "model_type": model_type
        }
        
        logger.info("=" * 80)
        logger.info(f"✅ Generated {len(images)} image(s) with {model_type.upper()}")
        logger.info("=" * 80)
        
        return result
    
    def generate_images_from_transcript_sync(
        self,
        transcript_text: str,
        num_images: int = 1,
        style: str = "professional",
        model_type: str = "sdxl",
        custom_prompt: Optional[str] = None,
        custom_instructions: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version for Celery workers
        
        Args:
            transcript_text: Full transcript
            num_images: Number of images
            style: Image style
            model_type: Model (sdxl/flux)
            custom_prompt: Custom prompt (override AI-generated)
            custom_instructions: Custom instructions for prompt generation
            seed: Random seed
        
        Returns:
            Same as async version
        """
        logger.info("=" * 80)
        logger.info(f"🎨 [SYNC] IMAGE GENERATION - Model: {model_type.upper()}")
        logger.info("=" * 80)
        
        # Smart prompt handling - Real custom prompts are short (< 100 chars)
        # Longer text is transcript that needs AI transformation
        if custom_prompt and len(custom_prompt.strip()) < 100:
            prompt = custom_prompt.strip()
            logger.info(f"📝 Using custom prompt ({len(prompt)} chars): {prompt[:100]}...")
        else:
            if custom_prompt and len(custom_prompt.strip()) >= 100:
                logger.info(f"⚠️ Custom prompt is transcript ({len(custom_prompt)} chars), will transform with AI")
                text_to_transform = custom_prompt
            else:
                logger.info(f"🤖 No custom prompt, using transcript")
                text_to_transform = transcript_text
            
            logger.info(f"🤖 Calling AI prompt transformation for style '{style}'...")
            prompt = self._simple_prompt_extraction(text_to_transform, style, custom_instructions)
            logger.info(f"✅ AI-transformed prompt ready")
        
        logger.info(f"📝 Final Prompt: {prompt[:200]}...")
        
        # Model seçimine göre görsel oluştur (sync)
        if model_type.lower() == "flux":
            # FLUX (H100)
            images = self.modal_flux.generate_images_sync(
                prompt=prompt,
                num_images=num_images,
                seed=seed
            )
        elif model_type.lower() == "imagen":
            # Imagen-4 (Replicate)
            logger.info("🎨 Using Replicate Imagen-4 (photorealistic)...")
            images = self.replicate_imagen.generate_batch_sync(
                prompts=[prompt] * num_images,
                seeds=[seed + i for i in range(num_images)] if seed else None,
                aspect_ratio="16:9"
            )
        else:
            # SDXL (A10G)
            images = self.modal_sd.generate_images_sync(
                prompt=prompt,
                num_images=num_images,
                seed=seed
            )
        
        result = {
            "prompt": prompt,
            "images": images,
            "count": len(images),
            "style": style,
            "model_type": model_type
        }
        
        logger.info("=" * 80)
        logger.info(f"✅ Generated {len(images)} image(s) with {model_type.upper()}")
        logger.info("=" * 80)
        
        return result
    
    def health_check(self) -> Dict[str, Any]:
        """Service health check"""
        modal_health = self.modal_sd.health_check()
        together_available = self.together.is_available() if hasattr(self.together, 'is_available') else False
        
        return {
            "status": "healthy" if modal_health["status"] == "healthy" else "degraded",
            "modal_sd": modal_health,
            "ai_prompt_generation": together_available,
            "available_styles": list(IMAGE_STYLES.keys())
        }


# Singleton
_image_generator_instance = None


def get_image_generator() -> ImageGeneratorService:
    """Get or create Image Generator singleton"""
    global _image_generator_instance
    if _image_generator_instance is None:
        _image_generator_instance = ImageGeneratorService()
    return _image_generator_instance
