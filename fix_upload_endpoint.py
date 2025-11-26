import os

web_dir = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web"
service_file = os.path.join(web_dir, "src", "services", "transcriptionService.ts")

content = """import axios from 'axios';
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

    const response = await api.post<Transcription>(ENDPOINTS.UPLOAD, formData, {
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

with open(service_file, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ transcriptionService.ts düzeltildi!")
print("   • ENDPOINTS.TRANSCRIPTIONS -> ENDPOINTS.UPLOAD")
print("   • Upload endpoint artık doğru: /api/v1/transcriptions/upload")
print("\n🔄 Vite dev server değişikliği otomatik algılayacak")
