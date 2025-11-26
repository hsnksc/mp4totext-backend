import os

web_dir = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web"
page_file = os.path.join(web_dir, "src", "pages", "TranscriptionDetailPage.tsx")

content = """import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types';

export const TranscriptionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [transcription, setTranscription] = useState<Transcription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'text' | 'enhanced' | 'summary'>('text');

  useEffect(() => {
    if (id) {
      fetchTranscription(parseInt(id));
    }
  }, [id]);

  // Auto-refresh for pending/processing transcriptions
  useEffect(() => {
    if (!transcription) return;
    
    const isPending = transcription.status === 'pending' || transcription.status === 'processing';
    if (!isPending) return;

    console.log('Polling enabled - Status:', transcription.status, 'Progress:', transcription.progress);
    
    const interval = setInterval(() => {
      console.log('Polling... Fetching transcription', transcription.id);
      fetchTranscription(transcription.id);
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [transcription?.status, transcription?.id]);

  const fetchTranscription = async (transcriptionId: number) => {
    try {
      if (loading) setLoading(true);
      const data = await transcriptionService.getById(transcriptionId);
      console.log('Transcription fetched:', data);
      setTranscription(data);
    } catch (err: any) {
      console.error('Failed to fetch transcription:', err);
      setError('Transkript yüklenemedi.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (format: 'txt' | 'json' | 'srt') => {
    if (!transcription) return;

    try {
      const blob = await transcriptionService.downloadText(transcription.id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${transcription.filename}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('İndirme başarısız oldu.');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50';
      case 'processing': return 'text-blue-600 bg-blue-50';
      case 'pending': return 'text-yellow-600 bg-yellow-50';
      case 'failed': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return 'Tamamlandı';
      case 'processing': return 'İşleniyor';
      case 'pending': return 'Bekliyor';
      case 'failed': return 'Başarısız';
      default: return status;
    }
  };

  if (loading && !transcription) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Yükleniyor...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (error || !transcription) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <div className="text-6xl mb-4">❌</div>
            <p className="text-gray-600 mb-4">{error || 'Transkript bulunamadı'}</p>
            <button
              onClick={() => navigate('/transcriptions')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg"
            >
              Geri Dön
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  const isProcessing = transcription.status === 'pending' || transcription.status === 'processing';

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate('/transcriptions')}
            className="mb-4 text-blue-600 hover:text-blue-700 flex items-center"
          >
            ← Geri
          </button>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">{transcription.filename}</h1>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span className={`px-3 py-1 rounded-full font-medium ${getStatusColor(transcription.status)}`}>
                  {getStatusText(transcription.status)}
                </span>
                {transcription.duration && (
                  <span>Süre: {Math.round(transcription.duration)}s</span>
                )}
                <span>Boyut: {(transcription.file_size / 1024 / 1024).toFixed(2)} MB</span>
              </div>
            </div>
            {transcription.status === 'completed' && (
              <div className="flex gap-2">
                <button
                  onClick={() => handleDownload('txt')}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  TXT İndir
                </button>
                <button
                  onClick={() => handleDownload('json')}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg"
                >
                  JSON İndir
                </button>
                <button
                  onClick={() => handleDownload('srt')}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg"
                >
                  SRT İndir
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Progress Bar for Processing */}
        {isProcessing && (
          <div className="mb-6 bg-white rounded-lg shadow p-6">
            <div className="mb-2 flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">
                {transcription.status === 'pending' ? 'Bekliyor...' : 'İşleniyor...'}
              </span>
              <span className="text-sm font-medium text-gray-700">
                {transcription.progress || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${transcription.progress || 0}%` }}
              ></div>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              🔄 Sayfa otomatik olarak güncelleniyor... (her 3 saniyede bir)
            </p>
          </div>
        )}

        {/* Tabs */}
        {transcription.status === 'completed' && (
          <>
            <div className="mb-6 border-b border-gray-200">
              <nav className="flex gap-8">
                <button
                  onClick={() => setActiveTab('text')}
                  className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'text'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Transkript
                </button>
                {transcription.enhanced_text && (
                  <button
                    onClick={() => setActiveTab('enhanced')}
                    className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'enhanced'
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Geliştirilmiş
                  </button>
                )}
                {transcription.summary && (
                  <button
                    onClick={() => setActiveTab('summary')}
                    className={`pb-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === 'summary'
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Özet
                  </button>
                )}
              </nav>
            </div>

            {/* Content */}
            <div className="bg-white rounded-lg shadow p-6">
              {activeTab === 'text' && (
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-gray-800">
                    {transcription.text || 'Transkript metni bulunamadı'}
                  </pre>
                </div>
              )}
              {activeTab === 'enhanced' && transcription.enhanced_text && (
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-gray-800">
                    {transcription.enhanced_text}
                  </pre>
                </div>
              )}
              {activeTab === 'summary' && transcription.summary && (
                <div className="prose max-w-none">
                  <p className="text-gray-800">{transcription.summary}</p>
                </div>
              )}
            </div>
          </>
        )}

        {/* Failed Status */}
        {transcription.status === 'failed' && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <div className="text-6xl mb-4">❌</div>
            <h3 className="text-xl font-semibold text-red-800 mb-2">
              Transkripsiyon Başarısız
            </h3>
            <p className="text-red-600">
              {transcription.error_message || 'Bir hata oluştu'}
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};
"""

with open(page_file, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ TranscriptionDetailPage.tsx düzeltildi!")
print("\n📍 Yeni Özellikler:")
print("   • ⏱️  Status polling: pending/processing ise her 3 saniyede günceller")
print("   • 📊 Progress bar: transcription.progress gösterir")
print("   • 🔄 Otomatik refresh: status değişince polling durur")
print("   • 🎨 Status badge: renkli status göstergesi")
print("   • 📥 Download buttons: sadece completed'de görünür")
print("   • ❌ Failed status: hata mesajı gösterir")
print("\n🔄 Vite HMR değişikliği otomatik algılayacak")
print("\n🎯 Şimdi bir dosya yükleyin ve detail sayfasını açın!")
