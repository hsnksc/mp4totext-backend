# MP4toText Web - AI Agent Instructions

## 🎯 Project Overview
**React web application** for audio/video transcription with AI-powered features, built with Vite, TypeScript, and modern React patterns.

**Tech Stack**: React 18+ | Vite | TypeScript | Zustand | React Query | TanStack Router | Tailwind CSS | WebSocket

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Web App (React + Vite)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    Pages     │  │    Stores    │  │   Services   │     │
│  │  (routes/)   │  │  (Zustand)   │  │   (API/WS)   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             │ HTTP/WebSocket
                             ▼
                    ┌──────────────────┐
                    │  FastAPI Backend │
                    │   (port 8002)    │
                    └──────────────────┘
```

### Key App Boundaries
- **Routing**: TanStack Router (file-based, type-safe routing)
- **State Management**: Zustand stores (auth, transcription, credits)
- **API Communication**: Axios with interceptors, React Query for data fetching
- **Real-time Updates**: WebSocket with reconnection logic
- **UI Framework**: Tailwind CSS + Shadcn/ui components
- **Build Tool**: Vite (fast HMR, optimized production builds)

---

## 📁 Key Directory Structure

```
mp4totext-web/
├── src/
│   ├── routes/                       # TanStack Router pages
│   │   ├── __root.tsx                # Root layout (providers, navbar)
│   │   ├── index.tsx                 # Home page (landing/dashboard)
│   │   ├── auth/
│   │   │   ├── login.tsx
│   │   │   └── register.tsx
│   │   ├── dashboard/
│   │   │   ├── index.tsx             # Dashboard (transcriptions list)
│   │   │   ├── new.tsx               # New transcription (upload)
│   │   │   └── transcription.$id.tsx # Detail view (dynamic route)
│   │   ├── credits/
│   │   │   ├── index.tsx             # Credits overview
│   │   │   └── purchase.tsx          # Purchase credits
│   │   └── profile/
│   │       └── index.tsx             # User profile
│   │
│   ├── components/                   # Reusable UI components
│   │   ├── ui/                       # Shadcn/ui primitives
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── toast.tsx
│   │   ├── layout/                   # Layout components
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   ├── transcription/            # Feature-specific components
│   │   │   ├── TranscriptionCard.tsx
│   │   │   ├── TranscriptionList.tsx
│   │   │   ├── UploadForm.tsx
│   │   │   └── TranscriptionDetail.tsx
│   │   └── common/                   # Shared components
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       └── CreditBadge.tsx
│   │
│   ├── stores/                       # Zustand state management
│   │   ├── authStore.ts              # User auth, token, login/logout
│   │   ├── transcriptionStore.ts     # Transcriptions list, CRUD
│   │   ├── creditStore.ts            # Credit balance, transactions
│   │   └── uiStore.ts                # UI state (sidebar, modals)
│   │
│   ├── services/                     # API & external services
│   │   ├── api/
│   │   │   ├── client.ts             # Axios instance, interceptors
│   │   │   ├── auth.ts               # Auth API calls
│   │   │   ├── transcription.ts      # Transcription API calls
│   │   │   └── credit.ts             # Credit API calls
│   │   └── websocket/
│   │       ├── WebSocketManager.ts   # WebSocket connection manager
│   │       └── handlers.ts           # Message handlers
│   │
│   ├── hooks/                        # Custom React hooks
│   │   ├── useWebSocket.ts           # WebSocket connection hook
│   │   ├── useTranscriptions.ts      # React Query hook
│   │   ├── useAuth.ts                # Auth state hook
│   │   └── useMediaQuery.ts          # Responsive design hook
│   │
│   ├── types/                        # TypeScript definitions
│   │   ├── transcription.ts
│   │   ├── user.ts
│   │   ├── api.ts
│   │   └── credit.ts
│   │
│   ├── utils/                        # Utility functions
│   │   ├── dateFormatter.ts
│   │   ├── creditCalculator.ts
│   │   ├── fileValidator.ts
│   │   └── cn.ts                     # Tailwind class merger
│   │
│   ├── lib/                          # Third-party lib configs
│   │   ├── queryClient.ts            # React Query config
│   │   └── router.ts                 # TanStack Router config
│   │
│   ├── App.tsx                       # Root component
│   ├── main.tsx                      # Entry point (ReactDOM.render)
│   └── index.css                     # Global styles (Tailwind)
│
├── public/                           # Static assets
│   ├── favicon.ico
│   └── logo.svg
│
├── index.html                        # HTML entry point
├── vite.config.ts                    # Vite configuration
├── tailwind.config.js                # Tailwind CSS config
├── tsconfig.json                     # TypeScript config
└── package.json
```

---

## 🔧 Development Workflow

### Setup & Installation

```bash
# 1. Install dependencies
cd mp4totext-web
npm install  # or yarn/pnpm

