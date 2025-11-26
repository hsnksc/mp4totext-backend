"""
Add credits system to users and create credit_transactions table

Run with: python add_credits_system.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.settings import get_settings
from app.database import Base
from app.models.user import User
from app.models.credit_transaction import CreditTransaction, OperationType

settings = get_settings()

def migrate():
    """Add credits column to users and create credit_transactions table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    print("🔧 Starting credit system migration...")
    
    with engine.connect() as conn:
        # Check if credits column exists
        print("📊 Checking if credits column exists...")
        try:
            result = conn.execute(text("SELECT credits FROM users LIMIT 1"))
            print("✅ Credits column already exists!")
        except Exception:
            print("➕ Adding credits column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN credits INTEGER DEFAULT 100"))
            conn.commit()
            print("✅ Credits column added successfully!")
        
        # Update existing users to have 100 credits if NULL
        print("🎁 Updating existing users with initial credits...")
        result = conn.execute(text("UPDATE users SET credits = 100 WHERE credits IS NULL"))
        conn.commit()
        print(f"✅ Updated {result.rowcount} users with 100 initial credits")
    
    # Create credit_transactions table
    print("📦 Creating credit_transactions table...")
    Base.metadata.create_all(engine, tables=[CreditTransaction.__table__])
    print("✅ Credit transactions table created!")
    
    print("\n🎉 Migration completed successfully!")
    print("\n📋 Summary:")
    print("  - Added 'credits' column to users (default: 100)")
    print("  - Created 'credit_transactions' table")
    print("  - All existing users now have 100 free credits")
    print("\n💰 Credit Pricing:")
    print("  - Transcription: 10 credits/minute")
    print("  - Speaker Recognition: +5 credits/minute")
    print("  - AI Enhancement: 20 credits")
    print("  - Lecture Notes: 30 credits")
    print("  - Custom Prompt: 25 credits")
    print("  - Exam Questions: 35 credits")
    print("  - Translation: 15 credits")
    print("  - YouTube Download: +10 credits")

if __name__ == "__main__":
    migrate()
