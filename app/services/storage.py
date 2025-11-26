"""
File storage service using MinIO (S3-compatible)
"""

import os
import uuid
import logging
from typing import Optional, BinaryIO
from pathlib import Path
from datetime import timedelta
from urllib3 import Retry
from minio import Minio
from minio.error import S3Error

from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileStorageService:
    """
    File storage service using local filesystem + MinIO for public URLs
    """
    
    def __init__(self, base_path: str = "./uploads"):
        # Local filesystem
        if not os.path.isabs(base_path):
            project_root = Path(__file__).parent.parent.parent
            self.base_path = project_root / base_path
        else:
            self.base_path = Path(base_path)
            
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ File storage initialized: {self.base_path.absolute()}")
        
        # MinIO client (optional for large files)
        try:
            # Configure retry strategy for ngrok stability
            retry = Retry(
                total=5,  # 5 attempts
                backoff_factor=0.5,  # 0.5s, 1s, 2s, 4s delays
                status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET", "PUT", "POST", "DELETE"]
            )
            
            # Create HTTP client with SSL verification disabled for self-signed certificates
            import urllib3
            http_client = urllib3.PoolManager(
                timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
                maxsize=10,
                cert_reqs='CERT_NONE',  # Disable SSL verification for self-signed certs
                retries=retry
            )
            
            # Suppress only the InsecureRequestWarning
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            self.minio_client = Minio(
                settings.STORAGE_ENDPOINT,
                access_key=settings.STORAGE_ACCESS_KEY,
                secret_key=settings.STORAGE_SECRET_KEY,
                secure=settings.STORAGE_SECURE,
                http_client=http_client  # Use custom client with SSL verification disabled
            )
            self.bucket_name = settings.STORAGE_BUCKET
            self.endpoint = settings.STORAGE_ENDPOINT  # ✅ Store endpoint for URL generation
            
            # Ensure bucket exists
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"📦 Created MinIO bucket: {self.bucket_name}")
            
            logger.info(f"✅ MinIO client initialized: {settings.STORAGE_ENDPOINT}/{self.bucket_name}")
            self.minio_enabled = True
        except Exception as e:
            logger.warning(f"⚠️ MinIO not available: {e}")
            self.minio_enabled = False
    
    def save_file(self, file: BinaryIO, filename: str) -> tuple[str, str]:
        """
        Save uploaded file to storage
        
        Args:
            file: File object
            filename: Original filename
            
        Returns:
            tuple: (file_id, file_path)
        """
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        stored_filename = f"{file_id}{ext}"
        
        # Create file path
        file_path = self.base_path / stored_filename
        
        # Save file
        try:
            with open(file_path, "wb") as f:
                content = file.read()
                f.write(content)
            
            logger.info(f"✅ File saved: {file_id} ({filename})")
            return file_id, str(file_path)
            
        except Exception as e:
            logger.error(f"❌ File save failed: {e}")
            raise
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """
        Get file path by file ID
        
        Args:
            file_id: File ID
            
        Returns:
            Path or None if not found
        """
        # Find file with this ID (any extension)
        for file_path in self.base_path.glob(f"{file_id}.*"):
            return file_path
        return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete file by file ID
        
        Args:
            file_id: File ID
            
        Returns:
            True if deleted, False if not found
        """
        file_path = self.get_file_path(file_id)
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"🗑️  File deleted: {file_id}")
            return True
        return False
    
    def get_file_size(self, file_id: str) -> Optional[int]:
        """
        Get file size in bytes
        
        Args:
            file_id: File ID
            
        Returns:
            File size or None if not found
        """
        file_path = self.get_file_path(file_id)
        if file_path and file_path.exists():
            return file_path.stat().st_size
        return None
    
    def upload_to_minio(self, file_path: str, object_name: str = None) -> Optional[str]:
        """
        Upload file to MinIO and return public URL
        
        Args:
            file_path: Local file path
            object_name: Object name in MinIO (defaults to basename)
            
        Returns:
            Public URL or None if upload failed
        """
        if not self.minio_enabled:
            logger.warning("⚠️ MinIO not enabled, cannot upload")
            return None
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            object_name = object_name or file_path.name
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # Upload file with larger part size for big files (10MB chunks)
            # This helps with ngrok stability on large uploads
            logger.info(f"📦 File size: {file_size_mb:.1f}MB, uploading to MinIO...")
            self.minio_client.fput_object(
                self.bucket_name,
                object_name,
                str(file_path),
                part_size=10*1024*1024  # 10MB chunks for better stability
            )
            
            # Get public URL (presigned for 1 hour)
            # ✅ Direct URL from Hostinger MinIO deployment
            internal_url = self.minio_client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(hours=1)  # 1 hour as timedelta
            )
            
            # For gistify.pro MinIO: URL is already public, no replacement needed!
            # MinIO generates: https://minio-wg8wok0k48soko0wsgk40www.gistify.pro/mp4totext/...
            logger.info(f"✅ Uploaded to MinIO: {object_name}")
            logger.info(f"🌐 Public URL: {internal_url[:80]}...")
            return internal_url
            
        except S3Error as e:
            logger.error(f"❌ MinIO upload failed: {e}")
            return None
    
    def upload_file_bytes(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """
        Upload file bytes directly to MinIO (for generated images)
        
        Args:
            file_bytes: File content as bytes
            filename: Object name in MinIO
            content_type: MIME type (e.g., 'image/png')
            
        Returns:
            Public URL or None if upload failed
        """
        if not self.minio_enabled:
            logger.warning("⚠️ MinIO not enabled, cannot upload")
            return None
        
        try:
            from io import BytesIO
            
            file_size_mb = len(file_bytes) / (1024 * 1024)
            logger.info(f"📦 Uploading {file_size_mb:.2f}MB to MinIO: {filename}")
            
            # Upload bytes directly
            self.minio_client.put_object(
                self.bucket_name,
                filename,
                BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type
            )
            
            # Get public URL
            internal_url = self.minio_client.presigned_get_object(
                self.bucket_name,
                filename,
                expires=timedelta(hours=1)
            )
            
            logger.info(f"✅ Uploaded bytes to MinIO: {filename}")
            return internal_url
            
        except S3Error as e:
            logger.error(f"❌ MinIO bytes upload failed: {e}")
            return None


# Singleton instance
_storage_service: Optional[FileStorageService] = None


def get_storage_service() -> FileStorageService:
    """
    Get storage service singleton
    
    Returns:
        FileStorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = FileStorageService()
    return _storage_service
