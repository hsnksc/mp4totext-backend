"""Generate fresh URL for video 261"""
from app.database import SessionLocal
from app.models.generated_video import GeneratedVideo
from app.services.storage import get_storage_service
from datetime import timedelta

db = SessionLocal()
storage = get_storage_service()

try:
    video = db.query(GeneratedVideo).filter_by(transcription_id=261).first()
    
    if video:
        print(f"Video ID: {video.id}")
        print(f"Filename: {video.filename}")
        print(f"Old URL (first 150 chars):")
        print(f"  {video.url[:150] if video.url else 'None'}...")
        print()
        
        # Generate fresh URL
        if video.filename:
            try:
                fresh_url = storage.minio_client.presigned_get_object(
                    bucket_name=storage.bucket_name,
                    object_name=video.filename,
                    expires=timedelta(hours=1)
                )
                print(f"✅ Fresh URL generated (expires in 1 hour):")
                print(f"  {fresh_url[:150]}...")
                print()
                print(f"Full URL:")
                print(fresh_url)
            except Exception as e:
                print(f"❌ Failed to generate URL: {e}")
        else:
            print("❌ No filename found")
    else:
        print("❌ No video found for transcription 261")
        
finally:
    db.close()
