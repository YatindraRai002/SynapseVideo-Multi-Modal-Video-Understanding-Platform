"""
Celery application configuration for SynapseVideo.
Handles background video processing tasks.
"""

from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "SynapseVideo",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,  # Process one video at a time per worker
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks to free memory
)

# Import tasks
from app.workers.tasks import process_video_task

__all__ = ['celery_app', 'process_video_task']
