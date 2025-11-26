"""
Fix TranscriptionDetailPage JSX error and create missing api.ts
"""

from pathlib import Path

FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")

# Create api.ts (axios configuration)
API_TS = FRONTEND_PATH / "src" / "services" / "api.ts"

API_CONTENT = '''import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
'''

# Fixed TranscriptionDetailPage (closing div tag fixed)
DETAIL_PAGE = FRONTEND_PATH / "src" / "pages" / "TranscriptionDetailPage.tsx"

FIXED_DETAIL = '''import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { transcriptionService } from '../services/transcriptionService';
import { Transcription } from '../types/transcription';
import { formatDuration, formatFileSize, formatDate } from '../utils/formatters';

const TranscriptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [transcription, setTranscription] = useState<Transcription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'original' | 'enhanced' | 'summary'>('original');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    loadTranscription();
    
    // Poll for updates if still processing
    const interval = setInterval(() => {
      if (transcription?.status === 'processing' || transcription?.status === 'pending') {
        loadTranscription();
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [id, transcription?.status]);

  const loadTranscription = async () => {
    try {
      const data = await transcriptionService.getById(Number(id));
      setTranscription(data);
      
      // Auto-switch to enhanced tab if available
      if (data.enhanced_text && activeTab === 'original') {
        setActiveTab('enhanced');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load transcription');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (format: 'txt' | 'json' | 'srt') => {
    if (!transcription) return;
    
    setDownloading(true);
    try {
      const blob = await transcriptionService.download(transcription.id, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${transcription.filename}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert('Download failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDownloading(false);
    }
  };

  const handleDelete = async () => {
    if (!transcription) return;
    if (!window.confirm('Bu transkripsionu silmek istediğinizden emin misiniz?')) return;

    try {
      await transcriptionService.delete(transcription.id);
      navigate('/transcriptions');
    } catch (err: any) {
      alert('Delete failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !transcription) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error || 'Transcription not found'}
      </div>
    );
  }

  const isProcessing = transcription.status === 'processing' || transcription.status === 'pending';
  const hasEnhanced = !!transcription.enhanced_text;
  const hasSummary = !!transcription.summary;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">{transcription.filename}</h1>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span>🗓️ {formatDate(transcription.created_at)}</span>
              {transcription.duration && <span>⏱️ {formatDuration(transcription.duration)}</span>}
              {transcription.file_size && <span>💾 {formatFileSize(transcription.file_size)}</span>}
            </div>
          </div>
          
          {/* Status Badge */}
          <div className={`px-4 py-2 rounded-full text-sm font-semibold ${
            transcription.status === 'completed' ? 'bg-green-100 text-green-800' :
            transcription.status === 'processing' ? 'bg-blue-100 text-blue-800' :
            transcription.status === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-yellow-100 text-yellow-800'
          }`}>
            {transcription.status === 'completed' ? '✅ Tamamlandı' :
             transcription.status === 'processing' ? '⏳ İşleniyor' :
             transcription.status === 'failed' ? '❌ Başarısız' :
             '⏸️ Beklemede'}
          </div>
        </div>

        {/* Progress Bar */}
        {isProcessing && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600">{transcription.progress_message || 'İşleniyor...'}</span>
              <span className="text-sm font-medium text-gray-700">{transcription.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${transcription.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Settings Info */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Model:</span>
            <span className="ml-2 font-semibold">{transcription.whisper_model || 'base'}</span>
          </div>
          <div>
            <span className="text-gray-500">Dil:</span>
            <span className="ml-2 font-semibold">{transcription.language || 'Auto'}</span>
          </div>
          <div>
            <span className="text-gray-500">Konuşmacı:</span>
            <span className="ml-2 font-semibold">{transcription.speaker_count || 0}</span>
          </div>
          {hasEnhanced && (
            <div>
              <span className="text-gray-500">AI:</span>
              <span className="ml-2 font-semibold text-green-600">✅ İyileştirildi</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {transcription.status === 'completed' && (
          <div className="mt-4 flex space-x-3">
            <button
              onClick={() => handleDownload('txt')}
              disabled={downloading}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              📄 TXT İndir
            </button>
            <button
              onClick={() => handleDownload('json')}
              disabled={downloading}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              📊 JSON İndir
            </button>
            <button
              onClick={() => handleDownload('srt')}
              disabled={downloading}
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              🎬 SRT İndir
            </button>
            <button
              onClick={handleDelete}
              className="ml-auto px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              🗑️ Sil
            </button>
          </div>
        )}
      </div>

      {/* Transcription Content */}
      {transcription.status === 'completed' && transcription.text && (
        <div className="bg-white rounded-lg shadow-md">
          {/* Tabs */}
          <div className="border-b border-gray-200">
            <div className="flex space-x-1 p-1">
              <button
                onClick={() => setActiveTab('original')}
                className={`flex-1 py-3 px-4 text-sm font-medium rounded-t-lg transition-colors ${
                  activeTab === 'original'
                    ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-700'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                }`}
              >
                📝 Orijinal Metin
              </button>
              
              {hasEnhanced && (
                <button
                  onClick={() => setActiveTab('enhanced')}
                  className={`flex-1 py-3 px-4 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === 'enhanced'
                      ? 'bg-green-50 text-green-700 border-b-2 border-green-700'
                      : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                  }`}
                >
                  ✨ AI İyileştirilmiş Metin
                </button>
              )}
              
              {hasSummary && (
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`flex-1 py-3 px-4 text-sm font-medium rounded-t-lg transition-colors ${
                    activeTab === 'summary'
                      ? 'bg-purple-50 text-purple-700 border-b-2 border-purple-700'
                      : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                  }`}
                >
                  📋 Özet
                </button>
              )}
            </div>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'original' && (
              <div className="prose max-w-none">
                <div className="whitespace-pre-wrap font-mono text-sm text-gray-800 leading-relaxed">
                  {transcription.text}
                </div>
                {transcription.segments && transcription.segments.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-lg font-semibold mb-3">Konuşmacı Segmentleri</h3>
                    <div className="space-y-2">
                      {transcription.segments.map((segment: any, idx: number) => (
                        <div key={idx} className="p-3 bg-gray-50 rounded border-l-4 border-blue-500">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-blue-700">{segment.speaker}</span>
                            <span className="text-xs text-gray-500">
                              {formatDuration(segment.start)} - {formatDuration(segment.end)}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700">{segment.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'enhanced' && hasEnhanced && (
              <div className="prose max-w-none">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-green-800">
                    🤖 Bu metin Gemini AI tarafından noktalama, yazım hataları ve paragraf düzeni için iyileştirildi.
                  </p>
                </div>
                <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                  {transcription.enhanced_text}
                </div>
                {transcription.gemini_improvements && transcription.gemini_improvements.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-lg font-semibold mb-3">Yapılan İyileştirmeler</h3>
                    <ul className="list-disc pl-5 space-y-1">
                      {transcription.gemini_improvements.map((improvement: any, idx: number) => (
                        <li key={idx} className="text-sm text-gray-700">
                          {improvement.type}: {improvement.description}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'summary' && hasSummary && (
              <div className="prose max-w-none">
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-purple-800">
                    📋 Bu özet Gemini AI tarafından otomatik oluşturuldu.
                  </p>
                </div>
                <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                  {transcription.summary}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error Message */}
      {transcription.status === 'failed' && transcription.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-2">❌ Hata</h3>
          <p className="text-red-700">{transcription.error_message}</p>
        </div>
      )}
    </div>
  );
};

export default TranscriptionDetailPage;
'''

