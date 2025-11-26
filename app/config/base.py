"""
Base Configuration for MP4toText Backend
Common settings across all environments
"""

import os
from kombu import Queue
from typing import Dict, Any


class BaseConfig:
    """Base configuration with common settings"""
    
    # =============================================================================
    # REDIS CONFIGURATION
    # =============================================================================
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    @property
    def REDIS_URL(self) -> str:
        """Build Redis URL with optional password"""
        if self.REDIS_PASSWORD:
            return f'redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'
        return f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}'
    
    # =============================================================================
    # CELERY CONFIGURATION
    # =============================================================================
    CELERY_CONFIG: Dict[str, Any] = {
        # Broker & Backend
        'broker_url': None,  # Will be set dynamically
        'result_backend': None,  # Will be set dynamically
        
        # Task Serialization (güvenlik için JSON zorunlu)
        'task_serializer': 'json',
        'accept_content': ['json'],
        'result_serializer': 'json',
        
        # Timezone
        'timezone': 'Europe/Istanbul',
        'enable_utc': True,
        
        # Queue Yapılandırması - Priority-based routing
        'task_queues': (
            Queue('critical', routing_key='critical', priority=10),  # Upload, file operations
            Queue('high', routing_key='high', priority=7),           # Transcription (Whisper)
            Queue('default', routing_key='default', priority=5),     # AI enhancement (Gemini/GPT)
            Queue('low', routing_key='low', priority=2),             # Cleanup, maintenance
        ),
        
        # Task Routing - Otomatik queue assignment
        'task_routes': {
            'app.workers.tasks.upload.*': {'queue': 'critical', 'routing_key': 'critical'},
            'app.workers.process_transcription': {'queue': 'high', 'routing_key': 'high'},
            'app.workers.tasks.ai_enhancement.*': {'queue': 'default', 'routing_key': 'default'},
            'app.workers.tasks.cleanup.*': {'queue': 'low', 'routing_key': 'low'},
        },
        
        # Performance Settings
        'worker_prefetch_multiplier': 1,  # Her seferde 1 task (ağır işlemler için)
        'worker_max_tasks_per_child': 50,  # 50 task sonra worker restart (memory leak önleme)
        'task_acks_late': True,  # Task bitince ACK (crash durumunda retry)
        'task_reject_on_worker_lost': True,  # Worker crash -> task başka worker'a
        
        # Retry Policy (default for all tasks)
        'task_default_retry_delay': 60,  # 60 saniye sonra retry
        'task_max_retries': 3,  # Maksimum 3 deneme
        
        # Time Limits (ağır işlemler için)
        'task_soft_time_limit': 3300,  # 55 dakika soft limit (warning)
        'task_time_limit': 3600,  # 60 dakika hard limit (kill)
        
        # Results
        'result_expires': 86400,  # 24 saat sonra result silinir
        'result_persistent': True,  # Result'lar disk'e yazılır
        'result_backend_transport_options': {
            'retry_policy': {
                'timeout': 5.0
            }
        },
        
        # Task Tracking
        'task_track_started': True,  # Task başlangıcı track edilir
        'task_send_sent_event': True,  # Task gönderildiğinde event
        
        # Connection Retry
        'broker_connection_retry_on_startup': True,
        'broker_connection_retry': True,
        'broker_connection_max_retries': 10,
    }
    
    def get_celery_config(self) -> Dict[str, Any]:
        """
        Get Celery config with dynamic Redis URLs
        
        Returns:
            Celery configuration dictionary
        """
        config = self.CELERY_CONFIG.copy()
        config['broker_url'] = self.REDIS_URL
        config['result_backend'] = f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{int(self.REDIS_DB) + 1}'
        return config
    
    # =============================================================================
    # MONITORING & HEALTH CHECKS
    # =============================================================================
    ENABLE_MONITORING = True
    FLOWER_PORT = 5555
    PROMETHEUS_PORT = 9090
    
    # =============================================================================
    # STORAGE & FILE HANDLING
    # =============================================================================
    MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB
    ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.mp4', '.avi', '.mov', '.mkv'}
    TEMP_UPLOAD_DIR = '/tmp/mp4totext_uploads'
