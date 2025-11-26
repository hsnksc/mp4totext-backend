#!/usr/bin/env python3
"""Test Together AI Custom Prompt API with authentication"""
import requests
import json

BASE_URL = "http://localhost:8002/api/v1"

print("=" * 60)
print("🔐 Step 1: Login")
print("=" * 60)

# Login
login_data = {
    "username": "testuser",
    "password": "testpass123"
}

try:
    login_response = requests.post(
        f"{BASE_URL}/auth/login",
        json=login_data
    )
    login_response.raise_for_status()
    token = login_response.json()["access_token"]
    print(f"✅ Login successful! Token: {token[:20]}...")
except Exception as e:
    print(f"❌ Login failed: {e}")
    exit(1)

print(f"\n{'=' * 60}")
print("🚀 Step 2: Test Custom Prompt API with Together AI")
print("=" * 60)

# Test custom prompt
transcription_id = 92
url = f"{BASE_URL}/transcriptions/{transcription_id}/apply-custom-prompt"

headers = {
    "Authorization": f"Bearer {token}"
}

# Form data
form_data = {
    "custom_prompt": "Make this text more professional.",
    "ai_provider": "together",
    "use_together": "true",
    "language": "English"
}

print(f"\n📋 Request Details:")
print(f"  URL: {url}")
print(f"  Form Data: {form_data}")

try:
    response = requests.post(
        url,
        headers=headers,
        data=form_data  # multipart/form-data
    )
    
    print(f"\n📊 Response:")
    print(f"  Status Code: {response.status_code}")
    print(f"  Content Type: {response.headers.get('Content-Type', 'N/A')}")
    
    if response.status_code == 200:
        print(f"\n✅ SUCCESS!")
        result = response.json()
        print(f"\n📄 Response Data (keys): {list(result.keys())}")
        
        # Print custom_prompt_result if exists
        if 'custom_prompt_result' in result:
            cpr = result['custom_prompt_result']
            print(f"\n✨ Custom Prompt Result:")
            print(f"  - Processed Text (first 200 chars): {cpr.get('processed_text', '')[:200]}...")
            print(f"  - Provider: {cpr.get('provider', 'N/A')}")
            print(f"  - Model: {cpr.get('model_used', 'N/A')}")
            print(f"  - Language: {cpr.get('language', 'N/A')}")
    else:
        print(f"\n❌ ERROR!")
        print(f"\nResponse Body:")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ Request failed: {e}")
    print(f"\nException type: {type(e).__name__}")
    
    import traceback
    print(f"\n🔍 Full Traceback:")
    traceback.print_exc()

print(f"\n{'=' * 60}")
