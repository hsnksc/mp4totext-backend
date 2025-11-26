"""
Local Concurrent User Test
2-3 kullanıcı ile eşzamanlı transcription testi
"""

import asyncio
import aiohttp
import time
import json
from pathlib import Path

# =============================================================================
# CONFIG
# =============================================================================
API_BASE_URL = "http://localhost:8002/api/v1"

# Test kullanıcıları (önceden oluşturulmuş olmalı)
TEST_USERS = [
    {"username": "user1", "password": "password1"},
    {"username": "user2", "password": "password2"},
    {"username": "user3", "password": "password3"},
]

# Test audio dosyası (küçük bir MP3 dosyası)
TEST_AUDIO = "test_audio.mp3"  # Bu dosya backend klasöründe olmalı


# =============================================================================
# FUNCTIONS
# =============================================================================

async def login(session: aiohttp.ClientSession, username: str, password: str):
    """Login ve token al"""
    try:
        async with session.post(
            f"{API_BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                token = data.get("access_token")
                print(f"✅ {username} logged in")
                return token
            else:
                print(f"❌ {username} login failed: {response.status}")
                return None
    except Exception as e:
        print(f"❌ {username} login error: {e}")
        return None


async def upload_file(session: aiohttp.ClientSession, username: str, token: str, file_path: str):
    """Audio dosyası upload et"""
    try:
        # Form data oluştur
        data = aiohttp.FormData()
        data.add_field(
            'file',
            open(file_path, 'rb'),
            filename=f'{username}_test.mp3',
            content_type='audio/mpeg'
        )
        data.add_field('whisper_model', 'large-v3')
        data.add_field('enable_speaker_recognition', 'false')
        
        print(f"📤 {username} uploading file...")
        start_time = time.time()
        
        async with session.post(
            f"{API_BASE_URL}/transcriptions/upload",
            data=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            upload_time = time.time() - start_time
            
            if response.status in [200, 201]:
                result = await response.json()
                transcription_id = result.get("id")
                print(f"✅ {username} uploaded in {upload_time:.2f}s - Transcription ID: {transcription_id}")
                return transcription_id
            else:
                error_text = await response.text()
                print(f"❌ {username} upload failed: {error_text}")
                return None
                
    except Exception as e:
        print(f"❌ {username} upload error: {e}")
        return None


async def check_status(session: aiohttp.ClientSession, username: str, token: str, transcription_id: int):
    """Transcription durumunu kontrol et"""
    try:
        async with session.get(
            f"{API_BASE_URL}/transcriptions/{transcription_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                status = data.get("status")
                progress = data.get("progress", 0)
                
                if status == "completed":
                    print(f"✅ {username} - Transcription COMPLETED!")
                    return "completed"
                elif status == "processing":
                    print(f"⏳ {username} - Processing... ({progress}%)")
                    return "processing"
                elif status == "failed":
                    print(f"❌ {username} - Transcription FAILED")
                    return "failed"
                else:
                    print(f"📊 {username} - Status: {status}")
                    return status
            else:
                print(f"⚠️ {username} - Status check failed")
                return "error"
                
    except Exception as e:
        print(f"⚠️ {username} - Status check error: {e}")
        return "error"


async def user_session(session: aiohttp.ClientSession, user: dict, file_path: str):
    """Tek kullanıcının tüm işlemleri"""
    username = user["username"]
    password = user["password"]
    
    print(f"\n{'='*60}")
    print(f"👤 Starting session: {username}")
    print(f"{'='*60}")
    
    # 1. Login
    token = await login(session, username, password)
    if not token:
        print(f"❌ {username} - Session failed (login error)")
        return
    
    # 2. Upload
    await asyncio.sleep(1)  # Küçük delay
    transcription_id = await upload_file(session, username, token, file_path)
    if not transcription_id:
        print(f"❌ {username} - Session failed (upload error)")
        return
    
    print(f"✅ {username} - File uploaded, transcription queued (ID: {transcription_id})")
    print(f"   Worker will process this in background...")
    
    # 3. İlk status kontrolü (5 saniye sonra)
    await asyncio.sleep(5)
    status = await check_status(session, username, token, transcription_id)
    
    print(f"🎬 {username} - Initial status: {status}")


async def run_concurrent_test(users: list, file_path: str):
    """Tüm kullanıcıları eşzamanlı çalıştır"""
    
    print("\n" + "="*80)
    print("🚀 CONCURRENT USER TEST - MP4toText")
    print("="*80)
    print(f"📊 Test Configuration:")
    print(f"   Users: {len(users)}")
    print(f"   API: {API_BASE_URL}")
    print(f"   Test File: {file_path}")
    print("="*80)
    print("\n⚠️ Make sure:")
    print("   1. Backend is running (python run.py)")
    print("   2. Redis is running")
    print("   3. Celery worker is running (./start_celery.ps1)")
    print("   4. Test users are created")
    print("\n⏱️ Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    start_time = time.time()
    
    # HTTP session oluştur
    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Tüm kullanıcıları AYNI ANDA çalıştır
        tasks = [
            user_session(session, user, file_path)
            for user in users
        ]
        
        await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80)
    print(f"Total Time: {total_time:.2f}s")
    print(f"Users Tested: {len(users)}")
    print("\n📊 Check Flower UI for task details:")
    print("   http://localhost:5555")
    print("\n⏳ Transcriptions are processing in background...")
    print("   Check status in a few minutes via API or mobile app")
    print("="*80)


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Dosya kontrolü
    if not Path(TEST_AUDIO).exists():
        print(f"❌ Test file not found: {TEST_AUDIO}")
        print(f"📝 Please create a small MP3 file for testing")
        print(f"   You can use any short audio file (5-30 seconds)")
        return
    
    print("\n🎯 INSTRUCTIONS:")
    print("="*80)
    print("1. Create test users first (if not exists):")
    print("   curl -X POST http://localhost:8002/api/v1/auth/register \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"username\":\"user1\",\"email\":\"user1@test.com\",\"password\":\"password1\"}'")
    print()
    print("   Repeat for user2, user3...")
    print()
    print("2. Make sure all services are running:")
    print("   - Backend: python run.py")
    print("   - Redis: redis-server")
    print("   - Celery: ./start_celery.ps1")
    print()
    print("3. Run this test:")
    print("   python test_concurrent_users.py")
    print("="*80)
    
    input("\n✋ Press ENTER to start the test...")
    
    # Test'i çalıştır
    asyncio.run(run_concurrent_test(TEST_USERS, TEST_AUDIO))


if __name__ == "__main__":
    main()
