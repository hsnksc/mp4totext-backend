"""
File storage service using Cloudflare R2 (S3-compatible)
Supports both MinIO and Cloudflare R2
"""

import os
import uuid
import logging
from typing import Optional, BinaryIO
from pathlib import Path
from datetime import timedelta
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FileStorageService:
    """
    File storage service using local filesystem + Cloudflare R2 for public URLs
    """
    
    def __init__(self, base_path: str = "./uploads"):
        # Local filesystem for temporary files
        if not os.path.isabs(base_path):
            project_root = Path(__file__).parent.parent.parent
            self.base_path = project_root / base_path
        else:
            self.base_path = Path(base_path)
            
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ File storage initialized: {self.base_path.absolute()}")
        
        # Cloudflare R2 client (S3-compatible)
        try:
            self.bucket_name = settings.STORAGE_BUCKET
            self.account_id = settings.STORAGE_ACCOUNT_ID
            self.public_url_base = settings.STORAGE_PUBLIC_URL  # e.g., https://pub-xxx.r2.dev
            
            # R2 endpoint format: https://<account_id>.r2.cloudflarestorage.com
            endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
            
            # Configure boto3 for R2
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=settings.STORAGE_ACCESS_KEY,
                aws_secret_access_key=settings.STORAGE_SECRET_KEY,
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3, 'mode': 'adaptive'}
                ),
                region_name='auto'  # R2 uses 'auto' region
            )
            
            # Verify bucket exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                logger.info(f"✅ R2 bucket verified: {self.bucket_name}")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == '404':
                    # Create bucket if not exists
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"📦 Created R2 bucket: {self.bucket_name}")
                else:
                    raise
            
            logger.info(f"✅ Cloudflare R2 client initialized: {endpoint_url}/{self.bucket_name}")
            self.r2_enabled = True
            self.minio_enabled = True  # For backwards compatibility
            
        except Exception as e:
            logger.warning(f"⚠️ Cloudflare R2 not available: {e}")
            self.r2_enabled = False
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
    
    def get_public_url(self, filename: str) -> str:
        """
        Get public URL for a file in R2
        Uses presigned URL with 7 day expiry (R2 max) for reliability
        
        Args:
            filename: Object name in R2
            
        Returns:
            Public URL or presigned URL
        """
        if self.public_url_base:
            # Try public URL first
            public_url = f"{self.public_url_base}/{filename}"
            return public_url
        else:
            # Use presigned URL with 7 day expiry (max for R2)
            return self.get_presigned_url(filename, expires_in=604800)  # 7 days
    
    def get_presigned_url(self, filename: str, expires_in: int = 604800) -> str:
        """
        Get presigned URL for a file in R2
        R2 supports up to 7 days (604800 seconds) expiry
        
        Args:
            filename: Object name in R2
            expires_in: Expiration time in seconds (default 7 days)
            
        Returns:
            Presigned URL
        """
        if not self.r2_enabled:
            return ""
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': filename},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return ""
    
    def upload_to_minio(self, file_path: str, object_name: str = None) -> Optional[str]:
        """
        Upload file to R2 and return public URL
        (Named for backwards compatibility with MinIO)
        
        Args:
            file_path: Local file path
            object_name: Object name in R2 (defaults to basename)
            
        Returns:
            Public URL or None if upload failed
        """
        return self.upload_to_r2(file_path, object_name)
    
    def upload_to_r2(self, file_path: str, object_name: str = None) -> Optional[str]:
        """
        Upload file to Cloudflare R2 and return public URL
        
        Args:
            file_path: Local file path
            object_name: Object name in R2 (defaults to basename)
            
        Returns:
            Public URL or None if upload failed
        """
        if not self.r2_enabled:
            logger.warning("⚠️ R2 not enabled, cannot upload")
            return None
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            object_name = object_name or file_path.name
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # Determine content type
            content_type = self._get_content_type(object_name)
            
            logger.info(f"📦 Uploading {file_size_mb:.1f}MB to R2: {object_name}")
            
            # Upload file
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                object_name,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Get public URL (no expiration for public buckets!)
            public_url = self.get_public_url(object_name)
            
            logger.info(f"✅ Uploaded to R2: {object_name}")
            logger.info(f"🌐 Public URL: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"❌ R2 upload failed: {e}")
            return None
    
    def upload_file_bytes(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> Optional[str]:
        """
        Upload file bytes directly to R2 (for generated images)
        
        Args:
            file_bytes: File content as bytes
            filename: Object name in R2
            content_type: MIME type (e.g., 'image/png')
            
        Returns:
            Public URL or None if upload failed
        """
        if not self.r2_enabled:
            logger.warning("⚠️ R2 not enabled, cannot upload")
            return None
        
        try:
            from io import BytesIO
            
            file_size_mb = len(file_bytes) / (1024 * 1024)
            logger.info(f"📦 Uploading {file_size_mb:.2f}MB to R2: {filename}")
            
            # Upload bytes directly
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file_bytes,
                ContentType=content_type
            )
            
            # Get public URL (permanent, no expiration!)
            public_url = self.get_public_url(filename)
            
            logger.info(f"✅ Uploaded bytes to R2: {filename}")
            return public_url
            
        except Exception as e:
            logger.error(f"❌ R2 bytes upload failed: {e}")
            return None
    
    def delete_from_r2(self, filename: str) -> bool:
        """
        Delete file from R2
        
        Args:
            filename: Object name in R2
            
        Returns:
            True if deleted, False if failed
        """
        if not self.r2_enabled:
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=filename)
            logger.info(f"🗑️ Deleted from R2: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ R2 delete failed: {e}")
            return False
    
    def _get_content_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.txt': 'text/plain',
        }
        return content_types.get(ext, 'application/octet-stream')


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
