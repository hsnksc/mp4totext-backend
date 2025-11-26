"""
CRITICAL PRIORITY TASKS
Queue: critical (priority=10)
For: File uploads, real-time operations, user-blocking tasks
"""

from celery import Task
from celery.utils.log import get_task_logger
from app.celery_config import celery_app

logger = get_task_logger(__name__)


class CriticalTask(Task):
    """Base task for critical operations"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 5}  # More retries for critical tasks
    retry_backoff = True
    retry_backoff_max = 300  # 5 minutes max
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=CriticalTask,
    queue='critical',
    routing_key='critical',
    name='app.workers.tasks.upload.validate_file'
)
def validate_file_task(self, file_id: int, file_path: str):
    """
    Validate uploaded file
    - Critical priority: user waits for this
    """
    try:
        logger.info(f"🔍 Validating file: {file_id}")
        
        # File validation logic here
        # - Check file size
        # - Verify file type
        # - Scan for viruses (optional)
        # - Move to permanent storage
        
        return {
            "status": "success",
            "file_id": file_id,
            "valid": True
        }
        
    except Exception as exc:
        logger.error(f"❌ File validation failed: {file_id} - {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    bind=True,
    base=CriticalTask,
    queue='critical',
    routing_key='critical',
    name='app.workers.tasks.upload.store_file'
)
def store_file_task(self, file_id: int, file_path: str, user_id: int):
    """
    Store file to MinIO/S3
    - Critical priority: blocks transcription
    """
    try:
        logger.info(f"☁️ Storing file: {file_id}")
        
        # Storage logic here
        # - Upload to MinIO/S3
        # - Generate secure URL
        # - Update database with storage URL
        
        return {
            "status": "success",
            "file_id": file_id,
            "storage_url": f"s3://bucket/{file_id}"
        }
        
    except Exception as exc:
        logger.error(f"❌ File storage failed: {file_id} - {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    queue='critical',
    routing_key='critical',
    priority=10,
    name='app.workers.tasks.upload.send_realtime_notification'
)
def send_realtime_notification(user_id: int, message: str, notification_type: str):
    """
    Send real-time notification to user (WebSocket)
    - Critical priority: immediate user feedback
    """
    logger.info(f"📢 Sending notification to user {user_id}: {notification_type}")
    
    # WebSocket notification logic
    # - Send via websocket manager
    # - Push notification to mobile
    
    return {"status": "sent", "user_id": user_id}
