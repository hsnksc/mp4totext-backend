import os

web_dir = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web"
service_file = os.path.join(web_dir, "src", "services", "transcriptionService.ts")

content = """import axios from 'axios';
import { API_CONFIG, ENDPOINTS } from '../config/api';
import type { Transcription, UploadProgress } from '../types';

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
  // Upload file and create transcription (2-step process)
  upload: async (file: File, onProgress?: (progress: UploadProgress) => void): Promise<Transcription> => {
    console.log('Step 1: Uploading file...', file.name);
    
    // Step 1: Upload file
    const formData = new FormData();
    formData.append('file', file);

    const uploadResponse = await api.post<{
      file_id: string;
      filename: string;
      file_size: number;
      content_type: string;
      message: string;
    }>(ENDPOINTS.UPLOAD, formData, {
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

    console.log('Step 1 complete. File ID:', uploadResponse.data.file_id);
    console.log('Step 2: Creating transcription...');

    // Step 2: Create transcription with file_id
    const transcriptionResponse = await api.post<Transcription>(ENDPOINTS.TRANSCRIPTIONS, {
      file_id: uploadResponse.data.file_id,
      language: null, // auto-detect
      use_speaker_recognition: false,
      use_gemini_enhancement: false,
    });

    console.log('Step 2 complete. Transcription created:', transcriptionResponse.data);

    return transcriptionResponse.data;
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
print("\n📍 Değişiklikler:")
print("   • Upload artık 2 adımlı:")
print("     1️⃣  POST /upload → file_id al")
print("     2️⃣  POST / → transcription oluştur")
print("   • Console.log'lar eklendi (debugging)")
print("   • Import path düzeltildi: '../types/transcription' → '../types'")
print("\n🔄 Vite HMR değişikliği otomatik algılayacak")
print("\n🎯 Şimdi tekrar dosya yükleyin!")
