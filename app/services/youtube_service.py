"""
YouTube video downloader service
Downloads audio from YouTube videos using yt-dlp
"""

import os
import logging
import yt_dlp
from pathlib import Path
from typing import Optional, Dict, Any
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class YouTubeService:
    """Service for downloading YouTube videos"""
    
    def __init__(self):
        self.temp_dir = Path("temp_youtube")
        self.temp_dir.mkdir(exist_ok=True)
        
    def extract_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract video information without downloading
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video metadata (title, duration, thumbnail, etc.)
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': 30,  # Shorter timeout for info extraction
                'retries': 3,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date'),
                }
        except Exception as e:
            logger.error(f"❌ Failed to extract video info: {e}")
            raise ValueError(f"Invalid YouTube URL or video unavailable: {str(e)}")
    
    def download_audio(self, url: str, output_path: Optional[Path] = None) -> Path:
        """
        Download audio from YouTube video
        
        Args:
            url: YouTube video URL
            output_path: Optional custom output path
            
        Returns:
            Path to downloaded audio file
        """
        try:
            logger.info(f"🎬 Downloading audio from YouTube: {url}")
            
            # Generate output filename
            if output_path is None:
                output_path = self.temp_dir / "%(id)s.%(ext)s"
            
            # yt-dlp options for best audio quality
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_path),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': False,
                'no_warnings': False,
                'extract_audio': True,
                'audio_format': 'mp3',
                'audio_quality': 0,  # Best quality
                # Network reliability settings
                'socket_timeout': 60,  # Socket timeout (seconds)
                'retries': 10,  # Number of retries
                'fragment_retries': 10,  # Fragment retries
                'file_access_retries': 5,  # File access retries
                'extractor_retries': 5,  # Extractor retries
                'http_chunk_size': 10485760,  # 10MB chunks
                # Additional reliability options
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'prefer_free_formats': True,  # Prefer formats that don't require login
                'no_check_certificate': False,  # Verify SSL certificates
                'geo_bypass': True,  # Try to bypass geo-restriction
            }
            
            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info['id']
                
                # Find downloaded file
                downloaded_file = self.temp_dir / f"{video_id}.mp3"
                
                if not downloaded_file.exists():
                    # Try alternative patterns
                    for file in self.temp_dir.glob(f"{video_id}.*"):
                        if file.suffix in ['.mp3', '.m4a', '.webm']:
                            downloaded_file = file
                            break
                
                if not downloaded_file.exists():
                    raise FileNotFoundError(f"Downloaded file not found: {downloaded_file}")
                
                logger.info(f"✅ Audio downloaded successfully: {downloaded_file}")
                return downloaded_file
                
        except Exception as e:
            logger.error(f"❌ YouTube download failed: {e}", exc_info=True)
            raise ValueError(f"Failed to download YouTube video: {str(e)}")
    
    def cleanup_file(self, file_path: Path) -> None:
        """
        Delete temporary downloaded file
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if file_path and file_path.exists():
                os.remove(file_path)
                logger.info(f"🗑️ Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup file {file_path}: {e}")


# Singleton instance
_instance: Optional[YouTubeService] = None


def get_youtube_service() -> YouTubeService:
    """Get or create YouTubeService singleton instance"""
    global _instance
    if _instance is None:
        _instance = YouTubeService()
        logger.info("✅ YouTube service initialized")
    return _instance