# 2. Start development server
npm run dev
# App runs on: http://localhost:5173

# 3. Environment configuration
# Create .env file (not tracked in git)
cp .env.example .env
```

### Environment Variables (`.env`)

```bash
# API endpoints
VITE_API_BASE_URL=http://localhost:8002
VITE_WS_URL=ws://localhost:8002

# Feature flags (optional)
VITE_ENABLE_ANALYTICS=false
VITE_DEBUG_MODE=true
```

### Build & Deploy

```bash
# Development build (HMR enabled)
npm run dev

# Production build
npm run build
# Output: dist/ directory

# Preview production build locally
npm run preview

# Type checking
npm run type-check

# Linting
npm run lint

# Format code
npm run format
```

### Testing & Debugging

```bash
# Run tests (if configured)
npm test

# TypeScript type checking
npx tsc --noEmit

# Browser DevTools
# React DevTools: Chrome/Firefox extension
# Redux DevTools: For Zustand (with middleware)
```

---

## 💻 Code Patterns & Conventions

### 1. Page Component Pattern (TanStack Router)

```tsx
// src/routes/dashboard/index.tsx - Standard page structure
import { createFileRoute } from '@tanstack/react-router';
import { useTranscriptions } from '@/hooks/useTranscriptions';
import { useAuthStore } from '@/stores/authStore';
import TranscriptionList from '@/components/transcription/TranscriptionList';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import ErrorMessage from '@/components/common/ErrorMessage';

export const Route = createFileRoute('/dashboard/')({
  component: DashboardPage,
});

function DashboardPage() {
  const { user } = useAuthStore();
  const { transcriptions, isLoading, error, refetch } = useTranscriptions();

  // Loading state
  if (isLoading) {
    return <LoadingSpinner />;
  }

  // Error state
  if (error) {
    return <ErrorMessage message="Failed to load transcriptions" onRetry={refetch} />;
  }

  // Empty state
  if (transcriptions.length === 0) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold mb-4">No transcriptions yet</h2>
        <p className="text-gray-600">Upload your first audio or video file</p>
      </div>
    );
  }

  // Main content
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">My Transcriptions</h1>
        <button onClick={refetch} className="btn-primary">
          Refresh
        </button>
      </div>
      <TranscriptionList transcriptions={transcriptions} />
    </div>
  );
}
```

### 2. Zustand Store Pattern

```typescript
// src/stores/authStore.ts - State management pattern
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { User } from '@/types/user';
import { authApi } from '@/services/api/auth';

