"""
WebSocket Full Flow Test Script
Tests the complete workflow: Register → Login → Upload → Process with WebSocket
"""

import asyncio
import socketio
import requests
import json
from pathlib import Path
import time

# Configuration
BASE_URL = "http://localhost:8000"
WS_URL = "http://localhost:8000/ws"

# Test credentials
TEST_USER = {
    "email": "websocket_test@example.com",
    "username": "websocket_tester",
    "password": "TestPassword123!",
    "full_name": "WebSocket Test User"
}

# Colors for console output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_step(step_num, message):
    """Print formatted step"""
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Step {step_num}: {message}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}\n")


def print_success(message):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")


async def test_websocket_flow():
    """Complete WebSocket test flow"""
    
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}🧪 WebSocket Full Flow Test{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    access_token = None
    user_id = None
    transcription_id = None
    file_id = None
    
    try:
        # Step 1: Register or Login
        print_step(1, "Authentication")
        
        # Try to register
        print_info("Attempting to register new user...")
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=TEST_USER
        )
        
        if response.status_code == 200:
            data = response.json()
            access_token = data["access_token"]
            user_id = data["user"]["id"]
            print_success(f"Registered successfully! User ID: {user_id}")
        elif response.status_code == 400:
            # User already exists, try login
            print_info("User exists, logging in...")
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                data={
                    "username": TEST_USER["username"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data["access_token"]
                user_id = data["user"]["id"]
                print_success(f"Logged in successfully! User ID: {user_id}")
            else:
                print_error(f"Login failed: {response.text}")
                return
        else:
            print_error(f"Registration failed: {response.text}")
            return
        
        # Headers for authenticated requests
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Step 2: Find or create a test audio file
        print_step(2, "Prepare Test Audio File")
        
        # Check for existing test files in desktop app directory
        desktop_app_dir = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext")
        test_files = [
            desktop_app_dir / "test.mp3",
            desktop_app_dir / "sample.mp3",
            desktop_app_dir / "audio.mp3",
            desktop_app_dir / "test.wav",
        ]
        
        audio_file_path = None
        for test_file in test_files:
            if test_file.exists():
                audio_file_path = test_file
                print_success(f"Found test file: {audio_file_path.name}")
                break
        
        if not audio_file_path:
            print_error("No test audio file found!")
            print_info("Please place a test.mp3 or sample.mp3 file in:")
            print_info(str(desktop_app_dir))
            return
        
        # Step 3: Upload file
        print_step(3, "Upload Audio File")
        
        with open(audio_file_path, "rb") as f:
            files = {"file": (audio_file_path.name, f, "audio/mpeg")}
            response = requests.post(
                f"{BASE_URL}/api/v1/transcriptions/upload",
                headers=headers,
                files=files
            )
        
        if response.status_code == 200:
            data = response.json()
            file_id = data["id"]
            print_success(f"File uploaded! File ID: {file_id}")
            print_info(f"Filename: {data['filename']}")
            print_info(f"Size: {data['file_size']} bytes")
        else:
            print_error(f"Upload failed: {response.text}")
            return
        
        # Step 4: Create transcription
        print_step(4, "Create Transcription")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/transcriptions/",
            headers=headers,
            json={
                "file_id": file_id,
                "language": "tr",
                "speaker_recognition": True
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            transcription_id = data["id"]
            print_success(f"Transcription created! ID: {transcription_id}")
            print_info(f"Status: {data['status']}")
        else:
            print_error(f"Transcription creation failed: {response.text}")
            return
        
        # Step 5: Setup WebSocket connection
        print_step(5, "Connect to WebSocket")
        
        sio = socketio.AsyncClient()
        progress_updates = []
        completed_data = None
        error_data = None
        
        @sio.event
        async def connect():
            print_success("Connected to WebSocket!")
            print_info(f"Session ID: {sio.sid}")
        
        @sio.event
        async def disconnect():
            print_info("Disconnected from WebSocket")
        
        @sio.event
        async def progress(data):
            """Handle progress updates"""
            progress_updates.append(data)
            transcription_id = data.get('transcription_id')
            progress = data.get('progress', 0)
            status = data.get('status', 'unknown')
            message = data.get('message', '')
            
            bar_length = 30
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"{Colors.OKCYAN}Progress [{bar}] {progress}% - {status}{Colors.ENDC}")
            if message:
                print(f"  {Colors.OKCYAN}└─ {message}{Colors.ENDC}")
        
        @sio.event
        async def completed(data):
            """Handle completion"""
            nonlocal completed_data
            completed_data = data
            print_success("Transcription completed!")
            result = data.get('result', {})
            print_info(f"Text length: {result.get('text_length', 0)} chars")
            print_info(f"Language: {result.get('language', 'unknown')}")
            print_info(f"Speakers: {result.get('speaker_count', 0)}")
            print_info(f"Processing time: {result.get('processing_time', 0):.2f}s")
        
        @sio.event
        async def error(data):
            """Handle errors"""
            nonlocal error_data
            error_data = data
            error_msg = data.get('error', 'Unknown error')
            print_error(f"Transcription error: {error_msg}")
        
        # Connect to WebSocket
        try:
            await sio.connect(
                WS_URL,
                transports=['websocket'],
                auth={'user_id': user_id}
            )
        except Exception as e:
            print_error(f"WebSocket connection failed: {e}")
            return
        
        # Step 6: Subscribe to transcription updates
        print_step(6, "Subscribe to Transcription")
        
        await sio.emit('subscribe', {
            'transcription_id': transcription_id
        })
        print_success(f"Subscribed to transcription {transcription_id}")
        
        # Step 7: Start processing
        print_step(7, "Start Processing with Real-time Updates")
        
        print_info("Starting transcription process...")
        response = requests.post(
            f"{BASE_URL}/api/v1/transcriptions/{transcription_id}/process",
            headers=headers
        )
        
        if response.status_code != 200:
            print_error(f"Processing failed: {response.text}")
            await sio.disconnect()
            return
        
        print_success("Processing started!")
        print_info("Waiting for real-time updates via WebSocket...\n")
        
        # Wait for completion (timeout after 5 minutes)
        timeout = 300
        start_time = time.time()
        
        while not completed_data and not error_data:
            await asyncio.sleep(0.5)
            
            if time.time() - start_time > timeout:
                print_error("Timeout waiting for completion")
                break
        
        # Step 8: Verify results
        print_step(8, "Verify Results")
        
        # Get final transcription data
        response = requests.get(
            f"{BASE_URL}/api/v1/transcriptions/{transcription_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Final transcription data retrieved:")
            print_info(f"Status: {data['status']}")
            print_info(f"Language: {data['language']}")
            print_info(f"Text preview: {data['text'][:200]}..." if data['text'] else "No text")
        
        print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Progress Updates Received: {len(progress_updates)}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}\n")
        
        for i, update in enumerate(progress_updates, 1):
            print(f"  {i}. Progress: {update['progress']}% - {update['status']}")
        
        # Disconnect
        await sio.disconnect()
        
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}✅ Test Completed Successfully!{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
        
    except Exception as e:
        print_error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        🧪 WebSocket Full Flow Test                         ║
    ║                                                            ║
    ║  This test will:                                          ║
    ║  1. Register/Login a test user                            ║
    ║  2. Upload an audio file                                  ║
    ║  3. Create a transcription                                ║
    ║  4. Connect to WebSocket                                  ║
    ║  5. Subscribe to transcription updates                    ║
    ║  6. Process transcription with real-time progress         ║
    ║  7. Verify final results                                  ║
    ║                                                            ║
    ║  Make sure backend server is running at localhost:8000    ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(test_websocket_flow())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
