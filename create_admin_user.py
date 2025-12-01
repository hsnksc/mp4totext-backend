"""
Create Admin User Script
Creates or updates a user to have admin privileges
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.models.source import Source  # Import Source to resolve relationship
from app.auth.utils import get_password_hash

def create_admin_user(username: str = "admin", email: str = "admin@mp4totext.com", password: str = "admin123"):
    """Create or update admin user"""
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(User).filter(User.username == username).first()
        
        if user:
            # Update existing user to admin
            user.is_superuser = True
            user.is_active = True
            print(f"✅ Updated existing user '{username}' to admin")
        else:
            # Create new admin user
            hashed_password = get_password_hash(password)
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_superuser=True,
                is_active=True,
                credits=1000.0  # Give admin lots of credits
            )
            db.add(user)
            print(f"✅ Created new admin user '{username}' with password '{password}'")
        
        db.commit()
        db.refresh(user)
        
        print(f"""
╔════════════════════════════════════════════════════════════╗
║                    ADMIN USER READY                        ║
╠════════════════════════════════════════════════════════════╣
║  Username:     {username:<42} ║
║  Email:        {email:<42} ║
║  Password:     {password:<42} ║
║  Credits:      {user.credits:<42} ║
║  Is Admin:     True                                        ║
╚════════════════════════════════════════════════════════════╝
        """)
        
        return user
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def make_user_admin(username: str):
    """Make an existing user an admin"""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User '{username}' not found")
            return None
        
        user.is_superuser = True
        db.commit()
        
        print(f"✅ User '{username}' is now an admin!")
        return user
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Make existing user admin
        username = sys.argv[1]
        make_user_admin(username)
    else:
        # Create default admin user
        create_admin_user()
