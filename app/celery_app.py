"""
Celery application instance
"""

from app.celery_config import get_celery_app

# Create Celery app instance
celery_app = get_celery_app()

# Export for Celery worker
app = celery_app
