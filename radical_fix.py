#!/usr/bin/env python3
"""
Radikal çözüm: Tüm yapıyı değiştir
1. transcription.ts -> index.ts (barrel export)
2. export type kullan
3. DashboardPage import'unu düzelt
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

# Step 1: Create types/index.ts with barrel exports
TYPES_INDEX = """// Auth types
export type { LoginRequest, RegisterRequest, AuthResponse, User } from './auth';

// Transcription types
export type { Transcription, Speaker, Segment, UploadProgress } from './transcription';
"""

# Step 2: Update transcription.ts with export type
TRANSCRIPTION_TS = """export type Transcription = {
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
};

export type Speaker = {
  id: string;
  name: string;
};

export type Segment = {
  start: number;
  end: number;
  text: string;
  speaker?: string;
};

export type UploadProgress = {
  loaded: number;
  total: number;
  percentage: number;
};
"""

# Step 3: Update auth.ts with export type
AUTH_TS = """export type LoginRequest = {
  username: string;
  password: string;
};

export type RegisterRequest = {
  username: string;
  email: string;
  password: string;
  full_name?: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
};

export type User = {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
};
"""

print("🔧 RADİKAL ÇÖZÜM: Type yapısı değiştiriliyor...\n")

types_dir = os.path.join(WEB_SRC, "types")
os.makedirs(types_dir, exist_ok=True)

# Write index.ts (barrel export)
index_path = os.path.join(types_dir, "index.ts")
with open(index_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(TYPES_INDEX)
print(f"✅ {index_path} (barrel export)")

# Write transcription.ts
trans_path = os.path.join(types_dir, "transcription.ts")
with open(trans_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(TRANSCRIPTION_TS)
print(f"✅ {trans_path} (export type)")

# Write auth.ts
auth_path = os.path.join(types_dir, "auth.ts")
with open(auth_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(AUTH_TS)
print(f"✅ {auth_path} (export type)")

# Step 4: Update DashboardPage.tsx import
DASHBOARD_PAGE_HEAD = """import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types'; // CHANGED: barrel import + type keyword
import { Layout } from '../components/Layout';
"""

dashboard_path = os.path.join(WEB_SRC, "pages", "DashboardPage.tsx")
if os.path.exists(dashboard_path):
    with open(dashboard_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace first 5 lines (import section)
    lines = content.split("\n")
    # Keep everything after line 5
    rest = "\n".join(lines[5:])
    new_content = DASHBOARD_PAGE_HEAD.strip() + "\n" + rest
    
    with open(dashboard_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    print(f"✅ {dashboard_path} (import güncellendi)")

print("\n📍 Değişiklikler:")
print("   • types/index.ts oluşturuldu (barrel export)")
print("   • interface -> type değişti")
print("   • DashboardPage: '../types/transcription' -> '../types'")
print("   • 'import type' kullanıldı")
print("\n🔥 Bu çözüm KESINLIKLE çalışmalı!")
