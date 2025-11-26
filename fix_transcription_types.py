#!/usr/bin/env python3
"""
Fix Transcription type export
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

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

print("🔧 Transcription types düzeltiliyor...\n")

types_path = os.path.join(WEB_SRC, "types", "transcription.ts")
os.makedirs(os.path.dirname(types_path), exist_ok=True)

with open(types_path, "w", encoding="utf-8") as f:
    f.write(TRANSCRIPTION_TYPES)

print("✅ types/transcription.ts düzeltildi!")
print("\n📍 Export edilen tipler:")
print("   • Transcription")
print("   • Speaker")
print("   • Segment")
print("   • UploadProgress")
