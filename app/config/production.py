"""
Production Configuration
High-scale deployment for 1000+ concurrent users
"""

from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    
    DEBUG = False
    ENVIRONMENT = 'production'
    
    # Production-specific Celery settings
    CELERY_CONFIG = {
        **BaseConfig.CELERY_CONFIG,
        
        # Worker Settings (high scale)
        'worker_concurrency': 8,  # 8 concurrent workers per instance
        'worker_pool': 'prefork',  # Multi-process pool
        
        # Autoscaling (dinamik worker sayısı)
        'worker_autoscale': (12, 4),  # Max 12, min 4 workers
        
        # Performance tuning (production optimized)
        'worker_prefetch_multiplier': 4,  # 4 task pre-fetch (higher throughput)
        'worker_max_tasks_per_child': 1000,  # 1000 task sonra restart
        
        # Time limits (production values)
        'task_soft_time_limit': 3300,  # 55 minutes
        'task_time_limit': 3600,  # 60 minutes
        
        # Broker & Backend reliability
        'broker_connection_retry_on_startup': True,
        'broker_connection_retry': True,
        'broker_connection_max_retries': 30,  # More retries in production
        'broker_heartbeat': 30,  # Health check every 30s
        
        # Result backend
        'result_expires': 86400,  # 24 hours
        'result_compression': 'gzip',  # Compress results
        
        # Logging (structured for production)
        'worker_log_format': '%(asctime)s [%(levelname)s] [%(processName)s] %(message)s',
        'worker_task_log_format': '%(asctime)s [%(levelname)s] [%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    }
    
    # Resource limits (production with 1000+ concurrent users)
    MAX_CONCURRENT_UPLOADS = 500  # 500 simultaneous uploads
    MAX_CONCURRENT_TRANSCRIPTIONS = 200  # 200 transcriptions
    MAX_CONCURRENT_AI_TASKS = 100  # 100 AI enhancements
    
    # Redis password REQUIRED in production
    REDIS_PASSWORD = None  # MUST be set via environment variable
    
    # Security
    REDIS_SSL = True  # SSL for Redis in production
    
    # Monitoring (enabled in production)
    ENABLE_MONITORING = True
    ENABLE_METRICS = True
    ENABLE_HEALTH_CHECKS = True
