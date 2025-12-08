#!/bin/bash
# Startup script for MP4toText Backend
# Runs migrations before starting services

set -e

echo "🚀 Starting MP4toText Backend..."

# Find database path
echo "🔍 Looking for database..."
if [ -f "/data/mp4totext.db" ]; then
    export DATABASE_PATH="/data/mp4totext.db"
    echo "  ✅ Found: /data/mp4totext.db"
elif [ -f "/app/data/mp4totext.db" ]; then
    export DATABASE_PATH="/app/data/mp4totext.db"
    echo "  ✅ Found: /app/data/mp4totext.db"
elif [ -f "/app/mp4totext.db" ]; then
    export DATABASE_PATH="/app/mp4totext.db"
    echo "  ✅ Found: /app/mp4totext.db"
elif [ -f "./mp4totext.db" ]; then
    export DATABASE_PATH="./mp4totext.db"
    echo "  ✅ Found: ./mp4totext.db"
else
    echo "  ⚠️ Database not found, will be created on first run"
fi

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

# PKB/RAG fields for Sources migration
if [ -f "add_source_pkb_fields.py" ]; then
    echo "  → Running Source PKB fields migration..."
    python add_source_pkb_fields.py || echo "  ⚠️ PKB fields migration skipped"
fi

# Pulse platform migration
if [ -f "add_pulse_platform.py" ]; then
    echo "  → Running Pulse platform migration..."
    python add_pulse_platform.py || echo "  ⚠️ Pulse migration skipped"
fi

echo "✅ Migrations complete!"

# Start supervisor (FastAPI + Celery)
echo "🔄 Starting services via supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