interface AuthState {
  // State
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
  updateCredits: (newBalance: number) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      // Login action
      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await authApi.login(email, password);
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      // Register action
      register: async (email: string, password: string, name: string) => {
        set({ isLoading: true });
        try {
          const response = await authApi.register(email, password, name);
          set({
            user: response.user,
            token: response.access_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      // Logout action
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        });
        localStorage.clear();
      },

      // Refresh token
      refreshToken: async () => {
        try {
          const response = await authApi.refreshToken();
          set({ token: response.access_token });
        } catch (error) {
          get().logout();
          throw error;
        }
      },

      // Update user (optimistic update)
      updateUser: (updates) => {
        const currentUser = get().user;
        if (currentUser) {
          set({ user: { ...currentUser, ...updates } });
        }
      },

      // Update credits (real-time from WebSocket)
      updateCredits: (newBalance) => {
        const currentUser = get().user;
        if (currentUser) {
          set({ user: { ...currentUser, credits: newBalance } });
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

### 3. API Service Pattern (Axios + Interceptors)

```typescript
// src/services/api/client.ts - Axios instance
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8002';

// Create Axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (add auth token)
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (handle errors globally)
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh token
        await useAuthStore.getState().refreshToken();
        // Retry original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - logout user
        useAuthStore.getState().logout();
        window.location.href = '/auth/login';
        return Promise.reject(refreshError);
      }
    }

    // Handle 402 Payment Required (insufficient credits)
    if (error.response?.status === 402) {
      // Show notification
      toast.error('Insufficient credits. Please purchase more.');
    }

    return Promise.reject(error);
  }
);

// src/services/api/transcription.ts - API service
import { apiClient } from './client';
import { Transcription, TranscriptionCreateRequest } from '@/types/transcription';

export const transcriptionApi = {
  // Get all transcriptions
  getAll: async (): Promise<Transcription[]> => {
    const response = await apiClient.get('/api/v1/transcriptions');
    return response.data;
  },

  // Get single transcription
  getById: async (id: number): Promise<Transcription> => {
    const response = await apiClient.get(`/api/v1/transcriptions/${id}`);
    return response.data;
  },

  // Upload file
  upload: async (
    file: File,
    options: TranscriptionCreateRequest,
    onProgress?: (progress: number) => void
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('options', JSON.stringify(options));

    const response = await apiClient.post('/api/v1/transcriptions/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
    });

    return response.data;
  },

  // Delete transcription
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/transcriptions/${id}`);
  },

  // Update transcription
  update: async (id: number, updates: Partial<Transcription>): Promise<Transcription> => {
    const response = await apiClient.patch(`/api/v1/transcriptions/${id}`, updates);
    return response.data;
  },
};
```

### 4. WebSocket Real-time Updates

```typescript
// src/services/websocket/WebSocketManager.ts
import { useAuthStore } from '@/stores/authStore';
import { useTranscriptionStore } from '@/stores/transcriptionStore';
import { toast } from '@/components/ui/use-toast';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8002';

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  connect() {
    const user = useAuthStore.getState().user;
    if (!user) {
      console.warn('⚠️ Cannot connect WebSocket: User not authenticated');
      return;
    }

    try {
      this.ws = new WebSocket(`${WS_URL}/ws?user_id=${user.id}`);

      this.ws.onopen = () => {
        console.log('✅ WebSocket connected');
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      };

      this.ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };

      this.ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected', event.code, event.reason);
        this.stopHeartbeat();
        this.reconnect();
      };
    } catch (error) {
      console.error('❌ WebSocket connection failed:', error);
      this.reconnect();
    }
  }

  private handleMessage(data: any) {
    console.log('📨 WebSocket message:', data);

    switch (data.type) {
      case 'upload_progress':
        useTranscriptionStore.getState().updateProgress(
          data.transcription_id,
          data.progress
        );
        break;

      case 'job_complete':
        useTranscriptionStore.getState().updateStatus(
          data.transcription_id,
          'completed'
        );
        toast({
          title: 'Transcription Complete',
          description: 'Your transcription is ready!',
        });
        break;

      case 'error':
        useTranscriptionStore.getState().updateStatus(
          data.transcription_id,
          'failed'
        );
        toast({
          title: 'Transcription Failed',
          description: data.message || 'An error occurred',
          variant: 'destructive',
        });
        break;

      case 'credit_update':
        useAuthStore.getState().updateCredits(data.new_balance);
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Max reconnect attempts reached');
      toast({
        title: 'Connection Lost',
        description: 'Unable to reconnect. Please refresh the page.',
        variant: 'destructive',
      });
      return;
    }

    this.reconnectAttempts++;
    console.log(`🔄 Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay * this.reconnectAttempts); // Exponential backoff
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket not connected. Cannot send message.');
    }
  }
}

export const websocketManager = new WebSocketManager();

// src/hooks/useWebSocket.ts - React hook
import { useEffect } from 'react';
import { websocketManager } from '@/services/websocket/WebSocketManager';
import { useAuthStore } from '@/stores/authStore';

export const useWebSocket = () => {
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      websocketManager.connect();
    }

    return () => {
      websocketManager.disconnect();
    };
  }, [isAuthenticated]);

  return {
    send: websocketManager.send.bind(websocketManager),
  };
};
```

### 5. React Query Data Fetching

```typescript
// src/hooks/useTranscriptions.ts - React Query hook
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { transcriptionApi } from '@/services/api/transcription';
import { toast } from '@/components/ui/use-toast';

export const useTranscriptions = () => {
  const queryClient = useQueryClient();

  // Fetch all transcriptions
  const {
    data: transcriptions,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['transcriptions'],
    queryFn: transcriptionApi.getAll,
    staleTime: 60000, // 1 minute
    gcTime: 300000, // 5 minutes (formerly cacheTime)
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: transcriptionApi.delete,
    onMutate: async (deletedId) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: ['transcriptions'] });

      // Snapshot previous value
      const previousTranscriptions = queryClient.getQueryData(['transcriptions']);

      // Optimistically remove from UI
      queryClient.setQueryData(['transcriptions'], (old: any[]) =>
        old?.filter((t) => t.id !== deletedId)
      );

      return { previousTranscriptions };
    },
    onError: (error, deletedId, context) => {
      // Rollback on error
      queryClient.setQueryData(['transcriptions'], context?.previousTranscriptions);
      toast({
        title: 'Delete Failed',
        description: 'Failed to delete transcription',
        variant: 'destructive',
      });
    },
    onSuccess: () => {
      toast({
        title: 'Deleted',
        description: 'Transcription deleted successfully',
      });
    },
    onSettled: () => {
      // Refetch to sync with server
      queryClient.invalidateQueries({ queryKey: ['transcriptions'] });
    },
  });

  return {
    transcriptions: transcriptions || [],
    isLoading,
    error,
    refetch,
    deleteTranscription: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
  };
};
```

### 6. File Upload with Drag & Drop

```tsx
// src/components/transcription/UploadForm.tsx
import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { transcriptionApi } from '@/services/api/transcription';
import { useAuthStore } from '@/stores/authStore';
import { Progress } from '@/components/ui/progress';
import { toast } from '@/components/ui/use-toast';

export function UploadForm() {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const { user } = useAuthStore();

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];

    // Validate file size (max 500MB)
    if (file.size > 500 * 1024 * 1024) {
      toast({
        title: 'File Too Large',
        description: 'Maximum file size is 500MB',
        variant: 'destructive',
      });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      await transcriptionApi.upload(
        file,
        {
          language: 'en',
          model: 'whisper',
          features: {
            sentiment_analysis: true,
            entity_detection: true,
          },
        },
        (progress) => {
          setUploadProgress(progress);
        }
      );

      toast({
        title: 'Upload Complete',
        description: 'Your transcription is being processed',
      });

      setUploadProgress(100);
    } catch (error: any) {
      console.error('❌ Upload failed:', error);
      toast({
        title: 'Upload Failed',
        description: error.response?.data?.detail || 'Please try again',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.flac'],
      'video/*': ['.mp4', '.mov', '.avi', '.mkv'],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        {isUploading ? (
          <div className="space-y-4">
            <p className="text-lg font-medium">Uploading...</p>
            <Progress value={uploadProgress} className="w-full" />
            <p className="text-sm text-gray-600">{uploadProgress}%</p>
          </div>
        ) : isDragActive ? (
          <p className="text-lg font-medium text-blue-600">Drop file here...</p>
        ) : (
          <div className="space-y-2">
            <p className="text-lg font-medium">Drag & drop or click to upload</p>
            <p className="text-sm text-gray-600">
              Supports audio (MP3, WAV, M4A) and video (MP4, MOV) files up to 500MB
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## 🎨 UI/UX Patterns

### Tailwind CSS + Shadcn/ui Integration

```tsx
// Using Tailwind with cn() utility for conditional classes
import { cn } from '@/utils/cn';

export function Button({ variant = 'default', className, ...props }) {
  return (
    <button
      className={cn(
        'px-4 py-2 rounded-md font-medium transition-colors',
        {
          'bg-blue-600 text-white hover:bg-blue-700': variant === 'default',
          'bg-gray-200 text-gray-800 hover:bg-gray-300': variant === 'secondary',
          'border border-gray-300 hover:bg-gray-50': variant === 'outline',
        },
        className
      )}
      {...props}
    />
  );
}
```

### Protected Route Pattern

```tsx
// src/components/layout/ProtectedRoute.tsx
import { Navigate, Outlet } from '@tanstack/react-router';
import { useAuthStore } from '@/stores/authStore';

export function ProtectedRoute() {
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" />;
  }

  return <Outlet />;
}
```

### Loading States with Suspense

```tsx
// Use React Suspense for better loading UX
import { Suspense } from 'react';
import LoadingSpinner from '@/components/common/LoadingSpinner';

export function DashboardLayout() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Outlet />
    </Suspense>
  );
}
```

---

## ⚠️ Common Issues & Solutions

### Issue 1: Vite Build Errors
```bash
# Problem: Build fails with "Cannot find module"
# Solution:
rm -rf node_modules dist .vite
npm install
npm run build
```

### Issue 2: Hot Module Replacement (HMR) Not Working
```bash
# Problem: Changes not reflecting
# Solution:
# 1. Check if you're using state incorrectly (avoid closure issues)
# 2. Restart Vite dev server
npm run dev
```

### Issue 3: WebSocket Connection Fails in Production
```typescript
// Problem: WebSocket using wrong protocol (ws:// vs wss://)
// Solution: Auto-detect protocol
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${window.location.host}`;
```

