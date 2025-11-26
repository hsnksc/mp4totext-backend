"""
Test file upload and transcription API
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

# Test credentials
USERNAME = "testuser"
PASSWORD = "test123456"


def login() -> str:
    """Login and get token"""
    print("\n" + "="*60)
    print("🔐 LOGGING IN")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Login successful")
        print(f"Token: {token[:50]}...")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Try to register if user doesn't exist
        print("\n📝 Registering new user...")
        reg_response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": USERNAME,
                "password": PASSWORD,
                "full_name": "Test User"
            }
        )
        
        if reg_response.status_code == 201:
            print("✅ Registration successful")
            # Try login again
            return login()
        else:
            print(f"❌ Registration failed: {reg_response.json()}")
            return None


def create_test_audio_file() -> Path:
    """Create a dummy audio file for testing"""
    test_file = Path("test_audio.mp3")
    
    # Create a small dummy file (not a real audio file, just for API testing)
    with open(test_file, "wb") as f:
        f.write(b"This is a test audio file content" * 100)
    
    print(f"\n📁 Created test file: {test_file.name} ({test_file.stat().st_size} bytes)")
    return test_file


def test_file_upload(token: str, test_file: Path):
    """Test file upload"""
    print("\n" + "="*60)
    print("📤 TEST 1: File Upload")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(test_file, "rb") as f:
        files = {"file": (test_file.name, f, "audio/mpeg")}
        response = requests.post(
            f"{BASE_URL}/api/v1/transcriptions/upload",
            headers=headers,
            files=files
        )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        return response.json()["file_id"]
    return None


def test_create_transcription(token: str, file_id: str):
    """Test transcription creation"""
    print("\n" + "="*60)
    print("🎙️ TEST 2: Create Transcription Job")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "file_id": file_id,
        "language": "tr",
        "use_speaker_recognition": True,
        "use_gemini_enhancement": False
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/transcriptions/",
        headers=headers,
        json=data
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        return response.json()["id"]
    return None


def test_get_transcription(token: str, transcription_id: int):
    """Test get transcription"""
    print("\n" + "="*60)
    print("📋 TEST 3: Get Transcription Status")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/transcriptions/{transcription_id}",
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_list_transcriptions(token: str):
    """Test list transcriptions"""
    print("\n" + "="*60)
    print("📚 TEST 4: List All Transcriptions")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BASE_URL}/api/v1/transcriptions/?page=1&page_size=10",
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_delete_transcription(token: str, transcription_id: int):
    """Test delete transcription"""
    print("\n" + "="*60)
    print("🗑️  TEST 5: Delete Transcription")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(
        f"{BASE_URL}/api/v1/transcriptions/{transcription_id}",
        headers=headers
    )
    
    print(f"\nStatus Code: {response.status_code}")
    if response.status_code == 204:
        print("✅ Transcription deleted successfully")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   File Upload & Transcription API Test Suite          ║
    ╚════════════════════════════════════════════════════════╝
    
    Testing endpoints:
    - POST /api/v1/transcriptions/upload
    - POST /api/v1/transcriptions/
    - GET /api/v1/transcriptions/{id}
    - GET /api/v1/transcriptions/
    - DELETE /api/v1/transcriptions/{id}
    """)
    
    try:
        # Step 1: Login
        token = login()
        if not token:
            print("❌ Cannot proceed without token")
            exit(1)
        
        # Step 2: Create test file
        test_file = create_test_audio_file()
        
        # Step 3: Upload file
        file_id = test_file_upload(token, test_file)
        if not file_id:
            print("❌ File upload failed")
            exit(1)
        
        # Step 4: Create transcription
        transcription_id = test_create_transcription(token, file_id)
        if not transcription_id:
            print("❌ Transcription creation failed")
            exit(1)
        
        # Step 5: Get transcription
        test_get_transcription(token, transcription_id)
        
        # Step 6: List transcriptions
        test_list_transcriptions(token)
        
        # Step 7: Delete transcription
        test_delete_transcription(token, transcription_id)
        
        # Cleanup
        test_file.unlink()
        print(f"\n🧹 Cleaned up test file: {test_file.name}")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
