"""
Modal FFmpeg Adapter - Connects backend to Modal FFmpeg service
Replaces local FFmpeg with remote Modal processing
"""

import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class ModalFFmpegAdapter:
    """
    Adapter for Modal FFmpeg service
    
    Features:
    - Automatic fallback to local FFmpeg if Modal unavailable
    - Progress tracking
    - Error handling
    - Batch processing support
    """
    
    def __init__(self, use_modal: bool = True):
        """
        Initialize Modal FFmpeg adapter
        
        Args:
            use_modal: Use Modal service (True) or local FFmpeg (False)
        """
        self.use_modal = use_modal and os.getenv("MODAL_TOKEN_ID") is not None
        self.ffmpeg_service = None
        
        if self.use_modal:
            try:
                from modal import Cls
                self.ffmpeg_service = Cls.from_name("mp4totext-ffmpeg", "FFmpegService")
                logger.info("✅ Modal FFmpeg service connected")
            except Exception as e:
                logger.warning(f"⚠️ Modal FFmpeg not available, using local: {e}")
                self.use_modal = False
        
        if not self.use_modal:
            # Fallback to local FFmpeg
            from app.services.video_assembly import VideoAssemblyService
            self.local_service = VideoAssemblyService()
            logger.info("📍 Using local FFmpeg")
    
    def create_video_segment(
        self,
        image_url: str,
        audio_url: str,
        output_path: str,
        audio_duration: Optional[float] = None
    ) -> str:
        """
        Create video segment from image + audio
        
        Args:
            image_url: URL or local path to image
            audio_url: URL or local path to audio
            output_path: Output video path
            audio_duration: Audio duration (optional)
            
        Returns:
            Path to output video
        """
        if self.use_modal:
            logger.info("🌐 Processing with Modal FFmpeg...")
            
            # Call Modal service
            video_data = self.ffmpeg_service().create_video_segment.remote(
                image_url=image_url,
                audio_url=audio_url,
                audio_duration=audio_duration
            )
            
            # Save to output path
            with open(output_path, "wb") as f:
                f.write(video_data)
            
            logger.info(f"✅ Modal FFmpeg completed: {len(video_data)/1024/1024:.1f} MB")
            
        else:
            logger.info("💻 Processing with local FFmpeg...")
            
            # Read local files
            with open(self._convert_to_local_path(image_url), "rb") as f:
                image_bytes = f.read()
            
            with open(self._convert_to_local_path(audio_url), "rb") as f:
                audio_bytes = f.read()
            
            # Use local service
            self.local_service.create_video_from_image_and_audio(
                image_bytes=image_bytes,
                audio_bytes=audio_bytes,
                output_path=output_path,
                audio_duration=audio_duration
            )
            
            logger.info(f"✅ Local FFmpeg completed")
        
        return output_path
    
    def concatenate_videos(
        self,
        video_urls: List[str],
        output_path: str
    ) -> str:
        """
        Concatenate multiple video segments
        
        Args:
            video_urls: List of video URLs or local paths
            output_path: Output video path
            
        Returns:
            Path to concatenated video
        """
        if self.use_modal:
            logger.info(f"🌐 Concatenating {len(video_urls)} videos with Modal...")
            
            # Call Modal service
            video_data = self.ffmpeg_service().concatenate_videos.remote(
                video_urls=video_urls
            )
            
            # Save to output path
            with open(output_path, "wb") as f:
                f.write(video_data)
            
            logger.info(f"✅ Modal concatenation completed: {len(video_data)/1024/1024:.1f} MB")
            
        else:
            logger.info(f"💻 Concatenating {len(video_urls)} videos with local FFmpeg...")
            
            # Convert URLs to local paths
            local_paths = [self._convert_to_local_path(url) for url in video_urls]
            
            # Use local service
            self.local_service.concatenate_videos(
                video_paths=local_paths,
                output_path=output_path
            )
            
            logger.info(f"✅ Local concatenation completed")
        
        return output_path
    
    def extract_audio(
        self,
        video_url: str,
        output_path: str,
        output_format: str = "mp3"
    ) -> str:
        """
        Extract audio from video
        
        Args:
            video_url: URL or local path to video
            output_path: Output audio path
            output_format: Audio format (mp3, wav, etc.)
            
        Returns:
            Path to extracted audio
        """
        if self.use_modal:
            logger.info("🌐 Extracting audio with Modal...")
            
            # Call Modal service
            audio_data = self.ffmpeg_service().extract_audio.remote(
                video_url=video_url,
                output_format=output_format
            )
            
            # Save to output path
            with open(output_path, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"✅ Modal audio extraction completed: {len(audio_data)/1024/1024:.1f} MB")
            
        else:
            logger.info("💻 Extracting audio with local FFmpeg...")
            
            import subprocess
            
            video_path = self._convert_to_local_path(video_url)
            
            command = [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "libmp3lame" if output_format == "mp3" else "copy",
                "-q:a", "2",
                output_path
            ]
            
            subprocess.run(command, check=True, capture_output=True)
            
            logger.info(f"✅ Local audio extraction completed")
        
        return output_path
    
    def batch_create_videos(
        self,
        segments: List[Dict[str, Any]],
        output_dir: str
    ) -> List[str]:
        """
        Batch process multiple video segments
        
        Args:
            segments: List of {image_url, audio_url, audio_duration, output_filename}
            output_dir: Output directory for videos
            
        Returns:
            List of output video paths
        """
        if self.use_modal:
            logger.info(f"🌐 Batch processing {len(segments)} segments with Modal...")
            
            # Prepare segments for Modal
            modal_segments = [
                {
                    "image_url": seg["image_url"],
                    "audio_url": seg["audio_url"],
                    "audio_duration": seg.get("audio_duration")
                }
                for seg in segments
            ]
            
            # Call Modal batch processing
            video_data_list = self.ffmpeg_service().batch_create_videos.remote(
                segments=modal_segments
            )
            
            # Save all videos
            output_paths = []
            for i, (seg, video_data) in enumerate(zip(segments, video_data_list)):
                output_path = os.path.join(output_dir, seg["output_filename"])
                with open(output_path, "wb") as f:
                    f.write(video_data)
                output_paths.append(output_path)
                logger.info(f"  ✓ Saved segment {i+1}/{len(segments)}")
            
            logger.info(f"✅ Modal batch processing completed")
            
        else:
            logger.info(f"💻 Batch processing {len(segments)} segments with local FFmpeg...")
            
            # Process sequentially with local FFmpeg
            output_paths = []
            for i, seg in enumerate(segments):
                output_path = os.path.join(output_dir, seg["output_filename"])
                
                self.create_video_segment(
                    image_url=seg["image_url"],
                    audio_url=seg["audio_url"],
                    output_path=output_path,
                    audio_duration=seg.get("audio_duration")
                )
                
                output_paths.append(output_path)
                logger.info(f"  ✓ Completed segment {i+1}/{len(segments)}")
            
            logger.info(f"✅ Local batch processing completed")
        
        return output_paths
    
    def _convert_to_local_path(self, url_or_path: str) -> str:
        """Convert URL to local path (download if necessary)"""
        # If already a local path, return it
        if os.path.exists(url_or_path):
            return url_or_path
        
        # If URL, download it (for local FFmpeg mode)
        if url_or_path.startswith(("http://", "https://")):
            import requests
            import tempfile
            from pathlib import Path
            
            response = requests.get(url_or_path, timeout=120)
            response.raise_for_status()
            
            # Save to temp file
            ext = Path(url_or_path).suffix or ".tmp"
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(response.content)
            temp_file.close()
            
            return temp_file.name
        
        return url_or_path
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about current service"""
        return {
            "using_modal": self.use_modal,
            "service": "Modal FFmpeg" if self.use_modal else "Local FFmpeg",
            "modal_available": self.ffmpeg_service is not None,
            "modal_token_set": os.getenv("MODAL_TOKEN_ID") is not None
        }


# Convenience function
def get_ffmpeg_service(use_modal: bool = True) -> ModalFFmpegAdapter:
    """Get FFmpeg service (Modal or local)"""
    return ModalFFmpegAdapter(use_modal=use_modal)
