"""
Modal Stable Diffusion App - HIGH QUALITY VERSION
Standalone file for Modal deployment - NO backend dependencies

FEATURES:
- A10G GPU (24GB VRAM) - 2x faster than T4, better quality
- SDXL 1.0 with 50 inference steps (higher quality)
- Batch generation support (up to 4 images at once)
"""

import io
import modal

# Modal App configuration
MODAL_APP_NAME = "transcript-image-generator"
CACHE_DIR = "/cache"
# SDXL 1.0 - High quality, open access, proven model
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

# Create Modal app
app = modal.App(MODAL_APP_NAME)

# Image with dependencies (only inference dependencies)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install(
        "accelerate==0.33.0",
        "diffusers==0.31.0",
        "torch==2.5.1",
        "torchvision==0.20.1",
        "transformers~=4.44.0",
        "sentencepiece==0.2.0",
        "protobuf==3.20.3",
    )
    .env({
        "HF_XET_HIGH_PERFORMANCE": "1",
        "HF_HUB_CACHE": CACHE_DIR,
    })
)

cache_volume = modal.Volume.from_name("hf-hub-cache", create_if_missing=True)


@app.cls(
    image=image,
    gpu="A10G",  # A10G GPU (24GB VRAM) - 2x faster + better quality!
    timeout=30 * 60,  # 30 dakika - batch generation için
    min_containers=0,  # Cold start OK
    volumes={CACHE_DIR: cache_volume},
)
class StableDiffusionInference:
    """Modal Stable Diffusion inference class"""
    
    @modal.enter()
    def load_pipeline(self):
        """Load SDXL Base + Refiner for maximum quality"""
        import diffusers
        import torch
        
        # SDXL 1.0 Base - High quality foundation
        self.pipe = diffusers.DiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
            add_watermarker=False  # Remove watermark for cleaner images
        ).to("cuda")
        
        # SDXL Refiner - Adds fine details (optional, used for ultra quality)
        self.refiner = diffusers.DiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0",
            text_encoder_2=self.pipe.text_encoder_2,
            vae=self.pipe.vae,
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True
        ).to("cuda")
        
        # Enable memory optimizations for A10G
        self.pipe.enable_attention_slicing()
        self.refiner.enable_attention_slicing()
    
    @modal.method()
    def generate(
        self, 
        prompt: str, 
        batch_size: int = 1,
        seed: int | None = None,
        high_quality: bool = True
    ) -> list[bytes]:
        """
        HIGH QUALITY Image Generation with SDXL 1.0
        
        Args:
            prompt: Text prompt for image generation
            batch_size: Number of images to generate (1-4 recommended)
            seed: Base random seed (incremented for each image)
            high_quality: If True, use 50 steps (slower but better quality)
        
        Returns:
            List of PNG images as bytes
        
        Quality Modes:
            - high_quality=True:  50 steps (~4-5s per image on A10G)
            - high_quality=False: 25 steps (~2-3s per image on A10G)
        """
        import torch
        import random
        
        # Base seed
        base_seed = seed if seed is not None else random.randint(0, 2**32 - 1000)
        
        # Quality settings
        num_steps = 50 if high_quality else 25
        refiner_steps = 30 if high_quality else 0  # Use refiner only in high quality mode
        guidance = 8.5 if high_quality else 7.5
        
        # Negative prompt for quality (avoid common artifacts)
        negative_prompt = (
            "blurry, out of focus, low quality, low resolution, "
            "ugly, distorted, deformed, watermark, text, signature, "
            "oversaturated, grainy, pixelated, amateur"
        )
        
        # Generate images individually with unique seeds
        image_output = []
        for i in range(batch_size):
            # Unique seed per image
            current_seed = base_seed + i
            generator = torch.Generator("cuda").manual_seed(current_seed)
            
            # Stage 1: SDXL Base - Generate foundation
            base_output = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_images_per_prompt=1,
                num_inference_steps=num_steps,
                guidance_scale=guidance,
                generator=generator,
                output_type="latent" if refiner_steps > 0 else "pil"  # Keep latent for refiner
            )
            
            if refiner_steps > 0:
                # Stage 2: SDXL Refiner - Add fine details
                generator_refiner = torch.Generator("cuda").manual_seed(current_seed)
                images = self.refiner(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    image=base_output.images,
                    num_inference_steps=refiner_steps,
                    guidance_scale=guidance,
                    generator=generator_refiner
                ).images
            else:
                images = base_output.images
            
            # Convert to high-quality PNG
            with io.BytesIO() as buf:
                images[0].save(
                    buf, 
                    format="PNG", 
                    optimize=False,  # No optimization for max quality
                    compress_level=1  # Minimal compression
                )
                image_output.append(buf.getvalue())
            
            torch.cuda.empty_cache()
        
        return image_output
    
    @modal.method()
    def generate_batch(
        self,
        prompts: list[str],
        seeds: list[int] | None = None,
        high_quality: bool = True
    ) -> list[bytes]:
        """
        TRUE PARALLEL BATCH Generation - Multiple images simultaneously
        
        A10G GPU (24GB VRAM) can handle 2-3 images in parallel.
        Uses mini-batches for optimal GPU utilization.
        
        Args:
            prompts: List of text prompts (one per image)
            seeds: Optional list of seeds (same length as prompts)
            high_quality: Quality mode (50 steps vs 25 steps)
        
        Returns:
            List of PNG images as bytes (same order as prompts)
        """
        import torch
        import random
        
        if seeds is None:
            base_seed = random.randint(0, 2**32 - 1000)
            seeds = [base_seed + i for i in range(len(prompts))]
        
        # Quality settings
        num_steps = 50 if high_quality else 25
        refiner_steps = 20 if high_quality else 0  # Reduced refiner for batch
        guidance = 8.5 if high_quality else 7.5
        
        # Parallel batch size - A10G can handle 2-3 SDXL images at once
        # With refiner disabled for batch, we can do 3 at a time
        PARALLEL_BATCH_SIZE = 3 if not high_quality else 2
        
        # Negative prompt
        negative_prompt = (
            "blurry, out of focus, low quality, low resolution, "
            "ugly, distorted, deformed, watermark, text, signature, "
            "oversaturated, grainy, pixelated, amateur"
        )
        
        # Truncate prompts to 77 tokens (CLIP limit)
        def truncate_prompt(prompt: str, max_words: int = 60) -> str:
            words = prompt.split()
            if len(words) > max_words:
                return ' '.join(words[:max_words])
            return prompt
        
        truncated_prompts = [truncate_prompt(p) for p in prompts]
        
        image_output = []
        total_prompts = len(truncated_prompts)
        
        print(f"🚀 TRUE PARALLEL BATCH: {total_prompts} images, batch_size={PARALLEL_BATCH_SIZE}")
        
        # Process in parallel mini-batches
        for batch_start in range(0, total_prompts, PARALLEL_BATCH_SIZE):
            batch_end = min(batch_start + PARALLEL_BATCH_SIZE, total_prompts)
            batch_prompts = truncated_prompts[batch_start:batch_end]
            batch_seeds = seeds[batch_start:batch_end]
            batch_size = len(batch_prompts)
            
            print(f"   Processing batch {batch_start//PARALLEL_BATCH_SIZE + 1}: images {batch_start+1}-{batch_end}")
            
            # Create generators for each image in batch
            generators = [
                torch.Generator("cuda").manual_seed(seed) 
                for seed in batch_seeds
            ]
            
            # TRUE PARALLEL: Generate all images in this batch at once!
            base_output = self.pipe(
                prompt=batch_prompts,
                negative_prompt=[negative_prompt] * batch_size,
                num_images_per_prompt=1,
                num_inference_steps=num_steps,
                guidance_scale=guidance,
                generator=generators,
                output_type="latent" if refiner_steps > 0 else "pil"
            )
            
            if refiner_steps > 0 and batch_size <= 2:
                # Refiner only for small batches (memory intensive)
                refiner_generators = [
                    torch.Generator("cuda").manual_seed(seed) 
                    for seed in batch_seeds
                ]
                images = self.refiner(
                    prompt=batch_prompts,
                    negative_prompt=[negative_prompt] * batch_size,
                    image=base_output.images,
                    num_inference_steps=refiner_steps,
                    guidance_scale=guidance,
                    generator=refiner_generators
                ).images
            else:
                images = base_output.images
            
            # Convert batch images to PNG bytes
            for img in images:
                with io.BytesIO() as buf:
                    img.save(buf, format="PNG", optimize=False, compress_level=1)
                    image_output.append(buf.getvalue())
            
            # Cleanup GPU memory between batches
            del base_output
            if refiner_steps > 0:
                del images
            torch.cuda.empty_cache()
            
            print(f"   ✅ Batch complete: {len(image_output)}/{total_prompts} images done")
        
        print(f"🎉 ALL DONE: {len(image_output)} images generated in parallel batches!")
        return image_output
