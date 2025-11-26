"""
Celery Task Monitoring & Health Checks
Real-time metrics and performance tracking for production
"""

import time
import logging
from typing import Dict, Any
from celery.signals import (
    task_prerun,
    task_postrun,
    task_failure,
    task_retry,
    task_revoked,
    worker_ready,
    worker_shutdown,
    before_task_publish,
    after_task_publish
)
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# =============================================================================
# TASK METRICS STORAGE
# =============================================================================
task_metrics: Dict[str, Dict[str, Any]] = {}
worker_metrics = {
    'tasks_completed': 0,
    'tasks_failed': 0,
    'tasks_retried': 0,
    'total_execution_time': 0,
    'worker_uptime_start': None
}


# =============================================================================
# TASK LIFECYCLE SIGNALS
# =============================================================================

@before_task_publish.connect
def task_before_publish(sender=None, headers=None, body=None, **kwargs):
    """Called before task is sent to broker"""
    task_id = headers.get('id') if headers else None
    task_name = headers.get('task') if headers else None
    
    logger.debug(f"📤 Task publishing: {task_name} [{task_id}]")


@after_task_publish.connect
def task_after_publish(sender=None, headers=None, body=None, **kwargs):
    """Called after task is sent to broker"""
    task_id = headers.get('id') if headers else None
    task_name = headers.get('task') if headers else None
    
    logger.debug(f"✅ Task published: {task_name} [{task_id}]")


@task_prerun.connect
def task_start_handler(sender=None, task_id=None, task=None, **kwargs):
    """
    Track task start time and initial metrics
    Called when task starts execution
    """
    queue = task.request.delivery_info.get('routing_key', 'unknown')
    
    task_metrics[task_id] = {
        'name': task.name,
        'queue': queue,
        'start_time': time.time(),
        'args': task.request.args,
        'kwargs': task.request.kwargs,
        'retries': task.request.retries or 0,
    }
    
    logger.info(
        f"🚀 Task started: {task.name} "
        f"[{task_id}] "
        f"Queue: {queue} "
        f"Retry: {task.request.retries or 0}"
    )


@task_postrun.connect
def task_complete_handler(sender=None, task_id=None, task=None, retval=None, **kwargs):
    """
    Track task completion and calculate duration
    Called after task successfully completes
    """
    if task_id in task_metrics:
        metric = task_metrics[task_id]
        duration = time.time() - metric['start_time']
        
        # Update worker metrics
        worker_metrics['tasks_completed'] += 1
        worker_metrics['total_execution_time'] += duration
        
        logger.info(
            f"✅ Task completed: {task.name} "
            f"[{task_id}] "
            f"Duration: {duration:.2f}s "
            f"Queue: {metric['queue']}"
        )
        
        # Log slow tasks (> 5 minutes)
        if duration > 300:
            logger.warning(
                f"⚠️ SLOW TASK: {task.name} took {duration:.2f}s "
                f"(> 5 minutes)"
            )
        
        # Clean up metrics
        del task_metrics[task_id]


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """
    Track task failures
    Called when task raises an exception
    """
    if task_id in task_metrics:
        metric = task_metrics[task_id]
        duration = time.time() - metric['start_time']
        
        # Update worker metrics
        worker_metrics['tasks_failed'] += 1
        
        logger.error(
            f"❌ Task failed: {sender.name} "
            f"[{task_id}] "
            f"Duration: {duration:.2f}s "
            f"Queue: {metric['queue']} "
            f"Error: {exception}"
        )
        
        # Clean up metrics
        del task_metrics[task_id]


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, **kwargs):
    """
    Track task retries
    Called when task is retried
    """
    # Update worker metrics
    worker_metrics['tasks_retried'] += 1
    
    logger.warning(
        f"🔄 Task retry: {sender.name} "
        f"[{task_id}] "
        f"Reason: {reason}"
    )


