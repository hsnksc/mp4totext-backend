# 📱 MP4toText Frontend Entegrasyon Rehberi

## 🎯 Genel Bakış

MP4toText Backend API, React ve React Native uygulamalarınızdan kolayca kullanabilirsiniz. Bu rehber, authentication, file upload, ve WebSocket entegrasyonu için kod örnekleri içerir.

---

## 🔐 1. Authentication (JWT)

### Base Configuration

```typescript
// src/config/api.ts
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000',  // Production'da domain kullan
  API_VERSION: '/api/v1',
  ENDPOINTS: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    ME: '/auth/me',
    UPLOAD: '/transcriptions/upload',
    TRANSCRIPTIONS: '/transcriptions',
    WS_BASE: 'ws://localhost:8000/ws'
  }
};

export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${API_CONFIG.API_VERSION}${endpoint}`;
};
```

### Authentication Service

```typescript
// src/services/authService.ts
import axios from 'axios';
import { getApiUrl } from '../config/api';

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData extends LoginCredentials {
  email: string;
  full_name: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
}

class AuthService {
  private token: string | null = null;

  // Register new user
  async register(data: RegisterData): Promise<any> {
    const response = await axios.post(
      getApiUrl('/auth/register'),
      data
    );
    return response.data;
  }

  // Login and get token
  async login(credentials: LoginCredentials): Promise<string> {
    const response = await axios.post<AuthResponse>(
      getApiUrl('/auth/login'),
      credentials
    );
    
    this.token = response.data.access_token;
    
    // Save to local storage
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('auth_token', this.token);
    }
    
    return this.token;
  }

  // Get current user profile
  async getProfile() {
    const token = this.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await axios.get(
      getApiUrl('/auth/me'),
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    
    return response.data;
  }

  // Logout
  logout() {
    this.token = null;
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
  }

  // Get stored token
  getToken(): string | null {
    if (!this.token && typeof localStorage !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  // Check if authenticated
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }
}

export const authService = new AuthService();
```

---

## 📤 2. File Upload & Transcription

### React/React Native Upload Component

```typescript
// src/services/transcriptionService.ts
import axios, { AxiosProgressEvent } from 'axios';
import { authService } from './authService';
import { getApiUrl } from '../config/api';

interface UploadOptions {
  file: File | { uri: string; name: string; type: string };  // File for web, object for RN
  language?: string;
  use_speaker_recognition?: boolean;
  onProgress?: (progress: number) => void;
}

interface TranscriptionResponse {
  id: number;
  status: string;
  file_name: string;
  file_size: number;
  language: string;
  created_at: string;
}

class TranscriptionService {
  // Upload audio/video file
  async uploadFile(options: UploadOptions): Promise<TranscriptionResponse> {
    const { file, language = 'tr', use_speaker_recognition = false, onProgress } = options;
    
    const token = authService.getToken();
    if (!token) throw new Error('Not authenticated');

    // Create FormData
    const formData = new FormData();
    formData.append('file', file as any);
    formData.append('language', language);
    formData.append('use_speaker_recognition', String(use_speaker_recognition));

    // Upload with progress tracking
    const response = await axios.post<TranscriptionResponse>(
      getApiUrl('/transcriptions/upload'),
      formData,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent: AxiosProgressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        }
      }
    );

    return response.data;
  }

  // Get transcription status
  async getTranscription(id: number): Promise<any> {
    const token = authService.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await axios.get(
      getApiUrl(`/transcriptions/${id}`),
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    return response.data;
  }

  // Poll for completion
  async waitForCompletion(
    id: number,
    options: {
      pollInterval?: number;
      maxAttempts?: number;
      onProgress?: (status: string) => void;
    } = {}
  ): Promise<any> {
    const { pollInterval = 2000, maxAttempts = 60, onProgress } = options;
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const transcription = await this.getTranscription(id);
      
      if (onProgress) onProgress(transcription.status);

      if (transcription.status === 'completed') {
        return transcription;
      } else if (transcription.status === 'failed') {
        throw new Error(transcription.error_message || 'Transcription failed');
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error('Transcription timeout');
  }

  // Get user's transcription history
  async listTranscriptions(params: { skip?: number; limit?: number } = {}): Promise<any[]> {
    const token = authService.getToken();
    if (!token) throw new Error('Not authenticated');

    const response = await axios.get(
      getApiUrl('/transcriptions'),
      {
        headers: { Authorization: `Bearer ${token}` },
        params
      }
    );

    return response.data;
  }

  // Delete transcription
  async deleteTranscription(id: number): Promise<void> {
    const token = authService.getToken();
    if (!token) throw new Error('Not authenticated');

    await axios.delete(
      getApiUrl(`/transcriptions/${id}`),
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
  }
}

export const transcriptionService = new TranscriptionService();
```

### React Hook Example

```typescript
// src/hooks/useTranscription.ts
import { useState } from 'react';
import { transcriptionService } from '../services/transcriptionService';

export const useTranscription = () => {
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadAndTranscribe = async (file: File, language: string = 'tr') => {
    try {
      setUploading(true);
      setUploadProgress(0);
      setError(null);

      // Upload file
      const uploadResult = await transcriptionService.uploadFile({
        file,
        language,
        onProgress: setUploadProgress
      });

      setUploading(false);
      setProcessing(true);

      // Wait for transcription to complete
      const result = await transcriptionService.waitForCompletion(
        uploadResult.id,
        {
          onProgress: (status) => {
            console.log('Transcription status:', status);
          }
        }
      );

      setProcessing(false);
      return result;

    } catch (err: any) {
      setError(err.message || 'Upload failed');
      setUploading(false);
      setProcessing(false);
      throw err;
    }
  };

  return {
    uploadAndTranscribe,
    uploading,
    processing,
    uploadProgress,
    error
  };
};
```

### React Component Example

```tsx
// src/components/TranscriptionUpload.tsx
import React, { useState } from 'react';
import { useTranscription } from '../hooks/useTranscription';

export const TranscriptionUpload: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const { uploadAndTranscribe, uploading, processing, uploadProgress, error } = useTranscription();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      const transcriptionResult = await uploadAndTranscribe(selectedFile, 'tr');
      setResult(transcriptionResult);
      alert('Transkripsiyon tamamlandı!');
    } catch (err) {
      console.error('Upload error:', err);
    }
  };

  return (
    <div className="transcription-upload">
      <h2>📤 Ses/Video Yükle</h2>

      <input
        type="file"
        accept="audio/*,video/*"
        onChange={handleFileSelect}
        disabled={uploading || processing}
      />

      {selectedFile && (
        <div>
          <p>Seçilen: {selectedFile.name}</p>
          <button onClick={handleUpload} disabled={uploading || processing}>
            {uploading ? 'Yükleniyor...' : processing ? 'İşleniyor...' : 'Yükle'}
          </button>
        </div>
      )}

      {uploading && (
        <div className="progress-bar">
          <div style={{ width: `${uploadProgress}%` }}>
            {uploadProgress}%
          </div>
        </div>
      )}

      {processing && <p>⏳ Transkripsiyon işleniyor...</p>}

      {error && <p style={{ color: 'red' }}>❌ Hata: {error}</p>}

      {result && (
        <div className="result">
          <h3>✅ Sonuç:</h3>
          <p><strong>Metin:</strong> {result.result_text}</p>
          <p><strong>Dil:</strong> {result.language}</p>
          <p><strong>Durum:</strong> {result.status}</p>
        </div>
      )}
    </div>
  );
};
```

---

## 📡 3. WebSocket Real-time Updates

```typescript
// src/services/websocketService.ts
import { authService } from './authService';
import { API_CONFIG } from '../config/api';

