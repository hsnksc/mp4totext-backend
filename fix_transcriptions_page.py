import os

web_dir = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web"
page_file = os.path.join(web_dir, "src", "pages", "TranscriptionsPage.tsx")

content = """import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { TranscriptionCard } from '../components/TranscriptionCard';
import { transcriptionService } from '../services/transcriptionService';
import type { Transcription } from '../types';

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
      console.log('TranscriptionsPage - API Response:', data);
      
      // Backend returns { items: [...] } or just [...]
      const transcriptionArray = Array.isArray(data) ? data : (data.items || []);
      
      setTranscriptions(transcriptionArray);
      setError('');
    } catch (err: any) {
      console.error('Failed to fetch transcriptions:', err);
      setError('Transkriptler yüklenemedi. Lütfen tekrar deneyin.');
      setTranscriptions([]);
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
            <div className="text-6xl mb-4">📋</div>
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

with open(page_file, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ TranscriptionsPage.tsx düzeltildi!")
print("   • API response handling eklendi (DashboardPage gibi)")
print("   • Array.isArray() kontrolü eklendi")
print("   • data.items fallback eklendi")
print("   • Console.log eklendi (debugging için)")
print("   • Import path düzeltildi: '../types/transcription' -> '../types'")
print("\n🔄 Vite HMR değişikliği otomatik algılayacak")
