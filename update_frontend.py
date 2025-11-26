"""
Frontend Upload Component Updater
Adds Whisper model selection and enhancement options
"""

import os
from pathlib import Path

# Frontend path
FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")
UPLOAD_PAGE = FRONTEND_PATH / "src" / "pages" / "UploadPage.tsx"

# New upload page content with model selection
NEW_UPLOAD_PAGE = '''import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import { transcriptionService } from '../services/transcriptionService';

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  // Model and options state
  const [whisperModel, setWhisperModel] = useState<string>('base');
  const [useSpeakerRecognition, setUseSpeakerRecognition] = useState<boolean>(true);
  const [useGeminiEnhancement, setUseGeminiEnhancement] = useState<boolean>(false);

  const handleFileSelect = async (file: File) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      console.log('Starting upload with options:', {
        whisper_model: whisperModel,
        use_speaker_recognition: useSpeakerRecognition,
        use_gemini_enhancement: useGeminiEnhancement
      });

      const transcription = await transcriptionService.upload(
        file,
        (progress) => {
          setUploadProgress(progress.percent);
        },
        {
          whisper_model: whisperModel,
          use_speaker_recognition: useSpeakerRecognition,
          use_gemini_enhancement: useGeminiEnhancement
        }
      );

      console.log('Upload complete! Transcription:', transcription);
      navigate(`/transcriptions/${transcription.id}`);
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const modelOptions = [
    { value: 'tiny', label: 'Tiny (En Hızlı, Düşük Kalite)', description: '~1GB RAM, En hızlı işlem' },
    { value: 'base', label: 'Base (Hızlı, İyi)', description: '~1GB RAM, Önerilen' },
    { value: 'small', label: 'Small (Orta Hız, Çok İyi)', description: '~2GB RAM' },
    { value: 'medium', label: 'Medium (Yavaş, Mükemmel)', description: '~5GB RAM' },
    { value: 'large', label: 'Large (En İyi Kalite)', description: '~10GB RAM, En yavaş' },
    { value: 'turbo', label: 'Turbo (Hızlı ve İyi)', description: '~6GB RAM, Yeni model' },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Yeni Transkripsiyon</h1>

        {/* Model Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            🎙️ Whisper Model Seçimi
          </label>
          <select
            value={whisperModel}
            onChange={(e) => setWhisperModel(e.target.value)}
            disabled={uploading}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {modelOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} - {option.description}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-500">
            Küçük modeller daha hızlı, büyük modeller daha doğru sonuç verir
          </p>
        </div>

        {/* Enhancement Options */}
        <div className="mb-6 space-y-3">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ✨ İyileştirme Seçenekleri
          </label>
          
          {/* Speaker Recognition */}
          <div className="flex items-center">
            <input
              id="speaker-recognition"
              type="checkbox"
              checked={useSpeakerRecognition}
              onChange={(e) => setUseSpeakerRecognition(e.target.checked)}
              disabled={uploading}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="speaker-recognition" className="ml-2 block text-sm text-gray-700">
              👥 Konuşmacı Tanıma (Speaker Recognition)
            </label>
          </div>
          <p className="ml-6 text-xs text-gray-500">
            Farklı konuşmacıları otomatik olarak ayırır ve etiketler
          </p>

          {/* Gemini Enhancement */}
          <div className="flex items-center">
            <input
              id="gemini-enhancement"
              type="checkbox"
              checked={useGeminiEnhancement}
              onChange={(e) => setUseGeminiEnhancement(e.target.checked)}
              disabled={uploading}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="gemini-enhancement" className="ml-2 block text-sm text-gray-700">
              🤖 Gemini AI İyileştirme
            </label>
          </div>
          <p className="ml-6 text-xs text-gray-500">
            Noktalama, yazım hataları düzeltme ve paragraf düzenleme (daha yavaş)
          </p>
        </div>

        {/* File Upload */}
        <FileUpload
          onFileSelect={handleFileSelect}
          disabled={uploading}
          accept="audio/*,video/*,.mp3,.mp4,.wav,.m4a,.avi,.mov,.mkv"
        />

        {/* Upload Progress */}
        {uploading && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Yükleniyor...</span>
              <span className="text-sm font-medium text-gray-700">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <h3 className="text-sm font-semibold text-blue-800 mb-2">💡 İpuçları:</h3>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>• İlk transkripsiyon daha yavaş olabilir (model indiriliyor)</li>
            <li>• Kısa dosyalar için "tiny" veya "base" modeli yeterlidir</li>
            <li>• Gemini iyileştirme işlem süresini 2-3 kat artırabilir</li>
            <li>• Speaker recognition çok konuşmacılı kayıtlar için faydalıdır</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
'''

