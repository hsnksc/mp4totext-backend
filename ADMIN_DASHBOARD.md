# Admin Dashboard - Transcription Provider Settings

## 📍 Lokasyon
**Web UI**: `http://localhost:5173/admin/settings` (React sayfası)
**Backend API**: `http://localhost:8002/api/v1/admin/transcription-provider`

## 🎯 Özellikler

Admin dashboard'dan transcription provider'ı değiştirebilirsiniz:

### Provider Seçenekleri:

#### 1. **Local** (Faster-Whisper)
- ✅ No external costs
- ✅ Full privacy (data stays local)
- ❌ Requires CPU/GPU resources
- ❌ Slower on CPU-only machines
- **Use case**: Development, privacy-sensitive data

#### 2. **RunPod Serverless**
- ✅ Cloud GPU ($0.00045/second)
- ✅ Fast transcription
- ❌ Limited to ~10MB files (base64 limitation)
- ❌ Official worker doesn't support audio_url
- **Status**: ⚠️ Limited - only for small files

#### 3. **Modal Labs** (Recommended)
- ✅ Cloud GPU (free $30/month)
- ✅ Supports large files (URL upload)
- ✅ Fast deployment
- ✅ Auto-scaling
- ✅ ngrok integration for MinIO
- **Use case**: Production, large files

## 🔧 Kurulum

### Backend API Kullanımı

#### GET Provider Status
```bash
curl -X GET http://localhost:8002/api/v1/admin/transcription-provider \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Response:**
```json
{
  "current_provider": "modal",
  "providers": [
    {
      "name": "local",
      "enabled": false,
      "configured": true,
      "healthy": true,
      "description": "Local Faster-Whisper (CPU/GPU) - No external costs"
    },
    {
      "name": "runpod",
      "enabled": false,
      "configured": true,
      "healthy": false,
      "description": "RunPod Serverless - Cloud GPU (~$0.00045/sec)"
    },
    {
      "name": "modal",
      "enabled": true,
      "configured": true,
      "healthy": true,
      "description": "Modal Labs - Serverless GPU, $30 free/month"
    }
  ]
}
```

#### POST Update Provider

**Switch to Modal:**
```bash
curl -X POST http://localhost:8002/api/v1/admin/transcription-provider \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "modal",
    "modal_token_id": "ak-xxxxx",
    "modal_token_secret": "as-xxxxx",
    "modal_function_name": "whisper-transcribe"
  }'
```

**Switch to Local:**
```bash
curl -X POST http://localhost:8002/api/v1/admin/transcription-provider \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type": application/json" \
  -d '{
    "provider": "local"
  }'
```

**Switch to RunPod:**
```bash
curl -X POST http://localhost:8002/api/v1/admin/transcription-provider \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type": application/json" \
  -d '{
    "provider": "runpod",
    "runpod_api_key": "rpa_xxxxx",
    "runpod_endpoint_id": "q3arg0kg6iadou",
    "runpod_timeout": 300
  }'
```

## 🖥️ Frontend Kullanımı

### React Component
Admin settings sayfası: `src/pages/AdminSettings.tsx`

**Features:**
- Provider status görüntüleme (configured, enabled, healthy)
- Provider seçimi (radio buttons)
- Credentials girişi (conditional forms)
- Validation ve error handling
- Success/error messages
- Auto-refresh after save

### Routing
Web app routing'e ekleyin (örnek):
```tsx
// App.tsx or Routes.tsx
import AdminSettings from './pages/AdminSettings';

<Route path="/admin/settings" element={<AdminSettings />} />
```

### Navigation
Dashboard'a admin link ekleyin:
```tsx
{user.is_superuser && (
  <Link to="/admin/settings">
    ⚙️ Admin Settings
  </Link>
)}
```

## 🔄 Workflow

### Provider Değiştirme:

1. **Admin dashboard'a git**: `http://localhost:5173/admin/settings`

2. **Provider seç**: Local / RunPod / Modal

3. **Credentials gir** (Modal için):
   - Token ID: `ak-xxxxx`
   - Token Secret: `as-xxxxx`
   
4. **Save tıkla**

5. **Backend ve Celery restart**:
   ```powershell
   # Terminal 1: Backend restart
   cd mp4totext-backend
   python run.py
   
   # Terminal 2: Celery restart
   .\start_celery.ps1
   
   # Terminal 3: ngrok (Modal için gerekli)
   ngrok http 9000
   
   # Terminal 4: Update .env with ngrok URL
   STORAGE_ENDPOINT=xxxx.ngrok-free.app
   ```

