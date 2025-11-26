"""
Modal Client Service
Handles communication with Modal workers
"""

import logging
import os
from typing import Dict, Any, Optional
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Check if Modal is available
MODAL_AVAILABLE = False
try:
    import modal
    MODAL_AVAILABLE = True
    logger.info("✅ Modal SDK available")
except ImportError:
    logger.warning("⚠️ Modal SDK not available. Install with: pip install modal")


class ModalClient:
    """Client for submitting jobs to Modal workers"""
    
    def __init__(self):
        self.modal_available = MODAL_AVAILABLE
        self.app_name = "mp4totext-worker"
        
        if not self.modal_available:
            logger.warning("Modal client initialized but Modal SDK not available")
            return
        
        try:
            # Load the Modal app
            from modal import Stub
            self.stub = modal.Stub.from_name(self.app_name)
            logger.info(f"✅ Connected to Modal app: {self.app_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Modal app: {e}")
            self.modal_available = False
    
    def submit_transcription_job(
        self,
        transcription_id: int,
        user_id: int,
        file_url: str,
        language: str,
        config: Dict[str, Any]
    ) -> Optional[str]:
        """
        Submit a transcription job to Modal
        
        Args:
            transcription_id: Database ID of transcription
            user_id: User ID for credit tracking
            file_url: URL to download the audio/video file
            language: Target language code
            config: Configuration dict
            
        Returns:
            Job ID if successful, None otherwise
        """
        if not self.modal_available:
            logger.error("Cannot submit job: Modal not available")
            return None
        
        try:
            # Import the function
            from modal_worker import process_transcription_modal
            
            # Submit async job
            logger.info(f"📤 Submitting transcription #{transcription_id} to Modal...")
            
            call = process_transcription_modal.spawn(
                transcription_id=transcription_id,
                user_id=user_id,
                file_url=file_url,
                language=language,
                config=config
            )
            
            job_id = call.object_id
            logger.info(f"✅ Job submitted to Modal with ID: {job_id}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to submit Modal job: {e}", exc_info=True)
            return None
    
    def check_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Check status of a Modal job
        
        Args:
            job_id: Modal job ID
            
        Returns:
            Job status dict or None
        """
        if not self.modal_available:
            return None
        
        try:
            # Get function call
            call = modal.FunctionCall.from_id(job_id)
            
            # Check if complete
            try:
                result = call.get(timeout=0)  # Non-blocking check
                return {
                    "status": "completed",
                    "result": result
                }
            except TimeoutError:
                return {
                    "status": "processing"
                }
                
        except Exception as e:
            logger.error(f"❌ Error checking job status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def wait_for_job(self, job_id: str, timeout: int = 3600) -> Optional[Dict[str, Any]]:
        """
        Wait for a Modal job to complete
        
        Args:
            job_id: Modal job ID
            timeout: Max wait time in seconds
            
        Returns:
            Job result or None
        """
        if not self.modal_available:
            return None
        
        try:
            call = modal.FunctionCall.from_id(job_id)
            result = call.get(timeout=timeout)
            return result
        except Exception as e:
            logger.error(f"❌ Error waiting for job: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running Modal job
        
        Args:
            job_id: Modal job ID
            
        Returns:
            True if canceled successfully
        """
        if not self.modal_available:
            return False
        
        try:
            call = modal.FunctionCall.from_id(job_id)
            call.cancel()
            logger.info(f"✅ Canceled Modal job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error canceling job: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Modal is available"""
        return self.modal_available


# Singleton instance
_modal_client: Optional[ModalClient] = None


def get_modal_client() -> ModalClient:
    """Get Modal client singleton"""
    global _modal_client
    if _modal_client is None:
        _modal_client = ModalClient()
    return _modal_client
