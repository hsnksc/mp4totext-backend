"""Set testuser as superuser"""
from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.username == 'testuser').first()
    if user:
        user.is_superuser = True
        db.commit()
        print(f"✅ testuser is now superuser: is_superuser={user.is_superuser}")
    else:
        print("❌ testuser not found")
finally:
    db.close()
