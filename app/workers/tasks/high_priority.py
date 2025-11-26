"""
HIGH PRIORITY TASKS
Queue: high (priority=7)
For: Transcription processing (Whisper), speaker recognition
"""

from celery import Task
from celery.utils.log import get_task_logger
from app.celery_config import celery_app

logger = get_task_logger(__name__)


class HighPriorityTask(Task):
    """Base task for high priority operations"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=HighPriorityTask,
    queue='high',
    routing_key='high',
    name='app.workers.process_transcription',
    soft_time_limit=3300,  # 55 minutes
    time_limit=3600  # 60 minutes
)
def process_transcription(self, transcription_id: int, user_id: int):
    """
    Process transcription with Whisper
    - High priority: core business logic
    - Time-consuming: 5-30 minutes depending on file
    
    This is the MAIN transcription task (imported from transcription_worker.py)
    """
    # Import the actual transcription logic
    from app.workers.transcription_worker import process_transcription_task
    
    try:
        logger.info(f"🎙️ Starting transcription: {transcription_id}")
        
        # Call the actual transcription logic
        result = process_transcription_task(self, transcription_id)
        
        logger.info(f"✅ Transcription completed: {transcription_id}")
        return result
        
    except Exception as exc:
        logger.error(f"❌ Transcription failed: {transcription_id} - {exc}")
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(
    bind=True,
    base=HighPriorityTask,
    queue='high',
    routing_key='high',
    name='app.workers.tasks.high_priority.speaker_recognition'
)
def speaker_recognition_task(self, transcription_id: int, audio_file: str):
    """
    Perform speaker recognition/diarization
    - High priority: important for transcription quality
    """
    try:
        logger.info(f"👥 Speaker recognition: {transcription_id}")
        
        # Speaker recognition logic
        # - Load audio file
        # - Run diarization model
        # - Assign speakers to segments
        
        return {
            "status": "success",
            "transcription_id": transcription_id,
            "speakers": []
        }
        
    except Exception as exc:
        logger.error(f"❌ Speaker recognition failed: {transcription_id} - {exc}")
        raise self.retry(exc=exc, countdown=120)
