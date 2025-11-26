#!/usr/bin/env python3
"""
Upload & Transcription komponentlerini oluştur
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

FILES = {
    # TYPES
    "types/transcription.ts": """export interface Transcription {
  id: number;
  file_id: string;
  filename: string;
  file_size: number;
  language: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  text?: string;
  enhanced_text?: string;
  summary?: string;
  speakers?: SpeakerSegment[];
  segments?: TranscriptionSegment[];
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface SpeakerSegment {
  speaker: string;
  start: number;
  end: number;
  text: string;
}

export interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}
""",

    # SERVICES
    "services/transcriptionService.ts": """import api from './authService';
import { API_CONFIG, ENDPOINTS } from '../config/api';
import type { Transcription, UploadProgress } from '../types/transcription';

export const transcriptionService = {
  async upload(
    file: File,
    language: string = 'auto',
    onProgress?: (progress: UploadProgress) => void
  ): Promise<Transcription> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);

    const response = await api.post<Transcription>(
      ENDPOINTS.TRANSCRIPTIONS.CREATE,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percentage = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percentage,
            });
          }
        },
      }
    );

    return response.data;
  },

  async getAll(page: number = 1, pageSize: number = 10): Promise<Transcription[]> {
    const response = await api.get<Transcription[]>(
      `${ENDPOINTS.TRANSCRIPTIONS.LIST}?page=${page}&page_size=${pageSize}`
    );
    return response.data;
  },

  async getById(id: number): Promise<Transcription> {
    const response = await api.get<Transcription>(
      ENDPOINTS.TRANSCRIPTIONS.GET(id)
    );
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(ENDPOINTS.TRANSCRIPTIONS.DELETE(id));
  },

  async downloadText(id: number, format: 'txt' | 'json' | 'srt' = 'txt'): Promise<Blob> {
    const response = await api.get(
      `${ENDPOINTS.TRANSCRIPTIONS.GET(id)}/download?format=${format}`,
      { responseType: 'blob' }
    );
    return response.data;
  },
};
""",

    # COMPONENTS - FileUpload
    "components/FileUpload.tsx": """import React, { useState, useRef } from 'react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onFileSelect,
  accept = 'audio/*,video/*',
  maxSize = 500 * 1024 * 1024, // 500MB
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFile = (file: File) => {
    setError('');

    // Validate file size
    if (file.size > maxSize) {
      setError(`Dosya boyutu çok büyük. Maksimum ${maxSize / (1024 * 1024)}MB olmalıdır.`);
      return;
    }

    // Validate file type
    const validTypes = accept.split(',').map(t => t.trim());
    const fileType = file.type;
    const isValid = validTypes.some(type => {
      if (type.endsWith('/*')) {
        return fileType.startsWith(type.replace('/*', ''));
      }
      return fileType === type;
    });

    if (!isValid) {
      setError('Geçersiz dosya formatı. Lütfen ses veya video dosyası yükleyin.');
      return;
    }

    onFileSelect(file);
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full">
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-all duration-200
          ${isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFileInput}
          className="hidden"
        />

        <div className="space-y-4">
          <div className="text-5xl">
            {isDragging ? '📥' : '🎙️'}
          </div>

          <div>
            <p className="text-lg font-medium text-gray-700">
              {isDragging ? 'Dosyayı buraya bırakın' : 'Ses veya video dosyası yükleyin'}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Dosyayı sürükle-bırak yapın veya tıklayın
            </p>
          </div>

          <div className="text-xs text-gray-400">
            <p>Desteklenen formatlar: MP3, MP4, WAV, M4A, AAC, FLAC</p>
            <p>Maksimum dosya boyutu: {maxSize / (1024 * 1024)}MB</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}
    </div>
  );
};
""",

    # COMPONENTS - ProgressBar
    "components/ProgressBar.tsx": """import React from 'react';

interface ProgressBarProps {
  percentage: number;
  status?: string;
  showPercentage?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  percentage,
  status,
  showPercentage = true,
}) => {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        {status && (
          <span className="text-sm font-medium text-gray-700">{status}</span>
        )}
        {showPercentage && (
          <span className="text-sm font-medium text-gray-700">{percentage}%</span>
        )}
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};
""",

    # COMPONENTS - TranscriptionCard
    "components/TranscriptionCard.tsx": """import React from 'react';
import type { Transcription } from '../types/transcription';

interface TranscriptionCardProps {
  transcription: Transcription;
  onView: (id: number) => void;
  onDelete: (id: number) => void;
}