type MessageHandler = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(clientId: string) {
    const token = authService.getToken();
    if (!token) {
      console.error('No auth token available');
      return;
    }

    const wsUrl = `${API_CONFIG.WS_BASE}/${clientId}?token=${token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('✅ WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (err) {
        console.error('WebSocket message parse error:', err);
      }
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('🔌 WebSocket disconnected');
      this.attemptReconnect(clientId);
    };
  }

  private attemptReconnect(clientId: string) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => this.connect(clientId), 3000);
    }
  }

  private handleMessage(data: any) {
    const { type } = data;
    const handlers = this.handlers.get(type) || [];
    handlers.forEach(handler => handler(data));
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type);
    if (handlers) {
      this.handlers.set(
        type,
        handlers.filter(h => h !== handler)
      );
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.handlers.clear();
  }
}

export const websocketService = new WebSocketService();
```

### React Hook for WebSocket

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useState } from 'react';
import { websocketService } from '../services/websocketService';

export const useWebSocket = (clientId: string) => {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);

  useEffect(() => {
    // Connect
    websocketService.connect(clientId);
    setConnected(true);

    // Listen for progress updates
    const handleProgress = (data: any) => {
      console.log('Progress update:', data);
      setMessages(prev => [...prev, data]);
    };

    websocketService.on('progress', handleProgress);
    websocketService.on('completed', handleProgress);
    websocketService.on('error', handleProgress);

    // Cleanup
    return () => {
      websocketService.off('progress', handleProgress);
      websocketService.disconnect();
      setConnected(false);
    };
  }, [clientId]);

  return {
    connected,
    messages,
    send: (data: any) => websocketService.send(data)
  };
};
```

---

## 📱 4. React Native Specific

### File Picker Integration

```typescript
// React Native için
import DocumentPicker from 'react-native-document-picker';
import { transcriptionService } from './services/transcriptionService';

const pickAndUploadFile = async () => {
  try {
    // Pick file
    const result = await DocumentPicker.pick({
      type: [DocumentPicker.types.audio, DocumentPicker.types.video],
    });

    const file = {
      uri: result[0].uri,
      name: result[0].name,
      type: result[0].type
    };

    // Upload
    const uploadResult = await transcriptionService.uploadFile({
      file,
      language: 'tr',
      onProgress: (progress) => {
        console.log('Upload progress:', progress);
      }
    });

    console.log('Upload complete:', uploadResult);

  } catch (err) {
    if (DocumentPicker.isCancel(err)) {
      console.log('User cancelled');
    } else {
      console.error('Error:', err);
    }
  }
};
```

---

## 🔧 5. Error Handling

```typescript
// src/utils/apiErrorHandler.ts
import axios, { AxiosError } from 'axios';

