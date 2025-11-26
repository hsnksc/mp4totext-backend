# Modal FFmpeg Deployment Guide

## 🎯 Overview

Modal FFmpeg service, video processing işlemlerini uzak sunucuda çalıştırarak:

- ✅ **Hızlı**: Otomatik ölçekleme ile paralel işlem
- ✅ **Ucuz**: Sadece kullandığınız süre kadar ödeme ($0.000025/saniye)
- ✅ **Kolay**: Sunucu yönetimi yok, otomatik deployment
- ✅ **Güvenilir**: Auto-scaling ve error handling

## 📊 Pricing Comparison

### Current (Local FFmpeg)

```
Server Requirements:
- CPU: 4+ cores
- RAM: 8GB+
- Storage: Fast SSD
- Cost: $50-100/month

Processing:
- 1 video segment: ~15 seconds
- 100 segments: ~25 minutes (sequential)
- Server always running, always paying
```

### Modal FFmpeg (Recommended)

```
Pay-per-use:
- $0.000025 per CPU-second
- Auto-scaling: 0-100 concurrent processes
- Free tier: 50 hours/month

Cost Example:
- 1 video segment: 15 seconds × $0.000025 = $0.000375 (0.04 cent!)
- 100 segments: 1500 seconds × $0.000025 = $0.0375 ($0.04)
- 1000 segments/day: $0.375/day ($11/month)

FREE TIER covers:
- 50 hours = 180,000 CPU-seconds
- ~12,000 video segments/month
- Perfect for development and small-medium usage
```

## 🚀 Quick Start

### 1. Install Modal

```bash
pip install modal
```

### 2. Create Modal Account

```bash
modal setup
```

Bu komut browser açacak ve Modal hesabı oluşturmanızı isteyecek (ücretsiz).

### 3. Set Modal Token

Modal token'ı environment variable olarak kaydedin:

```bash
# Windows PowerShell
$env:MODAL_TOKEN_ID="your_token_id"
$env:MODAL_TOKEN_SECRET="your_token_secret"

# Linux/Mac
export MODAL_TOKEN_ID="your_token_id"
export MODAL_TOKEN_SECRET="your_token_secret"
```

Token'ları `modal setup` komutundan sonra bulabilirsiniz.

### 4. Deploy to Modal

```bash
cd mp4totext-backend
modal deploy modal_ffmpeg_service.py
```

Output:

```
✅ Created objects.
├── 🔨 Created mount /code/mp4totext-backend
├── 🔨 Created function FFmpegService.create_video_segment
├── 🔨 Created function FFmpegService.concatenate_videos
├── 🔨 Created function FFmpegService.extract_audio
└── 🔨 Created function FFmpegService.batch_create_videos

✅ App deployed! 🎉

View at: https://modal.com/apps/your-workspace/mp4totext-ffmpeg
```

### 5. Test Deployment

```bash
modal run modal_ffmpeg_service.py
```

Bu test video oluşturacak ve başarıyı doğrulayacak.

### 6. Update Backend Configuration

`.env` dosyanıza ekleyin:

```bash
# Modal Configuration
MODAL_TOKEN_ID=your_token_id
MODAL_TOKEN_SECRET=your_token_secret
USE_MODAL_FFMPEG=true
```

## 📝 Usage in Backend

### Option 1: Automatic (Recommended)

Backend otomatik olarak Modal'ı kullanacak:

```python
from app.services.modal_ffmpeg_adapter import get_ffmpeg_service

# Auto-detect: Modal varsa Modal, yoksa local FFmpeg
ffmpeg = get_ffmpeg_service()

# Create video segment
output_path = ffmpeg.create_video_segment(
    image_url="https://storage.example.com/image.png",
    audio_url="https://storage.example.com/audio.mp3",
    output_path="/path/to/output.mp4"
)

# Concatenate videos
final_video = ffmpeg.concatenate_videos(
    video_urls=[
        "https://storage.example.com/segment1.mp4",
        "https://storage.example.com/segment2.mp4"
    ],
    output_path="/path/to/final.mp4"
)

# Batch processing (parallel on Modal)
segments = [
    {
        "image_url": "https://...",
        "audio_url": "https://...",
        "output_filename": "segment_001.mp4"
    },
    # ... more segments
]

output_paths = ffmpeg.batch_create_videos(
    segments=segments,
    output_dir="/path/to/output"
)
```

### Option 2: Force Modal or Local

```python
# Force Modal
ffmpeg = get_ffmpeg_service(use_modal=True)

# Force Local
ffmpeg = get_ffmpeg_service(use_modal=False)
```

### Option 3: Direct Modal Access

```python
from modal import Cls

FFmpegService = Cls.lookup("mp4totext-ffmpeg", "FFmpegService")

# Create video
video_data = FFmpegService().create_video_segment.remote(
    image_url="https://...",
    audio_url="https://..."
)

# Save video
with open("output.mp4", "wb") as f:
    f.write(video_data)
```

## 🔄 Update Worker to Use Modal

Update `app/workers/transcription_worker.py`:

