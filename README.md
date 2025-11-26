# MP4toText Backend API

Production-ready FastAPI backend for MP4toText mobile application.

## 🎯 Features

- ✅ Audio/Video transcription (Whisper)
- ✅ Speaker recognition (Global Model + RunPod)
- ✅ AI text enhancement (Gemini)
- ✅ JWT authentication
- ✅ File upload + cloud storage
- ✅ WebSocket real-time progress
- ✅ Background job processing (Celery + Redis)
- ✅ RESTful API
- ✅ Comprehensive documentation

## 🏗️ Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL
- **Cache**: Redis
- **Storage**: MinIO (S3-compatible)
- **Task Queue**: Celery
- **AI Models**: Whisper, Global Speaker Model, Gemini
- **Deployment**: Docker + Google Cloud Run

## 📁 Project Structure

```
mp4totext-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration
│   ├── database.py             # Database connection
│   ├── dependencies.py         # FastAPI dependencies
│   │
│   ├── auth/                   # Authentication
│   │   ├── __init__.py
│   │   ├── models.py          # User model
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── router.py          # Auth endpoints
│   │   └── utils.py           # JWT utilities
│   │
│   ├── api/                    # API endpoints
│   │   ├── __init__.py
│   │   ├── transcription.py   # Transcription endpoints
│   │   ├── speaker.py         # Speaker recognition
│   │   ├── enhancement.py     # Text enhancement
│   │   └── files.py           # File management
│   │
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── transcription.py
│   │   └── file.py
│   │
│   ├── schemas/                # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── transcription.py
│   │   ├── speaker.py
│   │   └── user.py
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── whisper_service.py
│   │   ├── speaker_service.py
│   │   ├── gemini_service.py
│   │   └── storage_service.py
│   │
│   ├── workers/                # Celery tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── tasks.py
│   │
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── audio.py
│       ├── websocket.py
│       └── logger.py
│
├── models/                      # AI model files
│   ├── best_model.pth
│   └── speaker_mapping.json
│
├── tests/                       # Tests
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_transcription.py
│   └── test_speaker.py
│
├── alembic/                     # Database migrations
│   └── versions/
│
├── .env                         # Environment variables
├── .env.example                 # Environment template
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- FFmpeg

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/mp4totext-backend.git
cd mp4totext-backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# 5. Run database migrations
alembic upgrade head

# 6. Start services (in separate terminals)

# Terminal 1: API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Redis (if not already running)
redis-server
```

### Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📚 API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔐 Authentication

```bash
# Register new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'

# Use returned JWT token in subsequent requests
curl -X GET http://localhost:8000/api/v1/transcriptions \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🎙️ Transcription API

```bash
# Upload and transcribe audio/video
curl -X POST http://localhost:8000/api/v1/transcriptions \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@audio.mp3" \
  -F "language=tr" \
  -F "model_size=base" \
  -F "use_speaker_recognition=true"

# Get transcription status
curl -X GET http://localhost:8000/api/v1/transcriptions/{task_id} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# List all transcriptions
curl -X GET http://localhost:8000/api/v1/transcriptions \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🎤 Speaker Recognition API

```bash
# Get speaker info
curl -X GET http://localhost:8000/api/v1/speaker/info \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Identify speaker in audio segment
curl -X POST http://localhost:8000/api/v1/speaker/identify \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@segment.wav" \
  -F "threshold=0.70"
```

## 🤖 Text Enhancement API

```bash
# Enhance transcribed text with Gemini AI
curl -X POST http://localhost:8000/api/v1/enhancement/improve \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Raw transcription text...",
    "options": {
      "remove_filler_words": true,
      "add_punctuation": true,
      "create_paragraphs": true
    }
  }'
```

## 🔌 WebSocket Real-time Updates

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/{task_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress + '%');
  console.log('Status:', data.status);
};
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_transcription.py

# Run with verbose output
pytest -v
```

## 📊 Monitoring

- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Logs**: Structured JSON logs with correlation IDs

## 🚢 Deployment

### Google Cloud Run

```bash
# Build and push Docker image
gcloud builds submit --tag gcr.io/PROJECT_ID/mp4totext-api

# Deploy to Cloud Run
gcloud run deploy mp4totext-api \
  --image gcr.io/PROJECT_ID/mp4totext-api \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --timeout 900s \
  --set-env-vars DATABASE_URL=$DATABASE_URL \
  --set-env-vars REDIS_URL=$REDIS_URL \
  --allow-unauthenticated
```

### Docker Compose (Production)

```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale worker=4
```

## 🔧 Configuration

Key environment variables (see `.env.example`):

```bash
# App
APP_NAME=MP4toText
APP_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/mp4totext

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage (MinIO/S3)
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_BUCKET=mp4totext

# AI Services
OPENAI_API_KEY=your-openai-key  # For Whisper (if using API)
GEMINI_API_KEY=your-gemini-key
HF_TOKEN=your-huggingface-token  # For speaker models

# JWT
JWT_SECRET=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600  # seconds

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## 📈 Performance

- **Throughput**: 100+ requests/second (with proper scaling)
- **Transcription**: ~10-20 seconds for 1-minute audio (base model)
- **Speaker Recognition**: <1 second per segment
- **Response Time**: <100ms for API endpoints (excluding long-running tasks)

## 🔒 Security

- ✅ JWT authentication
- ✅ Password hashing (bcrypt)
- ✅ Rate limiting
- ✅ CORS configuration
- ✅ Input validation
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ XSS protection
- ✅ File upload validation

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📞 Support

- **Email**: support@mp4totext.com
- **GitHub Issues**: https://github.com/yourusername/mp4totext-backend/issues
- **Documentation**: https://docs.mp4totext.com

## 🙏 Acknowledgments

- OpenAI Whisper
- PyTorch
- FastAPI
- Google Gemini
- RunPod Global Speaker Model

---

**Version**: 1.0.0
**Last Updated**: October 16, 2025
**Status**: Active Development 🚀
