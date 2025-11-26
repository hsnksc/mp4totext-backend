"""
Load Testing Script for MP4toText Backend
Test 1000 concurrent users uploading and transcribing files
"""

import asyncio
import aiohttp
import time
import random
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================
API_BASE_URL = "http://localhost:8002/api/v1"
TEST_USERS_COUNT = 1000
CONCURRENT_UPLOADS = 50  # Upload batch size
TEST_AUDIO_FILE = "test_audio.mp3"  # Small test file

# Test credentials (create these users first)
TEST_USERNAME = "loadtest_user_{}"
TEST_PASSWORD = "testpass123"

# =============================================================================
# TEST DATA
# =============================================================================
test_results = {
    'total_users': 0,
    'successful_logins': 0,
    'failed_logins': 0,
    'successful_uploads': 0,
    'failed_uploads': 0,
    'successful_transcriptions': 0,
    'failed_transcriptions': 0,
    'total_time': 0,
    'average_upload_time': 0,
    'average_transcription_time': 0,
    'errors': []
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def create_test_user(session: aiohttp.ClientSession, user_id: int) -> Dict[str, Any]:
    """Create a test user account"""
    username = TEST_USERNAME.format(user_id)
    
    try:
        async with session.post(
            f"{API_BASE_URL}/auth/register",
            json={
                "username": username,
                "email": f"test{user_id}@example.com",
                "password": TEST_PASSWORD
            },
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status in [200, 201]:
                data = await response.json()
                logger.info(f"✅ Created user: {username}")
                return {"success": True, "user_id": user_id, "username": username}
            else:
                logger.warning(f"⚠️ User {username} already exists or creation failed")
                return {"success": False, "user_id": user_id}
    except Exception as e:
        logger.error(f"❌ Failed to create user {username}: {e}")
        return {"success": False, "user_id": user_id, "error": str(e)}


async def login_user(session: aiohttp.ClientSession, user_id: int) -> Dict[str, Any]:
    """Login and get JWT token"""
    username = TEST_USERNAME.format(user_id)
    
    try:
        async with session.post(
            f"{API_BASE_URL}/auth/login",
            data={
                "username": username,
                "password": TEST_PASSWORD
            },
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                test_results['successful_logins'] += 1
                logger.debug(f"✅ Logged in: {username}")
                return {
                    "success": True,
                    "user_id": user_id,
                    "token": data.get("access_token"),
                    "username": username
                }
            else:
                test_results['failed_logins'] += 1
                return {"success": False, "user_id": user_id}
    except Exception as e:
        test_results['failed_logins'] += 1
        test_results['errors'].append(f"Login failed for {username}: {e}")
        return {"success": False, "user_id": user_id, "error": str(e)}


async def upload_file(
    session: aiohttp.ClientSession,
    token: str,
    user_id: int,
    file_path: str
) -> Dict[str, Any]:
    """Upload audio file for transcription"""
    start_time = time.time()
    
    try:
        # Create form data
        data = aiohttp.FormData()
        data.add_field(
            'file',
            open(file_path, 'rb'),
            filename=f'test_audio_{user_id}.mp3',
            content_type='audio/mpeg'
        )
        data.add_field('whisper_model', 'large-v3')
        data.add_field('enable_speaker_recognition', 'false')
        
        # Upload
        async with session.post(
            f"{API_BASE_URL}/transcriptions/upload",
            data=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=aiohttp.ClientTimeout(total=60)
        ) as response:
            upload_time = time.time() - start_time
            
            if response.status in [200, 201]:
                result = await response.json()
                test_results['successful_uploads'] += 1
                logger.info(f"📤 Uploaded file for user {user_id} in {upload_time:.2f}s")
                return {
                    "success": True,
                    "user_id": user_id,
                    "transcription_id": result.get("id"),
                    "upload_time": upload_time
                }
            else:
                test_results['failed_uploads'] += 1
                error_text = await response.text()
                test_results['errors'].append(f"Upload failed for user {user_id}: {error_text}")
                return {"success": False, "user_id": user_id, "upload_time": upload_time}
    
    except Exception as e:
        upload_time = time.time() - start_time
        test_results['failed_uploads'] += 1
        test_results['errors'].append(f"Upload exception for user {user_id}: {e}")
        return {"success": False, "user_id": user_id, "error": str(e), "upload_time": upload_time}


async def check_transcription_status(
    session: aiohttp.ClientSession,
    token: str,
    transcription_id: int
) -> Dict[str, Any]:
    """Check transcription processing status"""
    try:
        async with session.get(
            f"{API_BASE_URL}/transcriptions/{transcription_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                data = await response.json()
                status = data.get("status")
                
                if status == "completed":
                    test_results['successful_transcriptions'] += 1
                    return {"success": True, "status": status}
                elif status == "failed":
                    test_results['failed_transcriptions'] += 1
                    return {"success": False, "status": status}
                else:
                    return {"success": None, "status": status}  # Still processing
            else:
                return {"success": False, "status": "error"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# LOAD TEST SCENARIOS
# =============================================================================

async def simulate_user_session(session: aiohttp.ClientSession, user_id: int, file_path: str):
    """Simulate a complete user session: login → upload → wait for transcription"""
    
    # Step 1: Login
    login_result = await login_user(session, user_id)
    if not login_result.get("success"):
        logger.warning(f"⚠️ User {user_id} failed to login")
        return
    
    token = login_result["token"]
    
    # Step 2: Upload file
    await asyncio.sleep(random.uniform(0, 2))  # Random delay (0-2s)
    upload_result = await upload_file(session, token, user_id, file_path)
    
    if not upload_result.get("success"):
        logger.warning(f"⚠️ User {user_id} failed to upload")
        return
    
    transcription_id = upload_result["transcription_id"]
    
    # Step 3: Poll for transcription completion (optional)
    # In real scenario, users would check status later
    # For load test, we just record the upload success


async def run_load_test(num_users: int, file_path: str):
    """Run load test with specified number of users"""
    
    logger.info(f"🚀 Starting load test with {num_users} users")
    start_time = time.time()
    
    # Create HTTP session with connection pooling
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
    timeout = aiohttp.ClientTimeout(total=300)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # Create users in batches
        logger.info(f"📝 Creating {num_users} test users...")
        user_creation_tasks = [
            create_test_user(session, user_id)
            for user_id in range(1, num_users + 1)
        ]
        
        # Execute in batches of 50
        for i in range(0, len(user_creation_tasks), 50):
            batch = user_creation_tasks[i:i+50]
            await asyncio.gather(*batch)
            await asyncio.sleep(1)  # Small delay between batches
        
        logger.info(f"✅ User creation completed")
        
        # Simulate user sessions
        logger.info(f"🎬 Starting upload simulation for {num_users} users...")
        session_tasks = [
            simulate_user_session(session, user_id, file_path)
            for user_id in range(1, num_users + 1)
        ]
        
        # Execute in concurrent batches
        for i in range(0, len(session_tasks), CONCURRENT_UPLOADS):
            batch = session_tasks[i:i+CONCURRENT_UPLOADS]
            logger.info(f"📤 Processing batch {i//CONCURRENT_UPLOADS + 1}/{len(session_tasks)//CONCURRENT_UPLOADS + 1}")
            await asyncio.gather(*batch)
            await asyncio.sleep(0.5)  # Small delay between batches
    
    # Calculate results
    total_time = time.time() - start_time
    test_results['total_time'] = total_time
    test_results['total_users'] = num_users
    
    # Print results
    print("\n" + "="*80)
    print("LOAD TEST RESULTS")
    print("="*80)
    print(f"Total Users: {test_results['total_users']}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"\nLogin Results:")
    print(f"  ✅ Successful: {test_results['successful_logins']}")
    print(f"  ❌ Failed: {test_results['failed_logins']}")
    print(f"\nUpload Results:")
    print(f"  ✅ Successful: {test_results['successful_uploads']}")
    print(f"  ❌ Failed: {test_results['failed_uploads']}")
    print(f"\nTranscription Results:")
    print(f"  ✅ Completed: {test_results['successful_transcriptions']}")
    print(f"  ❌ Failed: {test_results['failed_transcriptions']}")
    
    if test_results['errors']:
        print(f"\nErrors ({len(test_results['errors'])} total):")
        for error in test_results['errors'][:10]:  # Show first 10
            print(f"  - {error}")
    
    # Calculate metrics
    success_rate = (test_results['successful_uploads'] / test_results['total_users'] * 100) if test_results['total_users'] > 0 else 0
    throughput = test_results['successful_uploads'] / total_time if total_time > 0 else 0
    
    print(f"\nMetrics:")
    print(f"  Success Rate: {success_rate:.2f}%")
    print(f"  Throughput: {throughput:.2f} uploads/second")
    print(f"  Average Time per User: {total_time/num_users:.2f}s")
    print("="*80)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the load test"""
    
    # Check if test audio file exists
    if not Path(TEST_AUDIO_FILE).exists():
        logger.error(f"❌ Test audio file not found: {TEST_AUDIO_FILE}")
        logger.info("📝 Create a small MP3 file for testing")
        return
    
    # Run load test
    asyncio.run(run_load_test(TEST_USERS_COUNT, TEST_AUDIO_FILE))


if __name__ == "__main__":
    main()
