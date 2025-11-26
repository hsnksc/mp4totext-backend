#!/usr/bin/env python3
"""
transcriptionService.ts ve App.tsx güncellemesi
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

# Update transcriptionService.ts with correct method names
SERVICE_FILE = """import axios from 'axios';
import { API_CONFIG, ENDPOINTS } from '../config/api';
import type { Transcription, UploadProgress } from '../types/transcription';

const api = axios.create({
  baseURL: API_CONFIG.API_V1,
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const transcriptionService = {
  // Upload file
  upload: async (file: File, onProgress?: (progress: UploadProgress) => void): Promise<Transcription> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Transcription>(ENDPOINTS.TRANSCRIPTIONS, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage,
          });
        }
      },
    });

    return response.data;
  },

  // Get single transcription by ID
  getById: async (id: number): Promise<Transcription> => {
    const response = await api.get<Transcription>(`${ENDPOINTS.TRANSCRIPTIONS}/${id}`);
    return response.data;
  },

  // Get all transcriptions with pagination
  getAll: async (page: number = 1, perPage: number = 10, status?: string): Promise<Transcription[]> => {
    const params: any = { page, per_page: perPage };
    if (status) params.status = status;

    const response = await api.get<Transcription[]>(ENDPOINTS.TRANSCRIPTIONS, { params });
    return response.data;
  },

  // Delete transcription
  delete: async (id: number): Promise<void> => {
    await api.delete(`${ENDPOINTS.TRANSCRIPTIONS}/${id}`);
  },

  // Download transcription text
  downloadText: async (id: number, format: 'txt' | 'json' | 'srt'): Promise<Blob> => {
    const response = await api.get(`${ENDPOINTS.TRANSCRIPTIONS}/${id}/download`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  },
};
"""

# Update App.tsx with all routes
APP_FILE = """import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { TranscriptionsPage } from './pages/TranscriptionsPage';
import { TranscriptionDetailPage } from './pages/TranscriptionDetailPage';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/upload" 
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/transcriptions" 
            element={
              <ProtectedRoute>
                <TranscriptionsPage />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/transcriptions/:id" 
            element={
              <ProtectedRoute>
                <TranscriptionDetailPage />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
"""

print("🔧 Service ve Route dosyaları güncelleniyor...\n")

# Write transcriptionService.ts
service_path = os.path.join(WEB_SRC, "services", "transcriptionService.ts")
os.makedirs(os.path.dirname(service_path), exist_ok=True)
with open(service_path, "w", encoding="utf-8") as f:
    f.write(SERVICE_FILE)
print("✅ services/transcriptionService.ts")

# Write App.tsx
app_path = os.path.join(WEB_SRC, "App.tsx")
with open(app_path, "w", encoding="utf-8") as f:
    f.write(APP_FILE)
print("✅ App.tsx")

print("\n✅ Tüm güncellemeler tamamlandı!")
print("\n📍 Eklenen Route'lar:")
print("   /dashboard          → Dashboard")
print("   /upload             → Dosya Yükleme")
print("   /transcriptions     → Transkript Listesi")
print("   /transcriptions/:id → Transkript Detayı")
