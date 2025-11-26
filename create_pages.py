#!/usr/bin/env python3
"""
Transcription List ve Dashboard güncellemesi
"""
import os

WEB_SRC = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web\src"

FILES = {
    # PAGES - TranscriptionsPage
    "pages/TranscriptionsPage.tsx": """import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
    </div>
  );
};
""",

    # PAGES - TranscriptionDetailPage
    "pages/TranscriptionDetailPage.tsx": """import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !transcription) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
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
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
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

        {/* Tabs */}
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

        {/* Speakers */}
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
    </div>
  );
};
""",

    # Updated DashboardPage with navigation
    "pages/DashboardPage.tsx": """import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types/transcription';

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
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

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-800">🎙️ MP4toText</h1>
            <span className="text-sm text-gray-500">Dashboard</span>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-800">{user?.full_name || user?.username}</p>
              <p className="text-xs text-gray-500">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors text-sm font-medium"
            >
              Çıkış
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
      </main>
    </div>
  );
};
""",
}

print("🔧 Transcription sayfaları oluşturuluyor...\n")
for path, content in FILES.items():
    full_path = os.path.join(WEB_SRC, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {path}")

print("\n✅ Tüm dosyalar başarıyla oluşturuldu!")
