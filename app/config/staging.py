"""
Staging Configuration
Pre-production testing with moderate resources
"""

from .base import BaseConfig


class StagingConfig(BaseConfig):
    """Staging environment configuration"""
    
    DEBUG = False
    ENVIRONMENT = 'staging'
    
    # Staging-specific Celery settings
    CELERY_CONFIG = {
        **BaseConfig.CELERY_CONFIG,
        
        # Worker Settings (moderate scale)
        'worker_concurrency': 4,  # 4 concurrent workers
        'worker_pool': 'prefork',  # Multi-process pool
        
        # Autoscaling (dinamik worker sayısı)
        'worker_autoscale': (6, 2),  # Max 6, min 2 workers
        
        # Performance tuning
        'worker_prefetch_multiplier': 2,  # 2 task pre-fetch
        'worker_max_tasks_per_child': 100,  # 100 task sonra restart
        
        # Logging
        'worker_log_format': '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
        'worker_task_log_format': '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
    }
    
    # Resource limits (staging with 100 concurrent users)
    MAX_CONCURRENT_UPLOADS = 50
    MAX_CONCURRENT_TRANSCRIPTIONS = 20
    MAX_CONCURRENT_AI_TASKS = 10
    
    # Redis password required in staging
    REDIS_PASSWORD = None  # Set via environment variable
