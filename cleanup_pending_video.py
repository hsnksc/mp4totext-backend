"""Clean up pending video generation task"""
from app.database import SessionLocal
from app.models.generated_video import GeneratedVideo

db = SessionLocal()
try:
    video = db.query(GeneratedVideo).filter_by(
        task_id='9c636f82-e372-4d7e-89c4-c67cb50dd6f1'
    ).first()
    
    if video:
        db.delete(video)
        db.commit()
        print(f'✅ Video {video.id} silindi')
    else:
        print('⚠️ Video bulunamadı')
finally:
    db.close()
