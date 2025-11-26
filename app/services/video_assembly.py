"""
Video Assembly Service - Combines images and audio into video using FFmpeg

OPTIMIZATIONS:
- FFmpeg ultrafast preset: 3x faster encoding (45s → 15s per segment)
- Parallel processing support via concurrent.futures
- Memory-efficient image handling
"""
import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import time
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)

# Check for Modal
try:
    import modal
    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False
    logger.warning("⚠️ Modal not installed, falling back to local FFmpeg")


class VideoAssemblyService:
    """Service for assembling images and audio into video"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "mp4totext_video"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize Modal connection
        self.modal_service = None
        if MODAL_AVAILABLE:
            try:
                # Lookup deployed service (Modal API: from_name instead of lookup)
                self.FFmpegService = modal.Cls.from_name("mp4totext-ffmpeg", "FFmpegService")
                self.modal_service = self.FFmpegService()
                logger.info("✅ Modal FFmpeg service connected")
            except Exception as e:
                logger.warning(f"⚠️ Modal connection failed: {e}")
    
    def check_ffmpeg_installed(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ FFmpeg not installed or not in PATH")
            return False
    
    def create_video_from_image_and_audio(
        self,
        image_bytes: bytes,
        audio_bytes: bytes,
        output_path: str,
        audio_duration: float = None
    ) -> str:
        """
        Create a video segment from a single image and audio file
        Uses Modal FFmpeg if available, falls back to local FFmpeg
        
        Args:
            image_bytes: Image data (PNG/JPEG)
            audio_bytes: Audio data (MP3)
            output_path: Output video file path
            audio_duration: Duration in seconds (calculated if None)
            
        Returns:
            Path to output video file
        """
        # Try Modal FFmpeg first for better performance
        if self.modal_service:
            try:
                return self._create_video_segment_modal(
                    image_bytes=image_bytes,
                    audio_bytes=audio_bytes,
                    output_path=output_path,
                    audio_duration=audio_duration
                )
            except Exception as e:
                logger.warning(f"⚠️ Modal FFmpeg failed, falling back to local: {e}")
        
        # Fallback to local FFmpeg
        return self._create_video_segment_local(
            image_bytes=image_bytes,
            audio_bytes=audio_bytes,
            output_path=output_path,
            audio_duration=audio_duration
        )
    
    def _create_video_segment_modal(
        self,
        image_bytes: bytes,
        audio_bytes: bytes,
        output_path: str,
        audio_duration: float = None
    ) -> str:
        """Create video segment using Modal FFmpeg (cloud processing)"""
        logger.info(f"☁️  Creating video segment on Modal...")
        storage = get_storage_service()
        
        # 1. Upload assets to MinIO
        img_name = f"temp_img_{int(os.urandom(4).hex(), 16)}.png"
        audio_name = f"temp_audio_{int(os.urandom(4).hex(), 16)}.mp3"
        
        # Resize image before upload
        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_bytes_resized = img_buffer.getvalue()
        
        img_url = storage.upload_file_bytes(img_bytes_resized, img_name, "image/png")
        audio_url = storage.upload_file_bytes(audio_bytes, audio_name, "audio/mpeg")
        
        logger.info(f"📤 Uploaded assets to MinIO: {img_name}, {audio_name}")
        
        # 2. Process on Modal
        video_bytes = self.modal_service.create_video_segment.remote(
            image_url=img_url,
            audio_url=audio_url,
            audio_duration=audio_duration
        )
        
        # 3. Save result
        with open(output_path, "wb") as f:
            f.write(video_bytes)
        
        logger.info(f"✅ Modal video segment created: {output_path} ({len(video_bytes)/1024/1024:.1f} MB)")
        return output_path
    
    def _create_video_segment_local(
        self,
        image_bytes: bytes,
        audio_bytes: bytes,
        output_path: str,
        audio_duration: float = None
    ) -> str:
        """Create video segment using local FFmpeg (fallback)"""
        try:
            # Save image temporarily
            img_path = self.temp_dir / f"temp_img_{int(os.urandom(4).hex(), 16)}.png"
            with open(img_path, "wb") as f:
                f.write(image_bytes)
            
            # Resize image to standard video resolution (1920x1080)
            img = Image.open(img_path)
            img = img.resize((1920, 1080), Image.Resampling.LANCZOS)
            img.save(img_path)
            
            # Save audio temporarily
            audio_path = self.temp_dir / f"temp_audio_{int(os.urandom(4).hex(), 16)}.mp3"
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            
            # Create video with FFmpeg
            # -loop 1: Loop the image
            # -i: Input image
            # -i: Input audio
            # -c:v libx264: H.264 video codec
            # -tune stillimage: Optimize for still image
            # -c:a aac: AAC audio codec
            # -b:a 192k: Audio bitrate
            # -pix_fmt yuv420p: Pixel format for compatibility
            # -shortest: Duration = audio duration
            
            command = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-loop", "1",
                "-i", str(img_path),
                "-i", str(audio_path),
                "-c:v", "libx264",
                "-preset", "ultrafast",  # OPTIMIZATION: 3x faster encoding
                "-tune", "stillimage",
                "-crf", "28",  # Slightly lower quality for speed
                "-c:a", "aac",
                "-b:a", "128k",  # Lower bitrate for speed
                "-ar", "44100",  # Sample rate
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",  # Web streaming optimization
                "-threads", "0",  # Use all CPU threads
                "-shortest",
                str(output_path)
            ]
            
            logger.info(f"🎬 Creating video segment locally: {output_path}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Cleanup temp files
            img_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
            
            logger.info(f"✅ Local video segment created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Local video creation failed: {e}")
            raise
    
    def _concatenate_videos_modal(self, video_paths: List[str], output_path: str) -> str:
        """Concatenate videos using Modal"""
        logger.info(f"🚀 Concatenating {len(video_paths)} videos on Modal...")
        storage = get_storage_service()
        
        # 1. Upload videos to MinIO
        video_urls = [None] * len(video_paths)
        
        def upload_video(idx, path):
            try:
                name = f"temp_seg_{int(os.urandom(4).hex(), 16)}.mp4"
                with open(path, "rb") as f:
                    content = f.read()
                url = storage.upload_file_bytes(content, name, "video/mp4")
                return idx, url
            except Exception as e:
                logger.error(f"Failed to upload video segment {idx}: {e}")
                return idx, None
            
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(upload_video, i, path) for i, path in enumerate(video_paths)]
            for future in as_completed(futures):
                idx, url = future.result()
                video_urls[idx] = url
            
        if not all(video_urls):
            raise RuntimeError("Failed to upload video segments")
            
        # 2. Process on Modal
        final_video_bytes = self.modal_service.concatenate_videos.remote(video_urls)
        
        # 3. Save result
        with open(output_path, "wb") as f:
            f.write(final_video_bytes)
            
        logger.info(f"✅ Modal concatenation complete: {output_path}")
        return output_path

    def concatenate_videos(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """
        Concatenate multiple video segments into one final video
        
        Args:
            video_paths: List of video file paths to concatenate
            output_path: Output final video path
            
        Returns:
            Path to final video
        """
        # Try Modal first
        if self.modal_service:
            try:
                return self._concatenate_videos_modal(video_paths, output_path)
            except Exception as e:
                logger.error(f"❌ Modal concatenation failed, falling back to local: {e}")
        
        try:
            if not video_paths:
                raise ValueError("No video segments to concatenate")
            
            if len(video_paths) == 1:
                # Only one segment, just copy it
                import shutil
                shutil.copy(video_paths[0], output_path)
                return output_path
            
            # Create concat list file
            concat_file = self.temp_dir / f"concat_{int(os.urandom(4).hex(), 16)}.txt"
            with open(concat_file, "w") as f:
                for video_path in video_paths:
                    # FFmpeg concat format
                    f.write(f"file '{os.path.abspath(video_path)}'\n")
            
            # Concatenate with FFmpeg
            command = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",  # Copy without re-encoding
                str(output_path)
            ]
            
            logger.info(f"🎬 Concatenating {len(video_paths)} video segments")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Cleanup
            concat_file.unlink(missing_ok=True)
            
            logger.info(f"✅ Final video created: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Video concatenation failed: {e}")
            raise
    
    def get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe"""
        try:
            command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            
            duration = float(result.stdout.strip())
            return duration
            
        except Exception as e:
            logger.error(f"❌ Failed to get video duration: {e}")
            return 0.0
    
    def _create_video_segment_batch_modal(self, segments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process segments using Modal (Serverless GPU/CPU)"""
        logger.info(f"🚀 Offloading {len(segments_data)} segments to Modal...")
        start_time = time.time()
        storage = get_storage_service()
        
        # 1. Upload assets to MinIO in parallel
        logger.info("📤 Uploading assets to MinIO...")
        upload_start = time.time()
        
        uploads = [None] * len(segments_data)
        
        def upload_assets(idx, seg_data):
            try:
                # Upload image
                img_name = f"temp_img_{int(os.urandom(4).hex(), 16)}.png"
                img_url = storage.upload_file_bytes(seg_data["image_bytes"], img_name, "image/png")
                
                # Upload audio
                audio_name = f"temp_audio_{int(os.urandom(4).hex(), 16)}.mp3"
                audio_url = storage.upload_file_bytes(seg_data["audio_bytes"], audio_name, "audio/mpeg")
                
                return idx, img_url, audio_url
            except Exception as e:
                logger.error(f"Upload failed for segment {idx}: {e}")
                return idx, None, None
            
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(upload_assets, i, data) for i, data in enumerate(segments_data)]
            for future in as_completed(futures):
                idx, img_url, audio_url = future.result()
                uploads[idx] = (img_url, audio_url)
        
        # Check uploads
        image_urls = []
        audio_urls = []
        for i, upload in enumerate(uploads):
            if not upload or not upload[0] or not upload[1]:
                raise RuntimeError(f"Failed to upload assets for segment {i}")
            image_urls.append(upload[0])
            audio_urls.append(upload[1])
            
        logger.info(f"✅ Upload complete in {time.time() - upload_start:.1f}s")
        
        # 2. Process in Modal (Parallel)
        logger.info("☁️  Processing in Modal...")
        process_start = time.time()
        
        # Use .map() for parallel execution
        # Note: map returns a generator, convert to list to execute
        video_results = list(self.modal_service.create_video_segment.map(image_urls, audio_urls))
        
        logger.info(f"✅ Modal processing complete in {time.time() - process_start:.1f}s")
        
        # 3. Save results
        results = []
        for i, video_bytes in enumerate(video_results):
            seg_data = segments_data[i]
            output_path = seg_data["output_path"]
            
            with open(output_path, "wb") as f:
                f.write(video_bytes)
                
            # Get duration
            duration = self.get_video_duration(output_path)
            
            results.append({
                "status": "success",
                "segment_num": seg_data.get("segment_num", 0),
                "output_path": output_path,
                "duration": duration,
                "processing_time": time.time() - process_start,
                "text": seg_data.get("text", "")
            })
            
        total_time = time.time() - start_time
        logger.info(f"✅ Modal batch complete: {len(results)} segments in {total_time:.1f}s")
        return results

    def create_video_segment_batch(
        self,
        segments_data: List[Dict[str, Any]],
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Create multiple video segments in parallel (OPTIMIZATION)
        
        Args:
            segments_data: List of dicts with keys:
                - image_bytes: Image data
                - audio_bytes: Audio data
                - output_path: Output video path
                - segment_num: Segment number
                - text: Segment text
            max_workers: Max parallel workers (default 4)
        
        Returns:
            List of results with status, duration, path
        """
        # Try Modal first if available
        logger.info(f"🔍 Modal service check: {self.modal_service is not None}")
        if self.modal_service:
            try:
                logger.info("☁️ Attempting Modal processing...")
                return self._create_video_segment_batch_modal(segments_data)
            except Exception as e:
                logger.error(f"❌ Modal processing failed, falling back to local: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Fall through to local processing
        else:
            logger.warning("⚠️ Modal service not available, using local FFmpeg")
        
        logger.info(f"🚀 Creating {len(segments_data)} video segments in parallel (max_workers={max_workers})...")
        
        start_time = time.time()
        results = []
        
        def process_single_segment(seg_data: Dict[str, Any]) -> Dict[str, Any]:
            """Process single segment (runs in thread)"""
            seg_num = seg_data.get("segment_num", 0)
            try:
                segment_start = time.time()
                
                # Create video segment
                self.create_video_from_image_and_audio(
                    image_bytes=seg_data["image_bytes"],
                    audio_bytes=seg_data["audio_bytes"],
                    output_path=seg_data["output_path"]
                )
                
                # Get duration
                duration = self.get_video_duration(seg_data["output_path"])
                
                processing_time = time.time() - segment_start
                
                logger.info(f"✅ Segment {seg_num} completed in {processing_time:.1f}s (duration: {duration:.1f}s)")
                
                return {
                    "status": "success",
                    "segment_num": seg_num,
                    "output_path": seg_data["output_path"],
                    "duration": duration,
                    "processing_time": processing_time,
                    "text": seg_data.get("text", "")
                }
                
            except Exception as e:
                logger.error(f"❌ Segment {seg_num} failed: {e}")
                return {
                    "status": "error",
                    "segment_num": seg_num,
                    "error": str(e),
                    "text": seg_data.get("text", "")
                }
        
        # Execute in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_segment = {
                executor.submit(process_single_segment, seg_data): seg_data 
                for seg_data in segments_data
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_segment):
                result = future.result()
                results.append(result)
        
        # Sort by segment_num to maintain order
        results.sort(key=lambda x: x.get("segment_num", 0))
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results if r["status"] == "success")
        
        logger.info(
            f"✅ Parallel video creation complete: "
            f"{successful}/{len(segments_data)} successful in {total_time:.1f}s "
            f"(avg {total_time/len(segments_data):.1f}s per segment)"
        )
        
        return results


# Global instance
_video_assembly_service = None


def get_video_assembly_service() -> VideoAssemblyService:
    """Get or create video assembly service instance"""
    global _video_assembly_service
    if _video_assembly_service is None:
        _video_assembly_service = VideoAssemblyService()
    return _video_assembly_service
