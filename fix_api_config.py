#!/usr/bin/env python3
"""
API config dosyasını düzelt
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

# Fixed API config
API_CONFIG = """export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000',
  API_V1: 'http://localhost:8000/api/v1',
};

export const ENDPOINTS = {
  // Auth endpoints
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  PROFILE: '/auth/me',
  
  // Transcription endpoints
  TRANSCRIPTIONS: '/transcriptions',
  UPLOAD: '/transcriptions/upload',
};
"""

print("🔧 API config dosyası düzeltiliyor...\n")

config_path = os.path.join(WEB_SRC, "config", "api.ts")
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, "w", encoding="utf-8") as f:
    f.write(API_CONFIG)

print("✅ config/api.ts düzeltildi!")
print("\n📍 Tanımlanan Endpoint'ler:")
print("   /auth/login")
print("   /auth/register")
print("   /auth/me")
print("   /transcriptions")
print("   /transcriptions/upload")
