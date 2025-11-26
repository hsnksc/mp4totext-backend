"""
Test Celery worker - Task gönderme testi
"""
import time
from app.celery_app import celery_app

print("=" * 60)
print("CELERY WORKER TEST")
print("=" * 60)

# Inspect worker
i = celery_app.control.inspect()

print("\n1. Active Workers:")
active = i.active()
if active:
    for worker, tasks in active.items():
        print(f"   - {worker}: {len(tasks)} active tasks")
else:
    print("   WARNING: No active workers found!")

print("\n2. Registered Tasks:")
registered = i.registered()
if registered:
    for worker, tasks in registered.items():
        print(f"   Worker: {worker}")
        for task in tasks:
            if not task.startswith('celery.'):
                print(f"     - {task}")
else:
    print("   WARNING: No registered tasks found!")

print("\n3. Worker Stats:")
stats = i.stats()
if stats:
    for worker, stat in stats.items():
        print(f"   {worker}:")
        print(f"     - Pool: {stat.get('pool', {}).get('implementation', 'unknown')}")
        print(f"     - Max concurrency: {stat.get('pool', {}).get('max-concurrency', 'unknown')}")
else:
    print("   WARNING: No worker stats available!")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