6. **Test et**: Büyük dosya yükle (>10MB)

## 🔐 Authorization

Sadece **admin (superuser)** kullanıcılar erişebilir:

```python
# Backend check
def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(403, "Admin access required")
    return current_user
```

## 📊 Provider Comparison

| Feature | Local | RunPod | Modal |
|---------|-------|--------|-------|
| Cost | Free | ~$0.03/min | Free $30/mo |
| File Size | Unlimited | <10MB | Unlimited |
| Speed | CPU: Slow<br>GPU: Fast | Very Fast | Very Fast |
| Setup | Easy | Medium | Easy |
| Privacy | ✅ Local | ❌ Cloud | ❌ Cloud |
| Scalability | ❌ Limited | ✅ Auto | ✅ Auto |
| **Recommended** | Dev | ❌ Limited | ✅ Production |

## 🚀 Production Deployment

### Önerilen Konfigürasyon:

**Development:**
```env
USE_MODAL=false
USE_RUNPOD=false
# Uses Local by default
```

**Production (Small files <10MB):**
```env
USE_MODAL=false
USE_RUNPOD=true
RUNPOD_API_KEY=rpa_xxxxx
RUNPOD_ENDPOINT_ID=xxxxx
```

**Production (All file sizes):**
```env
USE_MODAL=true
USE_RUNPOD=false
MODAL_TOKEN_ID=ak-xxxxx
MODAL_TOKEN_SECRET=as-xxxxx
MODAL_FUNCTION_NAME=whisper-transcribe

# ngrok URL (or production domain)
STORAGE_ENDPOINT=your-domain.com
STORAGE_SECURE=true
```

## 🐛 Troubleshooting

### Provider Status "Unhealthy"

**RunPod:**
```bash
# Test endpoint
curl https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/health
```

**Modal:**
```bash
# Test function
modal run modal_whisper_function.py
```

**Local:**
```bash
# Test Faster-Whisper
python -c "import faster_whisper; print('OK')"
```

### Settings Not Saving

1. Check admin token: `curl -H "Authorization: Bearer TOKEN" http://localhost:8002/api/v1/admin/transcription-provider`
2. Check .env permissions
3. Check logs: Backend console

### Changes Not Applied

**Mutlaka restart gerekli:**
```powershell
# Backend restart (CTRL+C then)
python run.py

# Celery restart (CTRL+C then)
.\start_celery.ps1
```

## 📝 API Endpoints Summary

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/admin/transcription-provider` | GET | Admin | Get all providers status |
| `/api/v1/admin/transcription-provider` | POST | Admin | Update active provider |
| `/api/v1/admin/runpod/health` | GET | Admin | Test RunPod endpoint |

## 💡 Best Practices

1. **Always test after switching providers**
2. **Keep credentials in .env, not in code**
3. **Monitor costs** (Modal: free $30/mo, RunPod: pay-per-use)
4. **Use ngrok for Modal** (large file support)
5. **Restart backend + Celery** after changes
6. **Check health status** before uploading

## 🎓 Example Full Workflow

```bash
# 1. Get current status
curl http://localhost:8002/api/v1/admin/transcription-provider

# 2. Switch to Modal
curl -X POST http://localhost:8002/api/v1/admin/transcription-provider \
  -d '{"provider": "modal", "modal_token_id": "ak-xxx", "modal_token_secret": "as-xxx"}'

# 3. Restart services
pkill -f "python run.py"
python run.py &

pkill -f celery
.\start_celery.ps1

# 4. Start ngrok (for Modal large files)
ngrok http 9000

# 5. Update .env with ngrok URL
echo "STORAGE_ENDPOINT=xxxx.ngrok-free.app" >> .env

# 6. Test upload
curl -X POST http://localhost:8002/api/v1/transcriptions/upload \
  -F "file=@large_audio.m4a"
```

## ✅ Verification Checklist

After switching providers:

- [ ] Backend restarted successfully
- [ ] Celery worker restarted successfully
- [ ] Provider status shows "healthy"
- [ ] ngrok tunnel running (if Modal + large files)
- [ ] .env updated with correct credentials
- [ ] Test file upload successful
- [ ] Transcription completed successfully
- [ ] Credits deducted correctly

---

**Need help?** Check logs:
- Backend: Terminal running `python run.py`
- Celery: Terminal running `.\start_celery.ps1`
- ngrok: Terminal running `ngrok http 9000`
