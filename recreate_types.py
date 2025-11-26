#!/usr/bin/env python3
"""
Recreate all TypeScript types with proper exports
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

# Auth types
AUTH_TYPES = """export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
}
"""

# Transcription types
TRANSCRIPTION_TYPES = """export interface Transcription {
  id: number;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  text?: string;
  enhanced_text?: string;
  summary?: string;
  language?: string;
  duration?: number;
  file_size: number;
  created_at: string;
  updated_at: string;
}

export interface Speaker {
  id: string;
  name: string;
}

export interface Segment {
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}
"""

print("🔧 TypeScript types yeniden oluşturuluyor...\n")

# Create types directory if not exists
types_dir = os.path.join(WEB_SRC, "types")
os.makedirs(types_dir, exist_ok=True)

# Write auth.ts
auth_path = os.path.join(types_dir, "auth.ts")
with open(auth_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(AUTH_TYPES)
print(f"✅ {auth_path}")

# Write transcription.ts
trans_path = os.path.join(types_dir, "transcription.ts")
with open(trans_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(TRANSCRIPTION_TYPES)
print(f"✅ {trans_path}")

print("\n📍 Tüm type'lar export edildi!")
print("\nExported from auth.ts:")
print("  • LoginRequest")
print("  • RegisterRequest")
print("  • AuthResponse")
print("  • User")
print("\nExported from transcription.ts:")
print("  • Transcription")
print("  • Speaker")
print("  • Segment")
print("  • UploadProgress")
