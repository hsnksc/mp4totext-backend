"""
Modal FLUX App - ULTRA QUALITY VERSION
Standalone file for Modal deployment - NO backend dependencies

FEATURES:
- H100 GPU - Fastest generation
- FLUX.1-schnell - Black Forest Labs' latest model
- 4 inference steps - Ultra fast
- Higher quality than SDXL
"""

import io
import modal
from pathlib import Path

# Modal App configuration
MODAL_APP_NAME = "transcript-flux-generator"
CACHE_DIR = "/cache"
MODEL_VARIANT = "schnell"  # or "dev"
NUM_INFERENCE_STEPS = 4  # 4 for schnell, ~50 for dev

# CUDA base image for H100 optimization
cuda_version = "12.4.0"
flavor = "devel"
operating_sys = "ubuntu22.04"
tag = f"{cuda_version}-{flavor}-{operating_sys}"

cuda_dev_image = modal.Image.from_registry(
    f"nvidia/cuda:{tag}", add_python="3.11"
).entrypoint([])

# Diffusers commit for FLUX support
diffusers_commit_sha = "81cf3b2f155f1de322079af28f625349ee21ec6b"

flux_image = (
    cuda_dev_image.apt_install(
        "git",
        "libglib2.0-0",
        "libsm6",
        "libxrender1",
        "libxext6",
        "ffmpeg",
        "libgl1",
    )
    .uv_pip_install(
        "invisible_watermark==0.2.0",
        "transformers==4.44.0",
        "huggingface-hub==0.36.0",
        "accelerate==0.33.0",
        "safetensors==0.4.4",
        "sentencepiece==0.2.0",
        "torch==2.5.0",
        f"git+https://github.com/huggingface/diffusers.git@{diffusers_commit_sha}",
        "numpy<2",
    )
    .env({
        "HF_XET_HIGH_PERFORMANCE": "1",
        "HF_HUB_CACHE": CACHE_DIR,
        "TORCHINDUCTOR_CACHE_DIR": "/root/.inductor-cache",
        "TORCHINDUCTOR_FX_GRAPH_CACHE": "1",
    })
)

# Create Modal app
app = modal.App(MODAL_APP_NAME, image=flux_image)

# Import FLUX pipeline
with flux_image.imports():
    import torch
    from diffusers import FluxPipeline


MINUTES = 60  # seconds


