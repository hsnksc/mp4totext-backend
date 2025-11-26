#!/usr/bin/env python3
"""
authService.ts düzeltmesi - JSON format için
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

AUTH_SERVICE = """import axios from 'axios';
import { API_CONFIG, ENDPOINTS } from '../config/api';
import type { User, LoginRequest, RegisterRequest, AuthResponse } from '../types/auth';

const api = axios.create({
  baseURL: API_CONFIG.API_V1,
});

export const authService = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    // Backend expects JSON, not form data
    const response = await axios.post<AuthResponse>(
      `${API_CONFIG.API_V1}${ENDPOINTS.LOGIN}`,
      {
        username: data.username,
        password: data.password,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await axios.post<AuthResponse>(
      `${API_CONFIG.API_V1}${ENDPOINTS.REGISTER}`,
      data,
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    return response.data;
  },

  getProfile: async (token: string): Promise<User> => {
    const response = await axios.get<User>(
      `${API_CONFIG.API_V1}${ENDPOINTS.PROFILE}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('token');
  },
};
"""

print("🔧 authService.ts düzeltiliyor...\n")

service_path = os.path.join(WEB_SRC, "services", "authService.ts")
with open(service_path, "w", encoding="utf-8") as f:
    f.write(AUTH_SERVICE)

print("✅ services/authService.ts düzeltildi!")
print("\n📍 Değişiklikler:")
print("   • Login request JSON formatında gönderiliyor")
print("   • Content-Type: application/json header'ı eklendi")
print("   • Form data yerine JSON kullanıldı")
