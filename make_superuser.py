"""
Set a user as superuser for testing admin features
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import get_settings
from app.models.user import User

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def make_superuser(username: str):
    """Make a user superuser"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User '{username}' not found")
            print("\n📋 Available users:")
            all_users = db.query(User).all()
            for u in all_users:
                status = "👑 SUPERUSER" if u.is_superuser else "👤 Regular"
                print(f"  • {u.username} ({u.email}) - {status}")
            return
        
        if user.is_superuser:
            print(f"✅ User '{username}' is already a superuser")
        else:
            user.is_superuser = True
            db.commit()
            print(f"✅ User '{username}' is now a superuser!")
        
        print(f"\n👤 User details:")
        print(f"  • Username: {user.username}")
        print(f"  • Email: {user.email}")
        print(f"  • Credits: {user.credits}")
        print(f"  • Superuser: {user.is_superuser}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python make_superuser.py <username>")
        print("Example: python make_superuser.py testuser")
        sys.exit(1)
    
    username = sys.argv[1]
    print(f"🚀 Making '{username}' a superuser...\n")
    make_superuser(username)
