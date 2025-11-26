import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Shield, Users, DollarSign, ArrowLeft, Edit2, Save, X, Server } from 'lucide-react';
import { TranscriptionProviderSettings } from '../components/TranscriptionProviderSettings';

interface PricingConfig {
  transcription_base: number;
  speaker_recognition: number;
  youtube_download: number;
  ai_enhancement: number;
  lecture_notes: number;
  custom_prompt: number;
  exam_questions: number;
  translation: number;
  tavily_web_search: number; // New: Tavily web search cost
}

interface User {
  id: number;
  username: string;
  email: string;
  credits: number;
  is_superuser: boolean;
  created_at: string;
}

const AdminDashboardPage = () => {
  const navigate = useNavigate();
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'pricing' | 'users' | 'models' | 'provider'>('pricing');
  const [pricing, setPricing] = useState<PricingConfig | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingPricing, setEditingPricing] = useState(false);
  const [editedPricing, setEditedPricing] = useState<PricingConfig | null>(null);
  const [saving, setSaving] = useState(false);
  
  // AI Models state
  interface AIModel {
    id: number;
    model_key: string;
    model_name: string;
    provider: string;
    credit_multiplier: number;
    description: string | null;
    is_active: boolean;
    is_default: boolean;
  }
  const [aiModels, setAiModels] = useState<AIModel[]>([]);
  const [editingModels, setEditingModels] = useState(false);
  const [editedModels, setEditedModels] = useState<AIModel[]>([]);

  // Check if user is admin
  useEffect(() => {
    if (!user?.is_superuser) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  useEffect(() => {
    if (activeTab === 'pricing') {
      fetchPricing();
    } else if (activeTab === 'users') {
      fetchUsers();
    } else if (activeTab === 'models') {
      fetchAIModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const fetchPricing = async () => {
    try {
      setLoading(true);
      // /credits/pricing returns object with snake_case keys
      const response = await api.get<{
        transcription_per_minute: number;
        speaker_recognition_per_minute: number;
        youtube_download: number;
        ai_enhancement: number;
        lecture_notes: number;
        custom_prompt: number;
        exam_questions: number;
        translation: number;
        tavily_web_search?: number; // Optional, may not exist yet
      }>('/credits/pricing');
      
      // Map to our PricingConfig format
      const pricingData: PricingConfig = {
        transcription_base: response.data.transcription_per_minute,
        speaker_recognition: response.data.speaker_recognition_per_minute,
        youtube_download: response.data.youtube_download,
        ai_enhancement: response.data.ai_enhancement,
        lecture_notes: response.data.lecture_notes,
        custom_prompt: response.data.custom_prompt,
        exam_questions: response.data.exam_questions,
        translation: response.data.translation,
        tavily_web_search: response.data.tavily_web_search || 5, // Default 5 credits
      };
      
      setPricing(pricingData);
      setEditedPricing(pricingData);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Fiyatlandırma bilgisi alınamadı');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      setLoading(true);
      // TODO: Create admin users endpoint
      // For now, show placeholder
      setUsers([]);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Kullanıcı listesi alınamadı');
    } finally {
      setLoading(false);
    }
  };

  const fetchAIModels = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get<AIModel[]>('/credits/admin/models');
      setAiModels(response.data);
      setEditedModels(JSON.parse(JSON.stringify(response.data))); // Deep copy
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'AI modelleri alınamadı');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveModels = async () => {
    setSaving(true);
    setError(null);
    try {
      // Update each modified model
      for (const model of editedModels) {
        await api.put(`/credits/admin/models/${model.id}`, {
          credit_multiplier: model.credit_multiplier,
          description: model.description,
          is_active: model.is_active,
          is_default: model.is_default
        });
      }
      
      await fetchAIModels(); // Refresh
      setEditingModels(false);
      alert('✅ AI model fiyatlandırması güncellendi');
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Güncelleme başarısız');
    } finally {
      setSaving(false);
    }
  };

  const handleSavePricing = async () => {
    if (!editedPricing) return;

    setSaving(true);
    try {
      // Backend expects: {"configs": {"transcription_base": 15, ...}}
      const configs: { [key: string]: number } = {
        transcription_base: editedPricing.transcription_base,
        speaker_recognition: editedPricing.speaker_recognition,
        youtube_download: editedPricing.youtube_download,
        ai_enhancement: editedPricing.ai_enhancement,
        lecture_notes: editedPricing.lecture_notes,
        custom_prompt: editedPricing.custom_prompt,
        exam_questions: editedPricing.exam_questions,
        translation: editedPricing.translation,
        tavily_web_search: editedPricing.tavily_web_search,
      };

      const response = await api.put<{
        success: boolean;
        updated_count: number;
        message: string;
      }>('/credits/admin/pricing', { configs });

      setPricing(editedPricing);
      setEditingPricing(false);
      
      // Show success message
      alert(`✅ ${response.data.message}`);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string | { message: string; errors: string[] } } } };
      const detail = error.response?.data?.detail;
      
      if (typeof detail === 'object' && 'message' in detail) {
        setError(`${detail.message}\n${detail.errors.join('\n')}`);
      } else {
        setError(typeof detail === 'string' ? detail : 'Güncelleme başarısız');
      }
    } finally {
      setSaving(false);
    }
  };

  const pricingFields = [
    { key: 'transcription_base', label: 'Transkripsiyon (dakika başı±)', unit: 'kredi/dk' },
    { key: 'speaker_recognition', label: 'Konuşmacı Tanıma (ek)', unit: 'kredi/dk' },
    { key: 'youtube_download', label: 'YouTube İndirme', unit: 'kredi' },
    { key: 'ai_enhancement', label: 'AI Enhancement', unit: 'kredi' },
    { key: 'lecture_notes', label: 'Ders Notları±', unit: 'kredi' },
    { key: 'custom_prompt', label: 'Ã–zel Prompt', unit: 'kredi' },
    { key: 'exam_questions', label: 'Sınav Soruları', unit: 'kredi' },
    { key: 'translation', label: 'Ã‡eviri', unit: 'kredi' },
    { key: 'tavily_web_search', label: 'Tavily Web Search', unit: 'kredi' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0e27] via-[#1e2749] to-[#0a0e27]">
      {/* Navbar */}
      <nav className="glass-effect border-b border-slate-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Shield className="w-6 h-6 text-red-400" />
              <span className="gradient-text">{i18n.language === 'tr' ? 'Admin Panel' : 'Admin Panel'}</span>
            </h1>
            <button 
              onClick={() => navigate('/dashboard')} 
              className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              {i18n.language === 'tr' ? 'Dashboard' : 'Dashboard'}
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Tabs */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setActiveTab('pricing')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              activeTab === 'pricing'
                ? 'btn-gradient text-white'
                : 'glass-effect text-slate-300 hover:text-white'
            }`}
          >
            <DollarSign className="w-5 h-5" />
            {i18n.language === 'tr' ? 'Fiyatlandırma' : 'Pricing'}
          </button>
          <button
            onClick={() => setActiveTab('models')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              activeTab === 'models'
                ? 'btn-gradient text-white'
                : 'glass-effect text-slate-300 hover:text-white'
            }`}
          >
            ðŸ¤– {i18n.language === 'tr' ? 'AI Modelleri' : 'AI Models'}
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              activeTab === 'users'
                ? 'btn-gradient text-white'
                : 'glass-effect text-slate-300 hover:text-white'
            }`}
          >
            <Users className="w-5 h-5" />
            {i18n.language === 'tr' ? 'Kullanıcılar' : 'Users'}
          </button>
          <button
            onClick={() => setActiveTab('provider')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              activeTab === 'provider'
                ? 'btn-gradient text-white'
                : 'glass-effect text-slate-300 hover:text-white'
            }`}
          >
            <Server className="w-5 h-5" />
            {i18n.language === 'tr' ? 'Provider' : 'Provider'}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="glass-effect rounded-2xl p-6 border-2 border-red-500/50 mb-8 fade-in">
            <div className="flex items-center gap-3 text-red-400">
              <span className="text-2xl">âš ï¸</span>
              <div>
                <p className="font-bold">Hata</p>
                <p className="text-sm text-slate-400">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
            <p className="text-slate-400">Yükleniyor...</p>
          </div>
        )}

        {/* Pricing Tab */}
        {activeTab === 'pricing' && pricing && !loading && (
          <div className="glass-effect rounded-2xl overflow-hidden fade-in">
            <div className="p-6 border-b border-slate-700 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {i18n.language === 'tr' ? 'Kredi FiyatlandırmasÄ±' : 'Credit Pricing'}
                </h2>
                <p className="text-slate-400 text-sm mt-1">
                  {i18n.language === 'tr' ? 'İşlem başı±na kredi maliyetlerini yönetin' : 'Manage credit costs per operation'}
                </p>
              </div>
              {!editingPricing ? (
                <button
                  onClick={() => setEditingPricing(true)}
                  className="btn-gradient text-white px-4 py-2 rounded-xl flex items-center gap-2"
                >
                  <Edit2 className="w-4 h-4" />
                  {i18n.language === 'tr' ? 'Düzenle' : 'Edit'}
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={handleSavePricing}
                    disabled={saving}
                    className="bg-green-500/20 text-green-400 border border-green-500/50 px-4 py-2 rounded-xl flex items-center gap-2 hover:bg-green-500/30 transition-all"
                  >
                    <Save className="w-4 h-4" />
                    {saving 
                      ? (i18n.language === 'tr' ? 'Kaydediliyor...' : 'Saving...') 
                      : (i18n.language === 'tr' ? 'Kaydet' : 'Save')}
                  </button>
                  <button
                    onClick={() => {
                      setEditingPricing(false);
                      setEditedPricing(pricing);
                    }}
                    className="bg-red-500/20 text-red-400 border border-red-500/50 px-4 py-2 rounded-xl flex items-center gap-2 hover:bg-red-500/30 transition-all"
                  >
                    <X className="w-4 h-4" />
                    {i18n.language === 'tr' ? 'Ä°ptal' : 'Cancel'}
                  </button>
                </div>
              )}
            </div>

            <div className="p-6 space-y-4">
              {pricingFields.map(({ key, label, unit }) => (
                <div key={key} className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
                  <div className="flex-1">
                    <label className="text-white font-medium block mb-1">{label}</label>
                    <span className="text-slate-400 text-sm">{unit}</span>
                  </div>
                  {editingPricing ? (
                    <input
                      type="number"
                      value={editedPricing?.[key as keyof PricingConfig] || 0}
                      onChange={(e) => {
                        if (editedPricing) {
                          setEditedPricing({
                            ...editedPricing,
                            [key]: parseInt(e.target.value) || 0
                          });
                        }
                      }}
                      className="w-24 px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-right"
                      min="0"
                    />
                  ) : (
                    <div className="text-2xl font-bold text-indigo-400">
                      {pricing[key as keyof PricingConfig]}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Models Tab */}
        {activeTab === 'models' && !loading && (
          <div className="glass-effect rounded-2xl overflow-hidden fade-in">
            <div className="p-6 border-b border-slate-700 flex justify-between items-center">
              <div>
                <h2 className="text-2xl font-bold text-white">AI Model FiyatlandırmasÄ±</h2>
                <p className="text-slate-400 text-sm mt-1">
                  Her AI modeli için kredi çarpanlarını yönetin
                </p>
              </div>
              {!editingModels ? (
                <button
                  onClick={() => setEditingModels(true)}
                  className="btn-gradient text-white px-4 py-2 rounded-xl flex items-center gap-2"
                >
                  <Edit2 className="w-4 h-4" />
                  Düzenle
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    onClick={handleSaveModels}
                    disabled={saving}
                    className="bg-green-500/20 text-green-400 border border-green-500/50 px-4 py-2 rounded-xl flex items-center gap-2 hover:bg-green-500/30 transition-all"
                  >
                    <Save className="w-4 h-4" />
                    {saving ? 'Kaydediliyor...' : 'Kaydet'}
                  </button>
                  <button
                    onClick={() => {
                      setEditingModels(false);
                      fetchAIModels();
                    }}
                    className="bg-red-500/20 text-red-400 border border-red-500/50 px-4 py-2 rounded-xl flex items-center gap-2 hover:bg-red-500/30 transition-all"
                  >
                    <X className="w-4 h-4" />
                    Ä°ptal
                  </button>
                </div>
              )}
            </div>

            <div className="p-6 space-y-4">
              {editedModels.map((model, index) => (
                <div key={model.id} className="p-4 bg-white/5 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-white font-bold text-lg">{model.model_name}</h3>
                      <p className="text-slate-400 text-sm">
                        {model.provider.toUpperCase()} â€¢ {model.model_key}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      {editingModels ? (
                        <>
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={model.is_active}
                              onChange={(e) => {
                                const updated = [...editedModels];
                                updated[index].is_active = e.target.checked;
                                setEditedModels(updated);
                              }}
                              className="w-4 h-4 rounded"
                            />
                            <span className="text-slate-400">Aktif</span>
                          </label>
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={model.is_default}
                              onChange={(e) => {
                                const updated = [...editedModels];
                                // If setting this as default, unset others
                                if (e.target.checked) {
                                  updated.forEach((m, i) => {
                                    m.is_default = i === index;
                                  });
                                } else {
                                  updated[index].is_default = false;
                                }
                                setEditedModels(updated);
                              }}
                              className="w-4 h-4 rounded"
                            />
                            <span className="text-slate-400">Varsayılan</span>
                          </label>
                        </>
                      ) : (
                        <div className="flex gap-2">
                          {model.is_active && (
                            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full border border-green-500/50">
                              Aktif
                            </span>
                          )}
                          {model.is_default && (
                            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full border border-blue-500/50">
                              Varsayılan
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-slate-400 text-sm block mb-2">
                        Kredi Çarpanı (Base Ã— ?)
                      </label>
                      {editingModels ? (
                        <input
                          type="number"
                          step="0.1"
                          value={model.credit_multiplier}
                          onChange={(e) => {
                            const updated = [...editedModels];
                            updated[index].credit_multiplier = parseFloat(e.target.value) || 0;
                            setEditedModels(updated);
                          }}
                          className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white"
                          min="0"
                        />
                      ) : (
                        <div className="text-2xl font-bold text-indigo-400">
                          {model.credit_multiplier}x
                        </div>
                      )}
                    </div>
                    <div>
                      <label className="text-slate-400 text-sm block mb-2">
                        Ã–rnek Maliyet (30 kredi base)
                      </label>
                      <div className="text-2xl font-bold text-green-400">
                        {(30 * model.credit_multiplier).toFixed(2)} kredi
                      </div>
                    </div>
                  </div>

                  {editingModels && (
                    <div>
                      <label className="text-slate-400 text-sm block mb-2">Açıklama</label>
                      <textarea
                        value={model.description || ''}
                        onChange={(e) => {
                          const updated = [...editedModels];
                          updated[index].description = e.target.value;
                          setEditedModels(updated);
                        }}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm"
                        rows={2}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && !loading && (
          <div className="glass-effect rounded-2xl p-6 fade-in">
            <h2 className="text-2xl font-bold text-white mb-4">Kullanıcı Yönetimi</h2>
            <div className="text-center py-12">
              <div className="text-6xl mb-4">ðŸ‘¥</div>
              <h3 className="text-xl font-bold text-white mb-2">Yakında</h3>
              <p className="text-slate-400">
                Kullanıcı yönetimi özellikleri yakında eklenecek
              </p>
            </div>
          </div>
        )}


        {/* Provider Tab */}
        {activeTab === 'provider' && (
          <div className="fade-in">
            <TranscriptionProviderSettings />
          </div>
        )}
        {/* Demo Notice */}
        <div className="mt-8 glass-effect rounded-2xl p-6 border border-yellow-500/30">
          <div className="flex items-start gap-3">
            <span className="text-2xl">â„¹ï¸</span>
            <div>
              <p className="text-yellow-300 font-bold mb-2">Demo Modu</p>
              <p className="text-slate-400 text-sm">
                Bu admin panel demo amaÃ§lÄ±dÄ±r. Fiyatlandırma gÃ¼ncellemeleri gerÃ§ek veritabanÄ±na kaydedilmez.
                GerÃ§ek Ã¼retim ortamÄ±nda admin API endpoint'leri kullanÄ±lacaktÄ±r.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardPage;