# Update transcription service types
TRANSCRIPTION_SERVICE = FRONTEND_PATH / "src" / "services" / "transcriptionService.ts"

NEW_SERVICE_CONTENT = '''import api from './api';
import { Transcription, UploadProgress } from '../types/transcription';

export interface TranscriptionOptions {
  whisper_model?: string;
  use_speaker_recognition?: boolean;
  use_gemini_enhancement?: boolean;
}

export const transcriptionService = {
  upload: async (
    file: File, 
    onProgress?: (progress: UploadProgress) => void,
    options?: TranscriptionOptions
  ): Promise<Transcription> => {
    console.log('Step 1: Uploading file...', file.name);
    
    // Step 1: Upload file to storage
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadResponse = await api.post<{file_id: string; filename: string}>(
      '/transcriptions/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress({
              loaded: progressEvent.loaded,
              total: progressEvent.total,
              percent,
            });
          }
        },
      }
    );
    
    console.log('Step 1 complete. File ID:', uploadResponse.data.file_id);
    console.log('Step 2: Creating transcription...');
    
    // Step 2: Create transcription record with options
    const transcriptionData = {
      file_id: uploadResponse.data.file_id,
      language: null,
      whisper_model: options?.whisper_model || 'base',
      use_speaker_recognition: options?.use_speaker_recognition ?? true,
      use_gemini_enhancement: options?.use_gemini_enhancement ?? false,
    };
    
    console.log('Creating transcription with:', transcriptionData);
    
    const transcriptionResponse = await api.post<Transcription>(
      '/transcriptions',
      transcriptionData
    );
    
    console.log('Step 2 complete. Transcription created:', transcriptionResponse.data);
    return transcriptionResponse.data;
  },

  getById: async (id: number): Promise<Transcription> => {
    const response = await api.get<Transcription>(`/transcriptions/${id}`);
    return response.data;
  },

  list: async (page: number = 1, pageSize: number = 10) => {
    const response = await api.get('/transcriptions', {
      params: { page, per_page: pageSize },
    });
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/transcriptions/${id}`);
  },

  download: async (id: number, format: 'txt' | 'json' | 'srt' = 'txt'): Promise<Blob> => {
    const response = await api.get(`/transcriptions/${id}/download/${format}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};
'''

def update_file(file_path: Path, content: str):
    """Update file with new content"""
    try:
        print(f"📝 Updating {file_path.name}...")
        file_path.write_text(content, encoding='utf-8')
        print(f"✅ {file_path.name} updated successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to update {file_path.name}: {e}")
        return False

def main():
    print("\n🚀 Updating MP4toText Frontend...")
    print("=" * 50)
    
    if not FRONTEND_PATH.exists():
        print(f"❌ Frontend path not found: {FRONTEND_PATH}")
        return
    
    # Update files
    success = True
    
    if UPLOAD_PAGE.exists():
        success = update_file(UPLOAD_PAGE, NEW_UPLOAD_PAGE) and success
    else:
        print(f"⚠️  {UPLOAD_PAGE} not found, skipping...")
    
    if TRANSCRIPTION_SERVICE.exists():
        success = update_file(TRANSCRIPTION_SERVICE, NEW_SERVICE_CONTENT) and success
    else:
        print(f"⚠️  {TRANSCRIPTION_SERVICE} not found, skipping...")
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Frontend updated successfully!")
        print("\n📋 Changes:")
        print("   • Whisper model selection (tiny → turbo)")
        print("   • Speaker Recognition checkbox")
        print("   • Gemini AI Enhancement checkbox")
        print("   • Updated transcriptionService with options")
    else:
        print("⚠️  Some files could not be updated")
    
    print("\n🔄 Please restart Vite dev server if running")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
