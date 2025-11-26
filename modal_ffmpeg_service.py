"""
Modal FFmpeg Service - Remote FFmpeg Processing
Hızlı, ucuz ve ölçeklenebilir FFmpeg işlemleri için Modal deployment

FEATURES:
- Video assembly (image + audio → video)
- Video concatenation (multiple segments → final video)
- Audio extraction from video files
- Parallel processing support
- Auto-scaling on demand
- GPU not needed (CPU işlemleri)

PRICING:
- CPU: $0.000025/second (~$0.09/hour)
- Storage: Free for temp files
- Modal deployment ücretsiz tier: 50 saat/ay
"""

import modal
import io
from typing import List, Dict, Any, Optional

app = modal.App("mp4totext-ffmpeg")

# FFmpeg image - CPU optimized, lightweight
ffmpeg_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(
        "ffmpeg",
        "libavcodec-extra",  # Extra codecs
        "libavformat-dev",
        "libavutil-dev"
    )
    .pip_install(
        "requests",
        "pillow",  # Image processing
    )
)


@app.cls(
    cpu=2.0,  # 2 CPU cores (FFmpeg multi-threaded)
    image=ffmpeg_image,
    timeout=1800,  # 30 min timeout
    allow_concurrent_inputs=100,  # High concurrency
)
class FFmpegService:
    """Remote FFmpeg processing service"""
    
    @modal.method()
    def create_video_segment(
        self,
        image_url: str,
        audio_url: str,
        audio_duration: Optional[float] = None
    ) -> bytes:
        """
        Create video segment from image + audio
        
        Args:
            image_url: URL of image (PNG/JPEG)
            audio_url: URL of audio file (MP3)
            audio_duration: Audio duration in seconds (optional)
            
        Returns:
            bytes: MP4 video data
        """
        import requests
        import subprocess
        import tempfile
        from pathlib import Path
        from PIL import Image
        
        print(f"📥 Downloading image and audio...")
        
        # Download image
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        
        # Download audio
        audio_response = requests.get(audio_url, timeout=60)
        audio_response.raise_for_status()
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save and resize image to 1920x1080
            img_path = temp_path / "image.png"
            img = Image.open(io.BytesIO(img_response.content))
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            img.save(img_path)
            
            # Save audio
            audio_path = temp_path / "audio.mp3"
            with open(audio_path, "wb") as f:
                f.write(audio_response.content)
            
            # Output video
            output_path = temp_path / "output.mp4"
            
            print(f"🎬 Creating video with FFmpeg...")
            
            # FFmpeg command - optimized for speed
            command = [
                "ffmpeg",
                "-y",  # Overwrite
                "-loop", "1",  # Loop image
                "-i", str(img_path),
                "-i", str(audio_path),
                "-c:v", "libx264",  # H.264 codec
                "-preset", "ultrafast",  # Fastest encoding
                "-tune", "stillimage",  # Optimized for still image
                "-crf", "28",  # Good quality/speed balance
                "-c:a", "aac",  # AAC audio
                "-b:a", "128k",  # Audio bitrate
                "-pix_fmt", "yuv420p",  # Compatibility
                "-shortest",  # Duration = audio length
                "-movflags", "+faststart",  # Web optimization
                str(output_path)
            ]
            
            # Run FFmpeg
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                print(f"❌ FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
            # Read output video
            with open(output_path, "rb") as f:
                video_data = f.read()
            
            print(f"✅ Video created: {len(video_data) / 1024 / 1024:.1f} MB")
            
            return video_data
    
    @modal.method()
    def concatenate_videos(
        self,
        video_urls: List[str]
    ) -> bytes:
        """
        Concatenate multiple video segments
        
        Args:
            video_urls: List of video URLs to concatenate
            
        Returns:
            bytes: Concatenated MP4 video
        """
        import requests
        import subprocess
        import tempfile
        from pathlib import Path
        
        print(f"📥 Downloading {len(video_urls)} video segments...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Download all videos
            video_paths = []
            for i, url in enumerate(video_urls):
                response = requests.get(url, timeout=120)
                response.raise_for_status()
                
                video_path = temp_path / f"segment_{i:03d}.mp4"
                with open(video_path, "wb") as f:
                    f.write(response.content)
                
                video_paths.append(video_path)
                print(f"  ✓ Downloaded segment {i+1}/{len(video_urls)}")
            
            # Create concat file
            concat_file = temp_path / "concat.txt"
            with open(concat_file, "w") as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # Output video
            output_path = temp_path / "final.mp4"
            
            print(f"🎬 Concatenating videos with FFmpeg...")
            
            # FFmpeg concat command
            command = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",  # Stream copy (no re-encoding)
                "-movflags", "+faststart",
                str(output_path)
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                print(f"❌ FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg concat failed: {result.stderr}")
            
            # Read final video
            with open(output_path, "rb") as f:
                video_data = f.read()
            
            print(f"✅ Final video: {len(video_data) / 1024 / 1024:.1f} MB")
            
            return video_data
    
    @modal.method()
    def extract_audio(
        self,
        video_url: str,
        output_format: str = "mp3"
    ) -> bytes:
        """
        Extract audio from video file
        
        Args:
            video_url: URL of video file
            output_format: Output format (mp3, wav, flac, etc.)
            
        Returns:
            bytes: Audio file data
        """
        import requests
        import subprocess
        import tempfile
        from pathlib import Path
        
        print(f"📥 Downloading video...")
        
        # Download video
        response = requests.get(video_url, timeout=120)
        response.raise_for_status()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save video
            video_path = temp_path / "input_video.mp4"
            with open(video_path, "wb") as f:
                f.write(response.content)
            
            # Output audio
            output_path = temp_path / f"audio.{output_format}"
            
            print(f"🎵 Extracting audio with FFmpeg...")
            
            # FFmpeg audio extraction
            command = [
                "ffmpeg",
                "-y",
                "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "libmp3lame" if output_format == "mp3" else "copy",
                "-q:a", "2",  # High quality
                str(output_path)
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                print(f"❌ FFmpeg error: {result.stderr}")
                raise RuntimeError(f"Audio extraction failed: {result.stderr}")
            
            # Read audio
            with open(output_path, "rb") as f:
                audio_data = f.read()
            
            print(f"✅ Audio extracted: {len(audio_data) / 1024 / 1024:.1f} MB")
            
            return audio_data
    
    @modal.method()
    def batch_create_videos(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[bytes]:
        """
        Batch process multiple video segments in parallel
        
        Args:
            segments: List of {image_url, audio_url, audio_duration}
            
        Returns:
            List of video bytes
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print(f"🚀 Processing {len(segments)} segments in parallel...")
        
        results = [None] * len(segments)
        
        def process_segment(idx, segment):
            video_data = self.create_video_segment(
                image_url=segment["image_url"],
                audio_url=segment["audio_url"],
                audio_duration=segment.get("audio_duration")
            )
            return idx, video_data
        
        # Process in parallel (Modal handles concurrency)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(process_segment, i, seg)
                for i, seg in enumerate(segments)
            ]
            
            for future in as_completed(futures):
                idx, video_data = future.result()
                results[idx] = video_data
                print(f"  ✓ Completed segment {idx+1}/{len(segments)}")
        
        print(f"✅ All {len(segments)} segments completed")
        
        return results


@app.local_entrypoint()
def test():
    """Test FFmpeg service"""
    
    # Test image and audio URLs  
    image_url = "https://picsum.photos/1920/1080"  # Random image
    audio_url = "https://upload.wikimedia.org/wikipedia/commons/4/46/1941_Roosevelt_speech_pearlharbor_p1.ogg"
    
    print("🧪 Testing Modal FFmpeg Service...")
    print(f"📸 Image: {image_url}")
    print(f"🎵 Audio: {audio_url}")
    
    # Create video segment
    ffmpeg = FFmpegService()
    video_data = ffmpeg.create_video_segment.remote(
        image_url=image_url,
        audio_url=audio_url
    )
    
    # Save test video
    import tempfile
    output_path = tempfile.gettempdir() + "/modal_ffmpeg_test.mp4"
    with open(output_path, "wb") as f:
        f.write(video_data)
    
    print(f"\n✅ Test successful!")
    print(f"📹 Video saved to: {output_path}")
    print(f"📊 Size: {len(video_data) / 1024 / 1024:.1f} MB")


# DEPLOYMENT INSTRUCTIONS
"""
1. Install Modal:
   pip install modal

2. Setup Modal account:
   modal setup

3. Deploy to Modal:
   modal deploy modal_ffmpeg_service.py

4. Test deployment:
   modal run modal_ffmpeg_service.py

5. Use in backend:
   
   from modal import Cls
   
   FFmpegService = Cls.from_name("mp4totext-ffmpeg", "FFmpegService")
   
   # Create video
   video_data = FFmpegService().create_video_segment.remote(
       image_url="https://...",
       audio_url="https://..."
   )
   
   # Concatenate videos
   final_video = FFmpegService().concatenate_videos.remote(
       video_urls=["https://...", "https://..."]
   )
   
   # Extract audio
   audio_data = FFmpegService().extract_audio.remote(
       video_url="https://..."
   )

PRICING COMPARISON:

Local FFmpeg (Current):
- Requires powerful server
- Memory: ~2GB per worker
- CPU: Heavy load during processing
- Not scalable

Modal FFmpeg (Recommended):
- Pay per use: $0.000025/second
- Auto-scaling: 0-100 concurrent processes
- No server management
- Cost example:
  * 100 segments x 15 seconds each = 1500 seconds
  * Cost: 1500 x $0.000025 = $0.0375 (4 cents!)
  
FREE TIER:
- 50 compute hours/month FREE
- More than enough for development
- ~12,000 video segments/month free
"""
