"""
Create Test Users for Concurrent Testing
Otomatik olarak 3 test kullanıcısı oluşturur
"""

import requests
import json

API_BASE_URL = "http://localhost:8002/api/v1"

TEST_USERS = [
    {"username": "user1", "email": "user1@test.com", "password": "password1"},
    {"username": "user2", "email": "user2@test.com", "password": "password2"},
    {"username": "user3", "email": "user3@test.com", "password": "password3"},
]


def create_user(username: str, email: str, password: str):
    """Kullanıcı oluştur"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            },
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ User created: {username}")
            return True
        elif response.status_code == 400:
            error = response.json().get("detail", "")
            if "already exists" in str(error).lower():
                print(f"⚠️ User already exists: {username}")
                return True
            else:
                print(f"❌ Failed to create {username}: {error}")
                return False
        else:
            print(f"❌ Failed to create {username}: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - Is backend running?")
        print(f"   Start backend: python run.py")
        return False
    except Exception as e:
        print(f"❌ Error creating {username}: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("👥 Creating Test Users")
    print("="*60)
    print(f"API: {API_BASE_URL}")
    print(f"Users to create: {len(TEST_USERS)}")
    print("="*60)
    print()
    
    success_count = 0
    
    for user in TEST_USERS:
        if create_user(user["username"], user["email"], user["password"]):
            success_count += 1
    
    print()
    print("="*60)
    print(f"✅ Successfully created/verified: {success_count}/{len(TEST_USERS)} users")
    print("="*60)
    
    if success_count == len(TEST_USERS):
        print("\n🎉 All users ready!")
        print("\n📝 Next steps:")
        print("   1. Make sure Celery worker is running: ./start_celery.ps1")
        print("   2. Run concurrent test: python test_concurrent_users.py")
    else:
        print("\n⚠️ Some users could not be created")
        print("   Check if backend is running: python run.py")


if __name__ == "__main__":
    main()
