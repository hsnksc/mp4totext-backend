"""
Start Celery worker
"""

import os
import sys

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    from celery import Celery
    from celery.bin import worker
    
    # Import celery app
    from app.celery_config import celery_app
    
    print("""
    ============================================
        MP4toText Celery Worker
    ============================================
    
    Starting worker...
    Queue: default
    Concurrency: 2
    """)
    
    # Start worker
    worker_instance = worker.worker(app=celery_app)
    
    options = {
        'loglevel': 'INFO',
        'traceback': True,
        'concurrency': 2,  # 2 concurrent workers
        'pool': 'solo',  # Use solo pool for Windows
    }
    
    worker_instance.run(**options)
