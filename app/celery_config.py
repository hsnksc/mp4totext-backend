"""
Celery configuration and application instance
Updated with environment-based configuration (dev/staging/prod)
"""

from dotenv import load_dotenv
load_dotenv()

from celery import Celery
from app.settings import get_settings

# Import new config system
try:
    from app.config import get_config
    USE_NEW_CONFIG = True
except ImportError:
    USE_NEW_CONFIG = False
    print("Warning: New config system not available, using legacy config")


def get_celery_app():
    """
    Get Celery app with environment-based configuration
    
    Returns:
        Configured Celery application instance
    """
    if USE_NEW_CONFIG:
        # NEW: Environment-based configuration
        config = get_config()
        celery_config = config.get_celery_config()
        
        # Create Celery app with new config
        celery_app = Celery(
            "mp4totext",
            broker=celery_config['broker_url'],
            backend=celery_config['result_backend'],
            include=["app.workers.transcription_worker"]
        )
        
        # Apply full configuration
        celery_app.conf.update(celery_config)
        
        print(f"✅ Celery configured for {config.ENVIRONMENT} environment")
        print(f"📊 Worker concurrency: {celery_config.get('worker_concurrency', 'auto')}")
        print(f"🔄 Autoscale: {celery_config.get('worker_autoscale', 'disabled')}")
        
    else:
        # LEGACY: Original configuration (fallback)
        settings = get_settings()
        
        celery_app = Celery(
            "mp4totext",
            broker=settings.CELERY_BROKER_URL,
            backend=settings.CELERY_RESULT_BACKEND,
            include=["app.workers.transcription_worker"]
        )
        
        # Legacy configuration
        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,
            task_soft_time_limit=3300,
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=50,
            broker_connection_retry_on_startup=True,
        )
        
        celery_app.conf.result_backend_transport_options = {
            'retry_policy': {
                'timeout': 5.0
            }
        }
        
        print("⚠️ Using legacy Celery configuration")
    
    return celery_app


# Create app instance
celery_app = get_celery_app()
