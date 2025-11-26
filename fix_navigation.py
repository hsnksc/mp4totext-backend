#!/usr/bin/env python3
"""
Navigation ve Layout düzeltmesi
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

# Create a Layout component with navigation
LAYOUT_FILE = """import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <Link to="/dashboard" className="flex items-center space-x-2">
                <span className="text-2xl">🎙️</span>
                <span className="text-xl font-bold text-gray-800">MP4toText</span>
              </Link>
              
              <nav className="flex space-x-4">
                <Link
                  to="/dashboard"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/dashboard')
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  Ana Sayfa
                </Link>
                <Link
                  to="/upload"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/upload')
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  Dosya Yükle
                </Link>
                <Link
                  to="/transcriptions"
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive('/transcriptions')
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  Transkriptlerim
                </Link>
              </nav>
            </div>

            <div className="flex items-center space-x-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-800">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Çıkış
              </button>
            </div>
          </div>
        </div>
      </header>

      <main>{children}</main>
    </div>
  );
};
"""

# Update DashboardPage to use Layout and fix navigation
DASHBOARD_FILE = """import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types/transcription';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    processing: 0,
    completed: 0,
  });

  useEffect(() => {
    fetchTranscriptions();
  }, []);

  const fetchTranscriptions = async () => {
    try {
      const data = await transcriptionService.getAll(1, 10);
      setTranscriptions(data);
      
      // Calculate stats
      setStats({
        total: data.length,
        processing: data.filter(t => t.status === 'processing' || t.status === 'pending').length,
        completed: data.filter(t => t.status === 'completed').length,
      });
    } catch (err) {
      console.error('Failed to fetch transcriptions:', err);
    }
  };

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Hoş Geldiniz! 👋</h2>
          <p className="text-gray-600">
            MP4toText platformuna hoş geldiniz. Ses ve video dosyalarınızı kolayca metne dönüştürün.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Toplam Transkript</p>
                <p className="text-3xl font-bold text-gray-800">{stats.total}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-2xl">📝</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">İşleniyor</p>
                <p className="text-3xl font-bold text-gray-800">{stats.processing}</p>
              </div>
              <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
                <span className="text-2xl">⏳</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Tamamlanan</p>
                <p className="text-3xl font-bold text-gray-800">{stats.completed}</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                <span className="text-2xl">✅</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Hızlı İşlemler</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button 
              onClick={() => navigate('/upload')}
              className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
            >
              <div className="text-2xl mb-2">📤</div>
              <p className="font-medium text-gray-800">Dosya Yükle</p>
              <p className="text-sm text-gray-600">Ses veya video dosyanızı yükleyin</p>
            </button>

            <button 
              onClick={() => navigate('/transcriptions')}
              className="p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
            >
              <div className="text-2xl mb-2">📋</div>
              <p className="font-medium text-gray-800">Transkriptlerim</p>
              <p className="text-sm text-gray-600">Tüm transkriptlerinizi görüntüleyin</p>
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
};
"""

# Update UploadPage to use Layout
UPLOAD_FILE = """import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { FileUpload } from '../components/FileUpload';
import { ProgressBar } from '../components/ProgressBar';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types/transcription';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState(false);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError('');
    setSuccess(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setError('');
      setUploadProgress(0);

      await transcriptionService.upload(selectedFile, (progress) => {
        setUploadProgress(progress.percentage);
      });

      setSuccess(true);
      setUploadProgress(100);
      
      // Redirect to transcriptions after 2 seconds
      setTimeout(() => {
        navigate('/transcriptions');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Yükleme başarısız oldu. Lütfen tekrar deneyin.');
      setUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploading(false);
    setUploadProgress(0);
    setError('');
    setSuccess(false);
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Dosya Yükle</h1>
          <p className="text-gray-600">
            Ses veya video dosyanızı yükleyin ve transkripsiyon işlemini başlatın
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          {!selectedFile && !uploading && !success && (
            <FileUpload onFileSelect={handleFileSelect} />
          )}

          {selectedFile && !uploading && !success && (
            <div className="space-y-4">
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-800">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    onClick={handleReset}
                    className="text-red-600 hover:text-red-700 text-sm font-medium"
                  >
                    Kaldır
                  </button>
                </div>
              </div>

              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                  {error}
                </div>
              )}

              <button
                onClick={handleUpload}
                className="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                Yüklemeyi Başlat
              </button>
            </div>
          )}

          {uploading && (
            <div className="space-y-4">
              <div className="text-center mb-4">
                <div className="text-4xl mb-2">⏳</div>
                <p className="text-lg font-medium text-gray-800">Dosya yükleniyor...</p>
                <p className="text-sm text-gray-600">Lütfen bekleyin</p>
              </div>
              <ProgressBar progress={uploadProgress} />
            </div>
          )}

          {success && (
            <div className="text-center py-8">
              <div className="text-6xl mb-4">✅</div>
              <h3 className="text-xl font-semibold text-gray-800 mb-2">
                Yükleme Başarılı!
              </h3>
              <p className="text-gray-600 mb-4">
                Dosyanız işleme alındı. Transkript hazır olduğunda listelenecektir.
              </p>
              <p className="text-sm text-gray-500">
                Transkriptler sayfasına yönlendiriliyorsunuz...
              </p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};
"""

# Update TranscriptionsPage to use Layout
TRANSCRIPTIONS_FILE = """import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { TranscriptionCard } from '../components/TranscriptionCard';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types/transcription';

export const TranscriptionsPage: React.FC = () => {
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchTranscriptions();
  }, []);

  const fetchTranscriptions = async () => {
    try {
      setLoading(true);
      const data = await transcriptionService.getAll();
      setTranscriptions(data);
    } catch (err: any) {
      setError('Transkriptler yüklenemedi. Lütfen tekrar deneyin.');
    } finally {
      setLoading(false);
    }
  };

  const handleView = (id: number) => {
    navigate(`/transcriptions/${id}`);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Bu transkripti silmek istediğinizden emin misiniz?')) {
      return;
    }

    try {
      await transcriptionService.delete(id);
      setTranscriptions(transcriptions.filter(t => t.id !== id));
    } catch (err: any) {
      alert('Silme işlemi başarısız oldu.');
    }
  };

  if (loading) {
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

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Transkriptlerim</h1>
            <p className="text-gray-600">Tüm transkriptlerinizi görüntüleyin ve yönetin</p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            + Yeni Yükle
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {transcriptions.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <div className="text-6xl mb-4">📝</div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              Henüz transkript yok
            </h3>
            <p className="text-gray-600 mb-6">
              İlk transkriptinizi oluşturmak için bir dosya yükleyin
            </p>
            <button
              onClick={() => navigate('/upload')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
            >
              Dosya Yükle
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {transcriptions.map((transcription) => (
              <TranscriptionCard
                key={transcription.id}
                transcription={transcription}
                onView={handleView}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};
"""

# Update TranscriptionDetailPage to use Layout
DETAIL_FILE = """import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types/transcription';

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

  const fetchTranscription = async (transcriptionId: number) => {
    try {
      setLoading(true);
      const data = await transcriptionService.getById(transcriptionId);
      setTranscription(data);
    } catch (err: any) {
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

  if (loading) {
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

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6">
          <button
            onClick={() => navigate('/transcriptions')}
            className="text-blue-600 hover:text-blue-700 font-medium mb-4"
          >
            ← Geri
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                {transcription.filename}
              </h1>
              <p className="text-gray-600">
                {new Date(transcription.created_at).toLocaleString('tr-TR')}
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => handleDownload('txt')}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm"
              >
                TXT İndir
              </button>
              <button
                onClick={() => handleDownload('json')}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm"
              >
                JSON İndir
              </button>
              <button
                onClick={() => handleDownload('srt')}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm"
              >
                SRT İndir
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow mb-6">
          <div className="border-b border-gray-200">
            <div className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('text')}
                className={`py-4 font-medium border-b-2 transition-colors ${
                  activeTab === 'text'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-800'
                }`}
              >
                Transkript
              </button>
              {transcription.enhanced_text && (
                <button
                  onClick={() => setActiveTab('enhanced')}
                  className={`py-4 font-medium border-b-2 transition-colors ${
                    activeTab === 'enhanced'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-800'
                  }`}
                >
                  AI Gelişmiş
                </button>
              )}
              {transcription.summary && (
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`py-4 font-medium border-b-2 transition-colors ${
                    activeTab === 'summary'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-800'
                  }`}
                >
                  Özet
                </button>
              )}
            </div>
          </div>

          <div className="p-6">
            {activeTab === 'text' && (
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-gray-800">
                  {transcription.text || 'Transkript henüz hazır değil...'}
                </p>
              </div>
            )}

            {activeTab === 'enhanced' && transcription.enhanced_text && (
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-gray-800">
                  {transcription.enhanced_text}
                </p>
              </div>
            )}

            {activeTab === 'summary' && transcription.summary && (
              <div className="prose max-w-none">
                <p className="whitespace-pre-wrap text-gray-800">
                  {transcription.summary}
                </p>
              </div>
            )}
          </div>
        </div>

        {transcription.speakers && transcription.speakers.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">
              Konuşmacılar
            </h2>
            <div className="space-y-4">
              {transcription.speakers.map((speaker, index) => (
                <div key={index} className="border-l-4 border-blue-500 pl-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-gray-800">
                      {speaker.speaker}
                    </span>
                    <span className="text-sm text-gray-500">
                      {Math.floor(speaker.start)}s - {Math.floor(speaker.end)}s
                    </span>
                  </div>
                  <p className="text-gray-700">{speaker.text}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
"""

FILES = {
    "components/Layout.tsx": LAYOUT_FILE,
    "pages/DashboardPage.tsx": DASHBOARD_FILE,
    "pages/UploadPage.tsx": UPLOAD_FILE,
    "pages/TranscriptionsPage.tsx": TRANSCRIPTIONS_FILE,
    "pages/TranscriptionDetailPage.tsx": DETAIL_FILE,
}

print("🔧 Layout ve Navigation oluşturuluyor...\n")
for path, content in FILES.items():
    full_path = os.path.join(WEB_SRC, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {path}")

print("\n✅ Tüm dosyalar başarıyla güncellendi!")
print("\n📍 Yeni Özellikler:")
print("   • Üst menü navigation bar (tüm sayfalarda)")
print("   • Aktif sayfa vurgulama")
print("   • Upload butonu çalışır durumda")
print("   • Tutarlı layout tüm sayfalarda")
