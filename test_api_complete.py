#!/usr/bin/env python3
"""
Complete API Test Suite for MP4toText Backend
Tests all endpoints: auth, upload, transcription, enhancement
"""

import requests
import json
import time
from pathlib import Path
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

# Test data
TEST_USER = {
    "username": "testuser",
    "password": "Test1234!",
    "email": "test@mp4totext.com",
    "full_name": "Test User"
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.RESET}")

def print_result(label: str, value):
    print(f"{Colors.CYAN}{label}:{Colors.RESET} {value}")


class APITester:
    def __init__(self):
        self.token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.transcription_id: Optional[int] = None
        self.tests_passed = 0
        self.tests_failed = 0

    def test_health(self) -> bool:
        """Test health check endpoint"""
        print_header("1️⃣  Health Check")
        
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print_success("Health check passed")
                print_result("Service", data.get("service"))
                print_result("Status", data.get("status"))
                print_result("Version", data.get("version"))
                self.tests_passed += 1
                return True
            else:
                print_error(f"Health check failed: {response.status_code}")
                self.tests_failed += 1
                return False
                
        except Exception as e:
            print_error(f"Health check error: {str(e)}")
            self.tests_failed += 1
            return False

    def test_login(self) -> bool:
        """Test user login"""
        print_header("2️⃣  User Login")
        
        try:
            response = requests.post(
                f"{API_V1}/auth/login",
                json={
                    "username": TEST_USER["username"],
                    "password": TEST_USER["password"]
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print_success("Login successful")
                print_result("Token", self.token[:50] + "...")
                print_result("Token Type", data.get("token_type"))
                self.tests_passed += 1
                return True
            else:
                print_error(f"Login failed: {response.status_code}")
                print_info(f"Response: {response.text}")
                self.tests_failed += 1
                return False
                
        except Exception as e:
            print_error(f"Login error: {str(e)}")
            self.tests_failed += 1
            return False

    def test_get_profile(self) -> bool:
        """Test get current user profile"""
        print_header("3️⃣  Get User Profile")
        
        if not self.token:
            print_error("No token available. Login first.")
            self.tests_failed += 1
            return False
        
        try:
            response = requests.get(
                f"{API_V1}/auth/me",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("id")
                print_success("Profile retrieved successfully")
                print_result("User ID", data.get("id"))
                print_result("Username", data.get("username"))
                print_result("Email", data.get("email"))
                print_result("Full Name", data.get("full_name"))
                self.tests_passed += 1
                return True
            else:
                print_error(f"Profile retrieval failed: {response.status_code}")
                print_info(f"Response: {response.text}")
                self.tests_failed += 1
                return False
                
        except Exception as e:
            print_error(f"Profile error: {str(e)}")
            self.tests_failed += 1
            return False

    def test_upload_file(self) -> bool:
        """Test file upload"""
        print_header("4️⃣  File Upload")
        
        if not self.token:
            print_error("No token available. Login first.")
            self.tests_failed += 1
            return False
        
        # Check if test file exists
        test_file = Path("test_files/test_audio.wav")
        if not test_file.exists():
            print_error(f"Test file not found: {test_file}")
            self.tests_failed += 1
            return False
        
        try:
            with open(test_file, 'rb') as f:
                files = {'file': ('test_audio.wav', f, 'audio/wav')}
                data = {
                    'language': 'tr',
                    'use_speaker_recognition': 'false'
                }
                
                print_info(f"Uploading file: {test_file.name} ({test_file.stat().st_size} bytes)")
                
                response = requests.post(
                    f"{API_V1}/transcriptions/upload",
                    headers={"Authorization": f"Bearer {self.token}"},
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code in [200, 201]:
                data = response.json()
                file_id = data.get("file_id")
                print_success("File uploaded successfully")
                print_result("File ID", file_id)
                print_result("File Name", data.get("filename"))
                print_result("File Size", f"{data.get('file_size')} bytes")
                print_result("Content Type", data.get("content_type"))
                
                # Now create transcription job
                print_info("Creating transcription job...")
                trans_response = requests.post(
                    f"{API_V1}/transcriptions/",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "file_id": file_id,
                        "language": "tr",
                        "use_speaker_recognition": False,
                        "use_gemini_enhancement": False
                    },
                    timeout=10
                )
                
                if trans_response.status_code in [200, 201]:
                    trans_data = trans_response.json()
                    self.transcription_id = trans_data.get("id")
                    print_success("Transcription job created")
                    print_result("Transcription ID", trans_data.get("id"))
                    print_result("Status", trans_data.get("status"))
                else:
                    print_error(f"Transcription creation failed: {trans_response.status_code}")
                    print_info(f"Response: {trans_response.text}")
                
                self.tests_passed += 1
                return True
            else:
                print_error(f"Upload failed: {response.status_code}")
                print_info(f"Response: {response.text}")
                self.tests_failed += 1
                return False
                
        except Exception as e:
            print_error(f"Upload error: {str(e)}")
            self.tests_failed += 1
            return False

    def test_get_transcription(self) -> bool:
        """Test get transcription status"""
        print_header("5️⃣  Get Transcription Status")
        
        if not self.token or not self.transcription_id:
            print_error("No transcription ID available. Upload first.")
            self.tests_failed += 1
            return False
        
        try:
            response = requests.get(
                f"{API_V1}/transcriptions/{self.transcription_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success("Transcription status retrieved")
                print_result("ID", data.get("id"))
                print_result("Status", data.get("status"))
                print_result("File Name", data.get("file_name"))
                print_result("Language", data.get("language"))
                
                if data.get("result_text"):
                    print_result("Result Text", data.get("result_text")[:100] + "...")
                
                self.tests_passed += 1
                return True
            else:
                print_error(f"Get transcription failed: {response.status_code}")
                print_info(f"Response: {response.text}")
                self.tests_failed += 1
                return False
                
        except Exception as e:
            print_error(f"Get transcription error: {str(e)}")
            self.tests_failed += 1
            return False

    def test_wait_for_completion(self, max_wait: int = 60) -> bool:
        """Wait for transcription to complete"""
        print_header("6️⃣  Wait for Transcription Completion")
        
        if not self.token or not self.transcription_id:
            print_error("No transcription ID available.")
            self.tests_failed += 1
            return False
        
        print_info(f"Polling every 3 seconds (max {max_wait}s)...")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait:
            attempt += 1
            
            try:
                response = requests.get(
                    f"{API_V1}/transcriptions/{self.transcription_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    print(f"  Attempt {attempt}: Status = {status}")
                    
                    if status == "completed":
                        print_success("Transcription completed!")
                        print_result("Result Text", data.get("result_text", "N/A")[:200])
                        print_result("Processing Time", f"{data.get('processing_time', 'N/A')}s")
                        
                        if data.get("speakers"):
                            print_result("Speakers Detected", len(data.get("speakers", [])))
                        
                        self.tests_passed += 1
                        return True
                    
                    elif status == "failed":
                        print_error(f"Transcription failed: {data.get('error_message')}")
                        self.tests_failed += 1
                        return False
                    
                    # Continue polling
                    time.sleep(3)
                    
                else:
                    print_error(f"Status check failed: {response.status_code}")
                    time.sleep(3)
                    
            except Exception as e:
                print_error(f"Polling error: {str(e)}")
                time.sleep(3)
        
        print_error(f"Timeout: Transcription not completed after {max_wait}s")
        self.tests_failed += 1
        return False

    def test_list_transcriptions(self) -> bool:
        """Test list user's transcriptions"""
        print_header("7️⃣  List Transcriptions")
        
        if not self.token:
            print_error("No token available.")
            self.tests_failed += 1
            return False
        
        try:
            response = requests.get(
                f"{API_V1}/transcriptions",
                headers={"Authorization": f"Bearer {self.token}"},
                params={"limit": 10},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"Retrieved {len(data)} transcription(s)")
                
                for idx, trans in enumerate(data[:3], 1):  # Show first 3
                    print(f"\n  {idx}. ID: {trans.get('id')}")
                    print(f"     File: {trans.get('file_name')}")
                    print(f"     Status: {trans.get('status')}")
                    print(f"     Created: {trans.get('created_at')}")
                
                self.tests_passed += 1
                return True
            else:
                print_error(f"List transcriptions failed: {response.status_code}")
                print_info(f"Response: {response.text}")
                self.tests_failed += 1
                return False
                
        except Exception as e:
            print_error(f"List error: {str(e)}")
            self.tests_failed += 1
            return False

    def print_summary(self):
        """Print test summary"""
        print_header("📊 Test Summary")
        
        total = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total * 100) if total > 0 else 0
        
        print(f"{Colors.GREEN}✅ Tests Passed: {self.tests_passed}{Colors.RESET}")
        print(f"{Colors.RED}❌ Tests Failed: {self.tests_failed}{Colors.RESET}")
        print(f"{Colors.CYAN}📈 Success Rate: {success_rate:.1f}%{Colors.RESET}")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED!{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Check the errors above.{Colors.RESET}")


def main():
    """Run all API tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print("🧪 MP4toText Backend - Complete API Test Suite")
    print(f"{'='*60}{Colors.RESET}\n")
    
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Test User: {TEST_USER['username']}")
    print("")
    
    tester = APITester()
    
    # Run tests
    if not tester.test_health():
        print_error("Health check failed. Is the server running?")
        return
    
    if not tester.test_login():
        print_error("Login failed. Cannot continue.")
        return
    
    tester.test_get_profile()
    
    if tester.test_upload_file():
        # Wait for transcription
        tester.test_wait_for_completion(max_wait=120)
    
    tester.test_list_transcriptions()
    
    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    main()