```python
from app.services.modal_ffmpeg_adapter import get_ffmpeg_service

# In generate_video_from_transcription task
def generate_video_from_transcription(self, transcription_id: int, user_id: int):
    # ... existing code ...

    # Replace local FFmpeg with Modal adapter
    ffmpeg = get_ffmpeg_service()  # Auto-detect Modal/local

    # Process segments in parallel (if Modal)
    segments = [
        {
            "image_url": img["url"],
            "audio_url": audio["url"],
            "audio_duration": audio["duration"],
            "output_filename": f"segment_{i:03d}.mp4"
        }
        for i, (img, audio) in enumerate(zip(images, audio_chunks))
    ]

    # Batch process (parallel on Modal, sequential on local)
    video_paths = ffmpeg.batch_create_videos(
        segments=segments,
        output_dir=temp_dir
    )

    # Concatenate all segments
    final_video = ffmpeg.concatenate_videos(
        video_urls=video_paths,
        output_path=final_output_path
    )
```

## 🛠️ Features

### 1. Create Video Segment

Image + Audio → Video

```python
video_data = ffmpeg.create_video_segment(
    image_url="https://storage.com/image.png",
    audio_url="https://storage.com/audio.mp3",
    audio_duration=10.5  # optional
)
```

### 2. Concatenate Videos

Multiple videos → Single video

```python
final_video = ffmpeg.concatenate_videos(
    video_urls=[
        "https://storage.com/seg1.mp4",
        "https://storage.com/seg2.mp4"
    ]
)
```

### 3. Extract Audio

Video → Audio

```python
audio_data = ffmpeg.extract_audio(
    video_url="https://storage.com/video.mp4",
    output_format="mp3"
)
```

### 4. Batch Processing

Multiple segments in parallel

```python
segments = [
    {"image_url": "...", "audio_url": "...", "output_filename": "seg1.mp4"},
    {"image_url": "...", "audio_url": "...", "output_filename": "seg2.mp4"},
    # ... more segments
]

videos = ffmpeg.batch_create_videos(segments, "/output/dir")
```

## 📈 Performance Benefits

### Sequential Processing (Local)

```
100 segments × 15 seconds = 1500 seconds (25 minutes)
Server running 100% CPU for 25 minutes
```

### Parallel Processing (Modal)

```
100 segments ÷ 10 parallel workers = 10 batches
10 batches × 15 seconds = 150 seconds (2.5 minutes)
10x faster! Only pay for 1500 CPU-seconds
```

## 🔍 Monitoring

### Check Service Status

```python
from app.services.modal_ffmpeg_adapter import get_ffmpeg_service

ffmpeg = get_ffmpeg_service()
info = ffmpeg.get_service_info()

print(info)
# {
#   "using_modal": true,
#   "service": "Modal FFmpeg",
#   "modal_available": true,
#   "modal_token_set": true
# }
```

### View Modal Dashboard

https://modal.com/dashboard

- View active functions
- Monitor usage and costs
- Check logs and errors
- Track performance metrics

## 🚨 Troubleshooting

### Issue: "Modal token not found"

**Solution:**

```bash
# Set environment variables
export MODAL_TOKEN_ID="your_token_id"
export MODAL_TOKEN_SECRET="your_token_secret"

# Restart backend
python run.py
```

### Issue: "Function not found"

**Solution:**

```bash
# Redeploy to Modal
modal deploy modal_ffmpeg_service.py
```

### Issue: "Connection timeout"

**Solution:**

```bash
# Check Modal service status
modal app logs mp4totext-ffmpeg

# Restart if needed
modal app restart mp4totext-ffmpeg
```

### Issue: "Out of free tier quota"

**Solution:**

```bash
# Check usage
modal profile show

# Options:
1. Wait until next month (quota resets)
2. Add payment method (very cheap)
3. Use local FFmpeg temporarily:
   USE_MODAL_FFMPEG=false
```

## 💰 Cost Optimization

### 1. Use Batch Processing

```python
# ❌ Bad: Sequential remote calls (slow + expensive)
for segment in segments:
    video = ffmpeg.create_video_segment(...)

# ✅ Good: Single batch call (fast + cheap)
videos = ffmpeg.batch_create_videos(segments, output_dir)
```

### 2. Cache Results

```python
# Store processed videos in MinIO/S3
# Reuse cached videos instead of re-processing
```

### 3. Monitor Usage

```bash
# Check daily usage
modal profile show --detailed

# Set budget alerts in Modal dashboard
```

## 🔐 Security

### Environment Variables

NEVER commit secrets to git:

```bash
# ❌ Bad
MODAL_TOKEN_ID=modal_123456  # In .env file in git

# ✅ Good
# Add to .gitignore
echo ".env" >> .gitignore

# Store in secure environment
export MODAL_TOKEN_ID="..."
```

### URL Access

Modal functions accept URLs, not local files:

- ✅ Use MinIO/S3 URLs
- ✅ Use presigned URLs with expiration
- ❌ Don't use localhost URLs (Modal can't reach)

## 📚 Additional Resources

- Modal Documentation: https://modal.com/docs
- Modal Pricing: https://modal.com/pricing
- FFmpeg Documentation: https://ffmpeg.org/documentation.html
- Examples: https://github.com/modal-labs/modal-examples

## 🎉 Success Metrics

After deploying Modal FFmpeg, you should see:

1. **10x faster** video processing (parallel)
2. **90% cost reduction** (pay-per-use vs always-on server)
3. **Zero maintenance** (no FFmpeg updates, no server management)
4. **Auto-scaling** (handles traffic spikes automatically)

## ⚡ Next Steps

1. Deploy to Modal: `modal deploy modal_ffmpeg_service.py`
2. Test: `modal run modal_ffmpeg_service.py`
3. Update backend: Set `USE_MODAL_FFMPEG=true`
4. Monitor: Check Modal dashboard
5. Optimize: Use batch processing for better performance

---

**Need help?** Check Modal support: https://modal.com/support
