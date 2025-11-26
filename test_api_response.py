import requests
import json

# Login to get token (OAuth2 form data format)
login_response = requests.post(
    "http://localhost:8002/api/v1/auth/login",
    data={"username": "testuser", "password": "Test1234!"},
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"✅ Login successful! Token: {token[:20]}...")
    
    # Get transcription
    headers = {"Authorization": f"Bearer {token}"}
    transcription_response = requests.get(
        "http://localhost:8002/api/v1/transcriptions/2",
        headers=headers
    )
    
    if transcription_response.status_code == 200:
        data = transcription_response.json()
        print("\n=== API RESPONSE ===")
        print(f"ID: {data.get('id')}")
        print(f"Status: {data.get('status')}")
        print(f"Gemini Status: {data.get('gemini_status', 'NOT IN RESPONSE')}")
        print(f"\nHas 'enhanced_text' field: {'enhanced_text' in data}")
        print(f"Has 'summary' field: {'summary' in data}")
        
        if 'enhanced_text' in data:
            print(f"\n✨ Enhanced Text (first 100 chars):\n{data['enhanced_text'][:100] if data['enhanced_text'] else 'NULL'}")
        else:
            print("\n❌ 'enhanced_text' field NOT in response!")
            
        if 'summary' in data:
            print(f"\n📊 Summary (first 100 chars):\n{data['summary'][:100] if data['summary'] else 'NULL'}")
        else:
            print("\n❌ 'summary' field NOT in response!")
            
        print(f"\n=== ALL FIELDS IN RESPONSE ===")
        print(json.dumps(list(data.keys()), indent=2))
    else:
        print(f"❌ Failed to get transcription: {transcription_response.status_code}")
        print(transcription_response.text)
else:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
