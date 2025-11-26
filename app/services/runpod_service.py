"""
RunPod Serverless API Integration
Handles Whisper transcription via RunPod serverless endpoints
"""

import logging
import time
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RunPodService:
    """RunPod Serverless Whisper Transcription Service"""
    
    def __init__(self):
        self.api_key = settings.RUNPOD_API_KEY
        self.endpoint_id = settings.RUNPOD_ENDPOINT_ID
        self.timeout = settings.RUNPOD_TIMEOUT
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        
        if not self.api_key or not self.endpoint_id:
            raise ValueError("RunPod API key and endpoint ID are required")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def transcribe_audio(
        self,
        audio_path: str = None,
        audio_url: str = None,
        language: Optional[str] = None,
        model: str = "large-v3",
        task: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using RunPod Whisper endpoint
        
        Args:
            audio_path: Path to audio file (alternative to audio_url)
            audio_url: Public URL to audio file (preferred for large files)
            language: Language code (e.g., 'tr', 'en', None for auto-detect)
            model: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            task: 'transcribe' or 'translate'
            
        Returns:
            Transcription result dictionary with text and segments
        """
        try:
            if not audio_path and not audio_url:
                raise ValueError("Either audio_path or audio_url must be provided")
            
            # Prepare input payload
            input_payload = {}
            
            if audio_url:
                # Use URL (preferred for large files)
                logger.info(f"🚀 RunPod transcription started with URL: {audio_url}")
                input_payload["audio_url"] = audio_url
            else:
                # Use base64 (for small files <10MB)
                logger.info(f"🚀 RunPod transcription started for: {audio_path}")
                
                audio_file = Path(audio_path)
                if not audio_file.exists():
                    raise FileNotFoundError(f"Audio file not found: {audio_path}")
                
                file_size_mb = audio_file.stat().st_size / (1024 * 1024)
                
                if file_size_mb > 10:
                    raise ValueError(
                        f"Audio file too large for base64: {file_size_mb:.1f}MB. "
                        f"Maximum supported: 10MB. "
                        f"Use audio_url parameter or switch to Local transcription."
                    )
                
                audio_base64 = self._read_audio_as_base64(audio_path)
                logger.info(f"📦 Audio base64 length: {len(audio_base64)} chars (~{file_size_mb:.1f}MB)")
                input_payload["audio_base64"] = audio_base64
            
            # Add optional parameters only if needed
            if language:
                input_payload["language"] = language
            
            if model != "base":
                input_payload["model"] = model
            
            if task != "transcribe":
                input_payload["translate"] = True
            
            logger.info(f"📋 Payload keys: {list(input_payload.keys())}")
            
            input_data = {"input": input_payload}
            
            logger.info(f"📤 Sending to RunPod Faster-Whisper worker")
            logger.info(f"📤 Model: {model}, Language: {language}, Task: {task}")
            
            # Submit job to RunPod (async)
            logger.info("📤 Submitting job to RunPod endpoint...")
            job_response = self._submit_job(input_data)
            job_id = job_response.get("id")
            
            if not job_id:
                raise ValueError(f"Failed to get job ID from RunPod: {job_response}")
            
            logger.info(f"✅ Job submitted successfully: {job_id}")
            
            # Poll for results
            result = self._poll_job_status(job_id)
            
            # Extract transcription data
            transcription_data = self._parse_transcription_result(result)
            
            logger.info(f"✅ RunPod transcription completed for: {audio_path}")
            return transcription_data
            
        except Exception as e:
            logger.error(f"❌ RunPod transcription failed: {str(e)}")
            raise
    
    def _read_audio_as_base64(self, audio_path: str) -> str:
        """Read audio file and encode as base64"""
        import base64
        
        with open(audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        return audio_base64
    
    def _submit_job(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit job to RunPod - using async /run endpoint"""
        # Use /run for asynchronous execution (handles large files better)
        url = f"{self.base_url}/run"
        
        logger.info(f"📤 Sending request to: {url}")
        logger.info(f"📤 Payload keys: {input_data.keys()}")
        
        # input_data already contains the full payload
        response = requests.post(
            url,
            headers=self.headers,
            json=input_data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def _poll_job_status(self, job_id: str, max_wait: int = None) -> Dict[str, Any]:
        """
        Poll job status until completion
        
        Args:
            job_id: RunPod job ID
            max_wait: Maximum wait time in seconds (default: from settings)
            
        Returns:
            Job result dictionary
        """
        max_wait = max_wait or self.timeout
        url = f"{self.base_url}/status/{job_id}"
        
        start_time = time.time()
        poll_interval = 2  # Start with 2 seconds
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait:
                raise TimeoutError(f"RunPod job timed out after {max_wait} seconds")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            job_data = response.json()
            status = job_data.get("status")
            
            logger.info(f"📊 Job status: {status} (elapsed: {elapsed:.1f}s)")
            
            if status == "COMPLETED":
                logger.info(f"🔍 RunPod job_data: {job_data}")
                return job_data
            
            elif status == "FAILED":
                error = job_data.get("error", "Unknown error")
                raise RuntimeError(f"RunPod job failed: {error}")
            
            elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                # Exponential backoff with max 10 seconds
                time.sleep(min(poll_interval, 10))
                poll_interval = min(poll_interval * 1.5, 10)
            
            else:
                logger.warning(f"⚠️ Unknown job status: {status}")
                time.sleep(poll_interval)
    
    def _parse_transcription_result(self, job_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse RunPod job result into standardized transcription format
        
        Returns:
            {
                "text": "full transcription text",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 5.5,
                        "text": "segment text",
                        "speaker": None
                    },
                    ...
                ],
                "language": "tr",
                "duration": 120.5
            }
        """
        output = job_result.get("output", {})
        
        logger.info(f"🔍 RunPod output type: {type(output)}")
        logger.info(f"🔍 RunPod output keys: {output.keys() if isinstance(output, dict) else 'not a dict'}")
        
        if not output:
            logger.error(f"❌ Empty output from RunPod. Full job_result: {job_result}")
            raise ValueError("No output in RunPod job result")
        
        # Extract transcription data based on your worker's output format
        # This depends on how your RunPod worker returns the data
        
        # RunPod Faster-Whisper worker returns "transcription" not "text"
        full_text = output.get("transcription", output.get("text", ""))
        segments_data = output.get("segments", [])
        language = output.get("detected_language", output.get("language", "unknown"))
        
        # Convert segments to our format
        segments = []
        for i, seg in enumerate(segments_data):
            segments.append({
                "id": i,
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": seg.get("text", "").strip(),
                "speaker": None,  # Will be added by speaker recognition later
                "words": seg.get("words", [])
            })
        
        # Calculate duration from last segment
        duration = segments[-1]["end"] if segments else 0.0
        
        return {
            "text": full_text,
            "segments": segments,
            "language": language,
            "duration": duration,
            "provider": "runpod"
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check RunPod endpoint health"""
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            health_data = response.json()
            logger.info(f"✅ RunPod endpoint health: {health_data}")
            
            return {
                "status": "healthy",
                "data": health_data
            }
            
        except Exception as e:
            logger.error(f"❌ RunPod health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Singleton instance
_runpod_service: Optional[RunPodService] = None


def get_runpod_service() -> RunPodService:
    """Get or create RunPod service singleton"""
    global _runpod_service
    
    if _runpod_service is None:
        _runpod_service = RunPodService()
    
    return _runpod_service