export const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError;
    
    if (axiosError.response) {
      // Server responded with error
      const { status, data } = axiosError.response;
      
      switch (status) {
        case 401:
          return 'Oturum süresi doldu. Lütfen tekrar giriş yapın.';
        case 403:
          return 'Bu işlem için yetkiniz yok.';
        case 404:
          return 'İstenen kaynak bulunamadı.';
        case 422:
          return 'Geçersiz veri gönderildi.';
        case 500:
          return 'Sunucu hatası. Lütfen daha sonra tekrar deneyin.';
        default:
          return (data as any)?.detail || 'Bir hata oluştu';
      }
    } else if (axiosError.request) {
      // No response received
      return 'Sunucuya bağlanılamadı. İnternet bağlantınızı kontrol edin.';
    }
  }

  return 'Bilinmeyen bir hata oluştu';
};
```

---

## 🎯 6. Complete Example: Full Workflow

```typescript
// src/App.tsx - Complete example
import React, { useState, useEffect } from 'react';
import { authService } from './services/authService';
import { transcriptionService } from './services/transcriptionService';
import { websocketService } from './services/websocketService';

const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check if already logged in
    if (authService.isAuthenticated()) {
      setIsAuthenticated(true);
      // Connect WebSocket
      websocketService.connect('user-123');
    }
  }, []);

  const handleLogin = async (username: string, password: string) => {
    try {
      await authService.login({ username, password });
      setIsAuthenticated(true);
      websocketService.connect('user-123');
    } catch (err) {
      console.error('Login failed:', err);
      alert('Giriş başarısız!');
    }
  };

  const handleFileUpload = async (file: File) => {
    try {
      setLoading(true);

      // Upload and wait for result
      const uploadResult = await transcriptionService.uploadFile({
        file,
        language: 'tr',
        onProgress: (progress) => {
          console.log('Upload:', progress + '%');
        }
      });

      // Poll for completion
      const result = await transcriptionService.waitForCompletion(
        uploadResult.id,
        {
          onProgress: (status) => {
            console.log('Status:', status);
          }
        }
      );

      console.log('Transcription complete:', result);
      alert(`✅ Tamamlandı!\n\nMetin: ${result.result_text}`);

    } catch (err) {
      console.error('Error:', err);
      alert('❌ Hata oluştu!');
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return <div>Lütfen giriş yapın</div>;
  }

  return (
    <div>
      <h1>MP4toText</h1>
      <input
        type="file"
        accept="audio/*,video/*"
        onChange={(e) => {
          if (e.target.files?.[0]) {
            handleFileUpload(e.target.files[0]);
          }
        }}
        disabled={loading}
      />
      {loading && <p>İşleniyor...</p>}
    </div>
  );
};

export default App;
```

---

## 📚 7. API Endpoints Özet

### Authentication
- `POST /api/v1/auth/register` - Yeni kullanıcı kaydı
- `POST /api/v1/auth/login` - Giriş yap ve token al
- `GET /api/v1/auth/me` - Profil bilgisi

### Transcriptions
- `POST /api/v1/transcriptions/upload` - Dosya yükle
- `POST /api/v1/transcriptions/` - Yeni transkripsiyon oluştur
- `GET /api/v1/transcriptions/{id}` - Transkripsiyon detayları
- `GET /api/v1/transcriptions/` - Transkripsiyon listesi
- `DELETE /api/v1/transcriptions/{id}` - Transkripsiyon sil
- `POST /api/v1/transcriptions/{id}/process` - İşleme başlat
- `POST /api/v1/transcriptions/{id}/enhance` - Gemini ile iyileştir

### WebSocket
- `WS /ws/{client_id}?token={jwt_token}` - Real-time updates

---

## ✅ Best Practices

1. **Token Management**: Token'ı güvenli bir şekilde sakla (localStorage, SecureStore)
2. **Error Handling**: Tüm API çağrılarında try-catch kullan
3. **Progress Tracking**: Upload ve processing için progress göster
4. **Offline Support**: Network hatalarını gracefully handle et
5. **WebSocket Reconnection**: Bağlantı koptuğunda otomatik yeniden bağlan
6. **File Size Limits**: Büyük dosyalar için chunk upload düşün
7. **Caching**: Transkripsiyon sonuçlarını cache'le

---

## 🚀 Production Checklist

- [ ] API Base URL'yi production domain ile değiştir
- [ ] HTTPS kullan (http:// → https://)
- [ ] WebSocket URL'yi wss:// yap
- [ ] Token refresh mekanizması ekle
- [ ] Rate limiting handle et
- [ ] Analytics entegre et
- [ ] Error logging servisi ekle (Sentry, etc.)
- [ ] Offline mode desteği
- [ ] Background upload (React Native)

---

**🎉 Tamamlandı! Frontend'inizi bu rehberle MP4toText Backend'e bağlayabilirsiniz.**

Sorularınız için: [GitHub Issues](https://github.com/your-repo/mp4totext)
