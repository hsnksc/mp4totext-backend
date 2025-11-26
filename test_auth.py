"""
Test authentication endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_register():
    """Test user registration"""
    print("\n" + "="*50)
    print("TEST 1: User Registration")
    print("="*50)
    
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "test123456",
        "full_name": "Test User"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=user_data)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json() if response.status_code == 201 else None


def test_login():
    """Test user login"""
    print("\n" + "="*50)
    print("TEST 2: User Login")
    print("="*50)
    
    login_data = {
        "username": "testuser",
        "password": "test123456"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"\n✅ Token received: {token[:50]}...")
        return token
    
    return None


def test_get_current_user(token):
    """Test getting current user info"""
    print("\n" + "="*50)
    print("TEST 3: Get Current User Info")
    print("="*50)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_unauthorized_access():
    """Test unauthorized access"""
    print("\n" + "="*50)
    print("TEST 4: Unauthorized Access (No Token)")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/api/v1/auth/me")
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_health():
    """Test health endpoint"""
    print("\n" + "="*50)
    print("TEST 5: Health Check")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/health")
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════╗
    ║   Authentication API Test Suite        ║
    ╚════════════════════════════════════════╝
    
    Testing endpoints:
    - POST /api/v1/auth/register
    - POST /api/v1/auth/login
    - GET /api/v1/auth/me
    - GET /health
    """)
    
    try:
        # Test 1: Register
        user = test_register()
        
        # Test 2: Login
        token = test_login()
        
        if token:
            # Test 3: Get current user with token
            test_get_current_user(token)
        
        # Test 4: Unauthorized access
        test_unauthorized_access()
        
        # Test 5: Health check
        test_health()
        
        print("\n" + "="*50)
        print("✅ All tests completed!")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