@app.cls(
    gpu="H100",  # H100 for maximum performance
    scaledown_window=30 * MINUTES,  # Keep container warm for 30 minutes (reduce cold starts)
    timeout=60 * MINUTES,
    volumes={
        "/cache": modal.Volume.from_name("hf-hub-cache", create_if_missing=True),
        "/root/.nv": modal.Volume.from_name("nv-cache", create_if_missing=True),
        "/root/.triton": modal.Volume.from_name("triton-cache", create_if_missing=True),
        "/root/.inductor-cache": modal.Volume.from_name(
            "inductor-cache", create_if_missing=True
        ),
    },
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
@modal.concurrent(max_inputs=5)  # Allow up to 5 concurrent requests per container
class FluxInference:
    """FLUX.1 Image Generation on H100"""
    
    @modal.enter()
    def load_pipeline(self):
        """Load FLUX pipeline (runs once per container)"""
        import os
        
        print(f"🎨 Loading FLUX.1-{MODEL_VARIANT} pipeline...")
        
        # Get HuggingFace token from secret
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if not hf_token:
            raise ValueError("HuggingFace token not found. Set HF_TOKEN in Modal secret.")
        
        print(f"✅ HuggingFace token found (length: {len(hf_token)})")
        
        # Load FLUX pipeline with authentication
        self.pipe = FluxPipeline.from_pretrained(
            f"black-forest-labs/FLUX.1-{MODEL_VARIANT}",
            torch_dtype=torch.bfloat16,
            token=hf_token
        ).to("cuda")
        
        # Apply optimizations
        self.pipe = self._optimize(self.pipe, compile=False)  # No torch.compile by default
        
        print(f"✅ FLUX.1-{MODEL_VARIANT} pipeline loaded")
    
    def _optimize(self, pipe, compile=False):
        """Apply FLUX optimizations"""
        # Fuse QKV projections
        pipe.transformer.fuse_qkv_projections()
        pipe.vae.fuse_qkv_projections()
        
        # Switch to channels_last memory layout
        pipe.transformer.to(memory_format=torch.channels_last)
        pipe.vae.to(memory_format=torch.channels_last)
        
        if compile:
            # torch.compile for maximum speed (takes 20+ minutes first time)
            config = torch._inductor.config
            config.disable_progress = False
            config.conv_1x1_as_mm = True
            config.coordinate_descent_tuning = True
            config.coordinate_descent_check_all_directions = True
            config.epilogue_fusion = False
            
            pipe.transformer = torch.compile(
                pipe.transformer, mode="max-autotune", fullgraph=True
            )
            pipe.vae.decode = torch.compile(
                pipe.vae.decode, mode="max-autotune", fullgraph=True
            )
            
            print("🔦 Running torch compilation (may take 20+ minutes)...")
            pipe(
                "dummy prompt to trigger compilation",
                output_type="pil",
                num_inference_steps=NUM_INFERENCE_STEPS,
            )
            print("✅ Torch compilation complete")
        
        return pipe
    
    @modal.method()
    def generate(
        self,
        prompt: str,
        batch_size: int = 1,
        seed: int | None = None,
        guidance_scale: float = 3.5,  # FLUX recommended value
    ) -> list[bytes]:
        """
        Generate images with FLUX.1
        
        Args:
            prompt: Text prompt
            batch_size: Number of images to generate
            seed: Random seed for reproducibility
            guidance_scale: Guidance scale (3.5 recommended for FLUX)
        
        Returns:
            List of PNG image bytes
        """
        import torch
        import random
        
        # Base seed
        base_seed = seed if seed is not None else random.randint(0, 2**32 - 1000)
        
        # Negative prompt for quality
        negative_prompt = (
            "blurry, out of focus, low quality, low resolution, "
            "ugly, distorted, deformed, watermark, text, signature, "
            "oversaturated, grainy, pixelated, amateur, worst quality"
        )
        
        # Generate images
        image_output = []
        for i in range(batch_size):
            current_seed = base_seed + i
            generator = torch.Generator("cuda").manual_seed(current_seed)
            
            # FLUX generation
            images = self.pipe(
                prompt=prompt,
                num_inference_steps=NUM_INFERENCE_STEPS,  # 4 steps for schnell
                guidance_scale=guidance_scale,
                generator=generator,
                output_type="pil",
            ).images
            
            # Convert to high-quality PNG
            with io.BytesIO() as buf:
                images[0].save(
                    buf,
                    format="PNG",
                    optimize=False,
                    compress_level=1
                )
                image_output.append(buf.getvalue())
            
            torch.cuda.empty_cache()
        
        return image_output
    
    @modal.method()
    def generate_batch(
        self,
        prompts: list[str],
        seeds: list[int] | None = None,
        guidance_scale: float = 3.5,
    ) -> list[bytes]:
        """
        BATCH Generation - Generate multiple images with different prompts
        
        Args:
            prompts: List of text prompts (one per image)
            seeds: Optional list of seeds (same length as prompts)
            guidance_scale: Guidance scale (3.5 recommended)
        
        Returns:
            List of PNG image bytes (one per prompt)
        """
        import torch
        import random
        
        # Prepare seeds
        if seeds is None:
            base_seed = random.randint(0, 2**32 - 10000)
            seeds = [base_seed + i for i in range(len(prompts))]
        
        # Negative prompt
        negative_prompt = (
            "blurry, out of focus, low quality, low resolution, "
            "ugly, distorted, deformed, watermark, text, signature, "
            "oversaturated, grainy, pixelated, amateur, worst quality"
        )
        
        all_images = []
        
        print(f"🚀 Batch generating {len(prompts)} images on H100...")
        
        # H100 has 80GB VRAM - we can be more aggressive!
        # FLUX.1-schnell with 4 steps is very efficient
        for i, (prompt, seed) in enumerate(zip(prompts, seeds)):
            print(f"   Generating {i+1}/{len(prompts)}: {prompt[:60]}...")
            
            generator = torch.Generator("cuda").manual_seed(seed)
            
            # FLUX generation
            images = self.pipe(
                prompt=prompt,
                num_inference_steps=NUM_INFERENCE_STEPS,
                guidance_scale=guidance_scale,
                generator=generator,
                output_type="pil",
            ).images
            
            # Convert to high-quality PNG
            with io.BytesIO() as buf:
                images[0].save(
                    buf,
                    format="PNG",
                    optimize=False,
                    compress_level=1
                )
                all_images.append(buf.getvalue())
            
            # Light cleanup (but keep model loaded)
            if i % 5 == 0:
                torch.cuda.empty_cache()
        
        print(f"✅ Batch complete: {len(all_images)} images generated")
        return all_images


# Local test function
@app.local_entrypoint()
def main(prompt: str = "a beautiful landscape with mountains and a lake at sunset"):
    """Test FLUX generation locally"""
    print(f"🎨 Generating image with FLUX.1-{MODEL_VARIANT}...")
    
    image_bytes = FluxInference().generate.remote(prompt, batch_size=1)
    
    output_path = Path("/tmp") / "flux" / "output.png"
    output_path.parent.mkdir(exist_ok=True, parents=True)
    output_path.write_bytes(image_bytes[0])
    
    print(f"✅ Image saved to {output_path}")