export const TranscriptionCard: React.FC<TranscriptionCardProps> = ({
  transcription,
  onView,
  onDelete,
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'pending':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Tamamlandı';
      case 'processing':
        return 'İşleniyor';
      case 'pending':
        return 'Bekliyor';
      case 'failed':
        return 'Başarısız';
      default:
        return status;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-4 border border-gray-200">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-medium text-gray-800 truncate" title={transcription.filename}>
            {transcription.filename}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            {formatFileSize(transcription.file_size)} • {formatDate(transcription.created_at)}
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(transcription.status)}`}>
          {getStatusText(transcription.status)}
        </span>
      </div>

      {transcription.text && (
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">
          {transcription.text}
        </p>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <button
          onClick={() => onView(transcription.id)}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          Detayları Gör
        </button>
        <button
          onClick={() => onDelete(transcription.id)}
          className="text-sm text-red-600 hover:text-red-700 font-medium"
        >
          Sil
        </button>
      </div>
    </div>
  );
};
""",

    # PAGES - UploadPage
    "pages/UploadPage.tsx": """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileUpload } from '../components/FileUpload';
import { ProgressBar } from '../components/ProgressBar';
import { transcriptionService } from '../services/transcriptionService';
import type { UploadProgress } from '../types/transcription';

export const UploadPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress>({ loaded: 0, total: 0, percentage: 0 });
  const [error, setError] = useState<string>('');
  const [language, setLanguage] = useState('auto');
  const navigate = useNavigate();

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError('');
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError('');

    try {
      const transcription = await transcriptionService.upload(
        selectedFile,
        language,
        setProgress
      );

      // Başarılı, dashboard'a yönlendir
      setTimeout(() => {
        navigate('/dashboard');
      }, 1000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Yükleme başarısız oldu. Lütfen tekrar deneyin.');
    } finally {
      setUploading(false);
    }
  };

  const handleCancel = () => {
    setSelectedFile(null);
    setProgress({ loaded: 0, total: 0, percentage: 0 });
    setError('');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Dosya Yükle</h1>
          <p className="text-gray-600">
            Ses veya video dosyanızı yükleyin ve otomatik transkripsiyon alın
          </p>
        </div>

        {!selectedFile ? (
          <FileUpload onFileSelect={handleFileSelect} />
        ) : (
          <div className="bg-white rounded-lg shadow p-6 space-y-6">
            {/* Seçili Dosya Bilgisi */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center space-x-4">
                <div className="text-4xl">📄</div>
                <div>
                  <p className="font-medium text-gray-800">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
              {!uploading && (
                <button
                  onClick={handleCancel}
                  className="text-red-600 hover:text-red-700 font-medium"
                >
                  İptal
                </button>
              )}
            </div>

            {/* Dil Seçimi */}
            {!uploading && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dil Seçimi
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="auto">Otomatik Algıla</option>
                  <option value="tr">Türkçe</option>
                  <option value="en">İngilizce</option>
                  <option value="de">Almanca</option>
                  <option value="fr">Fransızca</option>
                  <option value="es">İspanyolca</option>
                  <option value="ar">Arapça</option>
                </select>
              </div>
            )}

            {/* Progress Bar */}
            {uploading && (
              <ProgressBar
                percentage={progress.percentage}
                status="Yükleniyor..."
              />
            )}

            {/* Error */}
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                {error}
              </div>
            )}

            {/* Upload Button */}
            {!uploading && (
              <button
                onClick={handleUpload}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 rounded-lg transition-colors"
              >
                Yükle ve Transkribe Et
              </button>
            )}

            {progress.percentage === 100 && uploading && (
              <div className="text-center text-green-600 font-medium">
                ✅ Yükleme tamamlandı! İşleniyor...
              </div>
            )}
          </div>
        )}

        {/* Info */}
        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-medium text-blue-900 mb-2">ℹ️ Bilgi</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Dosyanız yüklendikten sonra otomatik olarak işlenmeye başlanacak</li>
            <li>• İşlem süresi dosya boyutuna göre değişiklik gösterir</li>
            <li>• İşlem tamamlandığında dashboard'da görebilirsiniz</li>
            <li>• Transkripsiyon, konuşmacı tanıma ve AI özetleme otomatik yapılır</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
""",
}

print("🔧 Upload & Transcription komponentleri oluşturuluyor...\n")
for path, content in FILES.items():
    full_path = os.path.join(WEB_SRC, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {path}")

print("\n✅ Tüm dosyalar başarıyla oluşturuldu!")
print("\n📝 Oluşturulan Dosyalar:")
print("  • types/transcription.ts - TypeScript tipleri")
print("  • services/transcriptionService.ts - API servisi")
print("  • components/FileUpload.tsx - Drag & drop upload")
print("  • components/ProgressBar.tsx - İlerleme çubuğu")
print("  • components/TranscriptionCard.tsx - Transkript kartı")
print("  • pages/UploadPage.tsx - Upload sayfası")
