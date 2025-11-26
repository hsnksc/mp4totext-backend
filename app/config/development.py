"""
Development Configuration
Local development with CONCURRENT USER TESTING support
"""

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    
    DEBUG = True
    ENVIRONMENT = 'development'
    
    # Development-specific Celery settings
    CELERY_CONFIG = {
        **BaseConfig.CELERY_CONFIG,
        
        # Worker Settings (CONCURRENT TESTING için optimize)
        'worker_concurrency': 4,  # 4 concurrent workers (2-3 kullanıcı için yeterli)
        'worker_pool': 'prefork',  # Multi-process pool (gerçek paralel işleme)
        
        # Prefetch ayarı (her worker 2 task önceden alır)
        'worker_prefetch_multiplier': 2,  # Her worker 2 task prefetch
        
        # Autoscaling (dinamik: min 2, max 4 worker)
        'worker_autoscale': (4, 2),  # Max 4, min 2 worker
        
        # Task restart (memory leak önleme)
        'worker_max_tasks_per_child': 20,  # 20 task sonra restart (dev için düşük)
        
        # Logging
        'worker_log_format': '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
        'worker_task_log_format': '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
        
        # Development optimizations
        'task_always_eager': False,  # False for real async behavior
        'task_eager_propagates': True,  # Errors propagate immediately
    }
    
    # Resource limits (local development - CONCURRENT TESTING)
    MAX_CONCURRENT_UPLOADS = 10  # Artırıldı: 10 eşzamanlı upload
    MAX_CONCURRENT_TRANSCRIPTIONS = 4  # Artırıldı: 4 eşzamanlı transcription
    MAX_CONCURRENT_AI_TASKS = 2  # Artırıldı: 2 eşzamanlı AI task