### Issue 4: Environment Variables Not Loading
```bash
# Problem: import.meta.env.VITE_* is undefined
# Cause: Not prefixed with VITE_
# Solution: All env vars MUST start with VITE_
# .env
VITE_API_BASE_URL=http://localhost:8002  # ✅ Works
API_BASE_URL=http://localhost:8002        # ❌ Doesn't work
```

### Issue 5: Zustand Store Not Persisting
```typescript
// Problem: Store resets on refresh
// Solution: Check persist middleware configuration
import { persist, createJSONStorage } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set) => ({
      // state and actions
    }),
    {
      name: 'auth-storage',  // localStorage key
      storage: createJSONStorage(() => localStorage),
    }
  )
);
```

---

## 🎯 Best Practices

### State Management
- Use Zustand for global client state (auth, UI state)
- Use React Query for server state (API data)
- Use local state (useState) for component-specific UI state

### Performance Optimization
```tsx
// 1. Lazy load routes
const DashboardPage = lazy(() => import('@/routes/dashboard'));

// 2. Memoize expensive computations
const expensiveValue = useMemo(() => {
  return computeExpensiveValue(data);
}, [data]);

// 3. Debounce search inputs
const debouncedSearch = useDebouncedCallback((value) => {
  search(value);
}, 300);

// 4. Virtualize long lists
import { useVirtualizer } from '@tanstack/react-virtual';
```

### Error Handling
```typescript
// Global error boundary
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div role="alert">
      <p>Something went wrong:</p>
      <pre>{error.message}</pre>
      <button onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

// In App.tsx
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <YourApp />
</ErrorBoundary>
```

### Logging
```typescript
// Use consistent logging pattern
console.log('🚀 Uploading file...');
console.log('✅ Upload complete');
console.error('❌ Upload failed:', error);
console.info('💰 Credits updated:', newBalance);
```

---

## 📚 Reference Files

### Key Entry Points
- `src/main.tsx` - React root, ReactDOM.render
- `src/App.tsx` - Root component, providers
- `src/routes/__root.tsx` - Root layout, navbar

### Core Configuration
- `vite.config.ts` - Vite build config, plugins
- `tailwind.config.js` - Tailwind CSS customization
- `src/lib/queryClient.ts` - React Query config

### Important Stores
- `src/stores/authStore.ts` - Authentication state
- `src/stores/transcriptionStore.ts` - Transcription list state
- `src/stores/uiStore.ts` - UI state (sidebar, modals)

### Critical Services
- `src/services/api/client.ts` - Axios instance, interceptors
- `src/services/websocket/WebSocketManager.ts` - WebSocket manager
