"""Check video for transcription 261"""
from app.database import SessionLocal
from app.models.generated_video import GeneratedVideo
from datetime import datetime, timedelta

db = SessionLocal()
try:
    videos = db.query(GeneratedVideo).filter_by(transcription_id=261).all()
    
    print(f"Found {len(videos)} video(s) for transcription 261:\n")
    
    for v in videos:
        print(f"Video ID: {v.id}")
        print(f"  Status: {v.status}")
        print(f"  Filename: {v.filename}")
        print(f"  Duration: {v.duration}s" if v.duration else "  Duration: None")
        print(f"  Created: {v.created_at}")
        print(f"  Completed: {v.completed_at}" if v.completed_at else "  Completed: None")
        
        # Check URL age
        if v.url:
            print(f"  URL exists: Yes")
            print(f"  URL (first 100 chars): {v.url[:100]}")
            
            # Calculate age
            if v.completed_at:
                age = datetime.utcnow() - v.completed_at
                print(f"  Video age: {age}")
                
                if age > timedelta(hours=24):
                    print(f"  ⚠️ URL likely expired (older than 24 hours)")
                else:
                    print(f"  ✅ URL should be valid")
        else:
            print(f"  URL exists: No")
        
        print()
        
finally:
    db.close()