@task_revoked.connect
def task_revoked_handler(sender=None, request=None, terminated=None, **kwargs):
    """
    Track task revocations
    Called when task is revoked/cancelled
    """
    task_id = request.id if request else None
    task_name = sender.name if sender else 'unknown'
    
    logger.warning(
        f"🚫 Task revoked: {task_name} "
        f"[{task_id}] "
        f"Terminated: {terminated}"
    )


# =============================================================================
# WORKER LIFECYCLE SIGNALS
# =============================================================================

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """
    Called when worker is ready to accept tasks
    """
    worker_metrics['worker_uptime_start'] = time.time()
    
    logger.info(
        f"🟢 Worker ready: {sender.hostname} "
        f"Queues: {', '.join([q.name for q in sender.app.conf.task_queues])}"
    )


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """
    Called when worker is shutting down
    Print final metrics
    """
    uptime = time.time() - worker_metrics['worker_uptime_start'] if worker_metrics['worker_uptime_start'] else 0
    
    logger.info(
        f"🔴 Worker shutdown: {sender.hostname} "
        f"Uptime: {uptime:.0f}s "
        f"Completed: {worker_metrics['tasks_completed']} "
        f"Failed: {worker_metrics['tasks_failed']} "
        f"Retried: {worker_metrics['tasks_retried']}"
    )


# =============================================================================
# METRICS HELPERS
# =============================================================================

def get_current_metrics() -> Dict[str, Any]:
    """
    Get current worker metrics
    
    Returns:
        Dictionary with current metrics
    """
    uptime = time.time() - worker_metrics['worker_uptime_start'] if worker_metrics['worker_uptime_start'] else 0
    
    return {
        'uptime_seconds': uptime,
        'tasks_completed': worker_metrics['tasks_completed'],
        'tasks_failed': worker_metrics['tasks_failed'],
        'tasks_retried': worker_metrics['tasks_retried'],
        'total_execution_time': worker_metrics['total_execution_time'],
        'active_tasks': len(task_metrics),
        'active_task_ids': list(task_metrics.keys()),
    }


def get_task_metrics(task_id: str) -> Dict[str, Any]:
    """
    Get metrics for specific task
    
    Args:
        task_id: Task ID
        
    Returns:
        Task metrics or None
    """
    metric = task_metrics.get(task_id)
    if not metric:
        return None
    
    return {
        'task_id': task_id,
        'name': metric['name'],
        'queue': metric['queue'],
        'running_time': time.time() - metric['start_time'],
        'retries': metric['retries'],
    }


def get_queue_stats() -> Dict[str, Dict[str, int]]:
    """
    Get statistics per queue
    
    Returns:
        Dictionary with queue statistics
    """
    queue_stats = {}
    
    for task_id, metric in task_metrics.items():
        queue = metric['queue']
        if queue not in queue_stats:
            queue_stats[queue] = {
                'active_tasks': 0,
                'total_time': 0,
            }
        
        queue_stats[queue]['active_tasks'] += 1
        queue_stats[queue]['total_time'] += time.time() - metric['start_time']
    
    return queue_stats


# =============================================================================
# HEALTH CHECK
# =============================================================================

def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check
    
    Returns:
        Health status dictionary
    """
    metrics = get_current_metrics()
    queue_stats = get_queue_stats()
    
    # Calculate success rate
    total_tasks = metrics['tasks_completed'] + metrics['tasks_failed']
    success_rate = (metrics['tasks_completed'] / total_tasks * 100) if total_tasks > 0 else 0
    
    # Determine health status
    if success_rate < 50:
        status = 'unhealthy'
    elif success_rate < 80:
        status = 'degraded'
    else:
        status = 'healthy'
    
    return {
        'status': status,
        'uptime_seconds': metrics['uptime_seconds'],
        'success_rate': round(success_rate, 2),
        'tasks': {
            'completed': metrics['tasks_completed'],
            'failed': metrics['tasks_failed'],
            'retried': metrics['tasks_retried'],
            'active': metrics['active_tasks'],
        },
        'queues': queue_stats,
    }


# =============================================================================
# EXPORT
# =============================================================================
__all__ = [
    'get_current_metrics',
    'get_task_metrics',
    'get_queue_stats',
    'health_check',
]