def main():
    print("\n🔧 Fixing Vite Errors...")
    print("=" * 50)
    
    success_count = 0
    
    # Create api.ts
    try:
        API_TS.parent.mkdir(parents=True, exist_ok=True)
        print(f"📝 Creating {API_TS.name}...")
        API_TS.write_text(API_CONTENT, encoding='utf-8')
        print(f"✅ {API_TS.name} created successfully!")
        success_count += 1
    except Exception as e:
        print(f"❌ Failed to create {API_TS.name}: {e}")
    
    # Fix TranscriptionDetailPage
    try:
        print(f"\n📝 Fixing {DETAIL_PAGE.name}...")
        DETAIL_PAGE.write_text(FIXED_DETAIL, encoding='utf-8')
        print(f"✅ {DETAIL_PAGE.name} fixed successfully!")
        success_count += 1
    except Exception as e:
        print(f"❌ Failed to fix {DETAIL_PAGE.name}: {e}")
    
    print("\n" + "=" * 50)
    if success_count == 2:
        print("✅ All fixes applied successfully!")
        print("\n📋 Fixed issues:")
        print("   • Created api.ts with axios configuration")
        print("   • Fixed JSX closing tag error in DetailPage")
        print("   • Added auth interceptors")
        print("\n🔄 Vite should hot-reload automatically")
    else:
        print(f"⚠️  {success_count}/2 fixes applied")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
