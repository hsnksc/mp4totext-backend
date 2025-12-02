"""
Production Configuration
High-scale deployment for 1000+ PDF/hour capacity
"""

from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """Production environment configuration for 1000 PDF/hour"""
    
    DEBUG = False
    ENVIRONMENT = 'production'
    
    # ==========================================================================
    # CELERY CONFIGURATION (Optimized for 1000 PDF/hour)
    # ==========================================================================
    # 
    # Calculation: 1000 PDF/hour = ~17 PDF/minute
    # Average PDF processing time: 50-60 seconds
    # Required concurrent workers: 17 * 1 = 17 minimum
    # With safety margin: 20-24 workers recommended
    #
    # Deployment Strategy:
    # - 3 Celery pods × 8 workers = 24 concurrent tasks
    # - Or 2 Celery pods × 12 workers = 24 concurrent tasks
    # ==========================================================================
    
    CELERY_CONFIG = {
        **BaseConfig.CELERY_CONFIG,
        
        # Worker Settings (1000 PDF/hour capacity)
        'worker_concurrency': 8,  # 8 concurrent workers per pod
        'worker_pool': 'prefork',  # Multi-process pool for CPU-bound tasks
        
        # Autoscaling (dynamic worker scaling)
        'worker_autoscale': (16, 4),  # Max 16, min 4 workers per pod
        
        # Performance tuning (high throughput)
        'worker_prefetch_multiplier': 2,  # 2 task pre-fetch (balance memory/throughput)
        'worker_max_tasks_per_child': 200,  # Restart after 200 tasks (prevent memory leaks)
        'worker_max_memory_per_child': 512000,  # 512MB memory limit per worker
        
        # Time limits (Vision API can be slow)
        'task_soft_time_limit': 300,  # 5 minutes soft limit
        'task_time_limit': 360,  # 6 minutes hard limit
        
        # Broker & Backend reliability
        'broker_connection_retry_on_startup': True,
        'broker_connection_retry': True,
        'broker_connection_max_retries': 50,
        'broker_heartbeat': 20,  # Health check every 20s
        'broker_pool_limit': 50,  # Connection pool size
        
        # Result backend
        'result_expires': 43200,  # 12 hours (save storage)
        'result_compression': 'gzip',
        
        # Task routing (priority queues)
        'task_routes': {
            'app.workers.transcription_worker.process_vision_task': {'queue': 'vision'},
            'app.workers.transcription_worker.process_transcription_task': {'queue': 'transcription'},
            'app.workers.transcription_worker.enhance_transcription_task': {'queue': 'enhancement'},
        },
        
        # Rate limiting (Gemini API: 60 req/min free tier, 1000 req/min paid)
        'task_annotations': {
            'app.workers.transcription_worker.process_vision_task': {
                'rate_limit': '50/m',  # 50 Vision tasks per minute
            },
        },
        
        # Logging (structured for production)
        'worker_log_format': '%(asctime)s [%(levelname)s] [%(processName)s] %(message)s',
        'worker_task_log_format': '%(asctime)s [%(levelname)s] [%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    }
    
    # ==========================================================================
    # RESOURCE LIMITS (1000 PDF/hour capacity)
    # ==========================================================================
    MAX_CONCURRENT_UPLOADS = 100  # 100 simultaneous uploads
    MAX_CONCURRENT_TRANSCRIPTIONS = 50  # 50 transcriptions at once
    MAX_CONCURRENT_VISION_TASKS = 50  # 50 Vision API calls at once
    MAX_CONCURRENT_AI_TASKS = 30  # 30 AI enhancements
    
    # Queue limits (prevent memory issues)
    MAX_QUEUE_SIZE = 5000  # Max 5000 tasks in queue
    
    # ==========================================================================
    # VISION API CONFIGURATION
    # ==========================================================================
    VISION_RATE_LIMIT = 50  # 50 requests per minute
    VISION_MAX_PAGES = 50  # Max 50 pages per PDF
    VISION_TIMEOUT = 120  # 2 minute timeout per page
    
    # ==========================================================================
    # REDIS CONFIGURATION
    # ==========================================================================
    REDIS_PASSWORD = None  # MUST be set via environment variable
    REDIS_SSL = False  # Set True if using managed Redis with SSL
    REDIS_MAX_CONNECTIONS = 100  # Connection pool size
    
    # ==========================================================================
    # MONITORING
    # ==========================================================================
    ENABLE_MONITORING = True
    ENABLE_METRICS = True
    ENABLE_HEALTH_CHECKS = True
