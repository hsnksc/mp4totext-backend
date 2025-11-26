"""
Hızlı servis kontrolü - Backend test öncesi
"""
import sys

print("🔍 SERVİS KONTROL RAPORU")
print("="*60)

# 1. Redis kontrolü
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, socket_timeout=2)
    r.ping()
    print("✅ Redis: RUNNING")
except Exception as e:
    print(f"❌ Redis: NOT RUNNING - {e}")
    print("   Redis'i başlatmak için: redis-server veya Docker ile çalıştırın")

# 2. Celery worker kontrolü
try:
    from app.celery_app import celery_app
    inspect = celery_app.control.inspect(timeout=2)
    active = inspect.active_queues()
    if active:
        print(f"✅ Celery Workers: {len(active)} worker(s) active")
        for worker_name, queues in active.items():
            print(f"   - {worker_name}: {[q['name'] for q in queues]}")
    else:
        print("❌ Celery Workers: NO WORKERS")
        print("   Worker başlatmak için: .\\start_celery.ps1")
except Exception as e:
    print(f"❌ Celery Workers: ERROR - {e}")

# 3. Database kontrolü
try:
    import sqlite3
    conn = sqlite3.connect('mp4totext.db')
    cursor = conn.cursor()
    count = cursor.execute("SELECT COUNT(*) FROM transcriptions").fetchone()[0]
    conn.close()
    print(f"✅ Database: OK ({count} transcriptions)")
except Exception as e:
    print(f"❌ Database: ERROR - {e}")

# 4. Storage klasörü kontrolü
import os
storage_path = "storage/uploads"
if os.path.exists(storage_path):
    print(f"✅ Storage: {storage_path} klasörü mevcut")
else:
    print(f"⚠️  Storage: {storage_path} klasörü YOK - oluşturulacak")

print("\n" + "="*60)
print("📋 ÖZET:")
print("   Backend hazır: http://localhost:8002")
print("   Docs: http://localhost:8002/docs")
print("\n💡 Eksik servisler varsa:")
print("   Redis: redis-server (veya Docker)")
print("   Celery: .\\start_celery.ps1")
