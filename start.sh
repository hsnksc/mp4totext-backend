#!/bin/bash

echo "🚀 MP4toText Backend Başlatılıyor..."
echo ""

# Virtual environment'ı aktifleştir
source venv/bin/activate

# Servislerin çalıştığını kontrol et
echo "📦 Docker servisleri kontrol ediliyor..."
docker-compose ps

echo ""
echo "🔧 Environment variables yükleniyor..."

# FastAPI sunucusunu başlat (background)
echo ""
echo "🌐 FastAPI sunucusu başlatılıyor (http://localhost:8000)..."
echo "📚 API Docs: http://localhost:8000/docs"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Birkaç saniye bekle
sleep 3

# Celery worker'ı başlat (background)
echo ""
echo "⚙️  Celery worker başlatılıyor..."
celery -A app.workers.transcription_worker worker --loglevel=info &

echo ""
echo "✅ Backend başlatıldı!"
echo ""
echo "🛑 Durdurmak için: pkill -f uvicorn && pkill -f celery"
