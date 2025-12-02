#!/bin/bash
# Startup script for MP4toText Backend
# Runs migrations before starting services

set -e

echo "🚀 Starting MP4toText Backend..."

# Run database migrations
echo "📊 Running database migrations..."
cd /app

# Vision API migration
if [ -f "add_vision_api_support.py" ]; then
    echo "  → Running Vision API migration..."
    python add_vision_api_support.py || echo "  ⚠️ Vision migration skipped"
fi

# Credits system migration
if [ -f "add_credits_system.py" ]; then
    echo "  → Running Credits system migration..."
    python add_credits_system.py || echo "  ⚠️ Credits migration skipped"
fi

# AI Model pricing migration
if [ -f "add_ai_model_pricing.py" ]; then
    echo "  → Running AI Model pricing migration..."
    python add_ai_model_pricing.py || echo "  ⚠️ AI pricing migration skipped"
fi

echo "✅ Migrations complete!"

# Start supervisor (FastAPI + Celery)
echo "🔄 Starting services via supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
