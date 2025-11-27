"""
API-based Migration Script
Migrates data from SQLite to PostgreSQL via API
"""
import sqlite3
import requests
import json
from datetime import datetime

# Configuration
SQLITE_PATH = "mp4totext.db"
API_BASE = "https://api.gistify.pro/api/v1"

def get_sqlite_data():
    """Get all data from SQLite"""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get users
    cur.execute("SELECT * FROM users")
    users = [dict(row) for row in cur.fetchall()]
    
    # Get transcriptions
    cur.execute("SELECT * FROM transcriptions")
    transcriptions = [dict(row) for row in cur.fetchall()]
    
    # Get credit transactions
    cur.execute("SELECT * FROM credit_transactions")
    transactions = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    return {
        "users": users,
        "transcriptions": transcriptions,
        "transactions": transactions
    }

def register_user(username, email, password="TempPass123!"):
    """Register a user via API"""
    try:
        response = requests.post(
            f"{API_BASE}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400 and "already" in response.text.lower():
            print(f"  ⚠️ User {username} already exists")
            return {"exists": True}
        else:
            print(f"  ❌ Failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def login_user(username, password="TempPass123!"):
    """Login and get token"""
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            data={
                "username": username,
                "password": password
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    except Exception as e:
        print(f"  ❌ Login error: {e}")
        return None

def main():
    print("=" * 60)
    print("🚀 API-based Migration: SQLite → PostgreSQL")
    print("=" * 60)
    
    # Get SQLite data
    print("\n📦 Reading SQLite database...")
    data = get_sqlite_data()
    
    print(f"  • Users: {len(data['users'])}")
    print(f"  • Transcriptions: {len(data['transcriptions'])}")
    print(f"  • Credit Transactions: {len(data['transactions'])}")
    
    # Show users
    print("\n👥 Users in SQLite:")
    for user in data['users']:
        print(f"  • {user['username']} ({user['email']}) - Credits: {user['credits']}")
    
    print("\n" + "=" * 60)
    print("📝 Migration Options:")
    print("=" * 60)
    print("""
Since we can't directly insert hashed passwords via API, you have 2 options:

OPTION 1: Register users with new passwords
  - Users will need to use new passwords
  - Run: python api_migrate.py --register

OPTION 2: Direct database migration (recommended)
  - Use Coolify Terminal to run migration inside container
  - Preserves original passwords and all data

For Option 2, in Coolify Terminal run:
  python -c "
  from app.database import SessionLocal, engine
  from app.models import User
  db = SessionLocal()
  # Check if tables exist
  print('Users:', db.query(User).count())
  "
""")
    
    # Test API connection
    print("\n🔌 Testing API connection...")
    try:
        response = requests.get(f"{API_BASE.replace('/api/v1', '')}/health", timeout=10)
        if response.status_code == 200:
            print("  ✅ API is healthy")
        else:
            print(f"  ⚠️ API returned: {response.status_code}")
    except Exception as e:
        print(f"  ❌ API connection failed: {e}")
        return
    
    # Ask user what to do
    print("\n" + "=" * 60)
    choice = input("Register users with new passwords? (y/n): ").strip().lower()
    
    if choice == 'y':
        print("\n🔄 Registering users...")
        for user in data['users']:
            print(f"\n  Registering: {user['username']}")
            result = register_user(user['username'], user['email'])
            if result and not result.get('exists'):
                print(f"  ✅ Registered successfully")

if __name__ == "__main__":
    main()
