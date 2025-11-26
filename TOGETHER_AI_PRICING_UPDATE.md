# Together AI Fiyatlandırma Güncellemesi

## 📊 Güncelleme Özeti

**Tarih**: 3 Kasım 2025  
**Güncellenen Modeller**: 19 adet  
**Bulunamayan Modeller**: 7 adet (veritabanında yok)

## 🎯 Baz Fiyatlandırma

- **Referans Model**: Gemini 2.5-flash = 1.0x = 20 kredi
- **API Maliyeti Bazı**: $0.30 / 1M token (input+output ortalaması)
- **Formül**: `credit_multiplier = (model_avg_cost) / 0.30`

## 💰 Fiyat Kategorileri

### 🆓 ÜCRETSİZ (0.0x)
- **meta-llama/Llama-3.3-70B-Instruct-Turbo-Free**: 0 kredi

### 💚 ULTRA UCUZ (0.1-0.4x) - 2-8 kredi
- **google/gemma-3n-E4B-it**: 2 kredi ($0.02/$0.04)
- **openai/gpt-oss-20b**: 8 kredi ($0.05/$0.20)

### 🟢 UCUZ (0.5-0.9x) - 10-18 kredi
- **llama-3.3-70b-together**: 10 kredi
- **meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo**: 12 kredi ($0.18)

### 🔵 UYGUN (1.0-1.5x) - 20-30 kredi
- **Qwen/Qwen2.5-7B-Instruct-Turbo**: 20 kredi ($0.30)
- **mistralai/Magistral-Small-2506**: 20 kredi
- **openai/gpt-oss-120b**: 24 kredi ($0.15/$0.60)
- **meta-llama/Llama-4-Scout-17B-16E-Instruct**: 26 kredi ($0.18/$0.59)
- **llama-3.1-405b-instruct-turbo**: 30 kredi

### 🟡 STANDART (1.6-2.5x) - 32-50 kredi
- **meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8**: 38 kredi ($0.27/$0.85)

### 🟠 PREMİUM (2.6-3.5x) - 52-70 kredi
- **mistralai/Mistral-Small-24B-Instruct-2501**: 54 kredi ($0.80)
- **meta-llama/Llama-3.3-70B-Instruct-Turbo**: 58 kredi ($0.88)
- **arcee-ai/virtuoso-medium-v2**: 64 kredi ($0.75/$1.20)

### 🔴 FLAGSHIP (3.6x+) - 76-334 kredi
- **deepseek-ai/DeepSeek-V3.1**: 76 kredi ($0.60/$1.70)
- **Qwen/Qwen2.5-72B-Instruct-Turbo**: 80 kredi ($1.20)
- **Qwen3-235B-A22B-Instruct-2507**: 122 kredi ($0.65/$3.00)
- **Qwen3-235B-A22B-Thinking-2507**: 122 kredi ($0.65/$3.00)
- **DeepSeek-R1-Distill-Llama-70B**: 134 kredi ($2.00)
- **moonshotai/Kimi-K2-Instruct-0905**: 134 kredi ($1.00/$3.00)
- **Meta-Llama-3.1-405B-Instruct-Turbo**: 234 kredi ($3.50)
- **deepseek-ai/DeepSeek-R1**: 334 kredi ($3.00/$7.00) ⚡ EN PAHALI

## 📈 Önemli Değişiklikler

### 🔺 Fiyatı Artanlar (Gerçek API fiyatlarına göre düzeltme)
- **Qwen/Qwen2.5-7B-Instruct-Turbo**: 6 → 20 kredi (+233%)
- **Mistral-Small-24B**: 16 → 54 kredi (+237%)
- **Llama-3.3-70B-Instruct-Turbo**: 36 → 58 kredi (+61%)
- **Qwen2.5-72B-Instruct-Turbo**: 24 → 80 kredi (+233%)
- **arcee-ai/virtuoso-medium-v2**: 24 → 64 kredi (+167%)
- **DeepSeek-R1-Distill-Llama-70B**: 30 → 134 kredi (+347%)
- **DeepSeek-V3.1**: 56 → 76 kredi (+36%)
- **DeepSeek-R1**: 60 → 334 kredi (+457%) 🚀
- **Meta-Llama-3.1-405B**: 70 → 234 kredi (+234%)
- **Qwen3-235B**: 64/70 → 122 kredi (+74%)
- **Kimi-K2**: 80 → 134 kredi (+68%)

### 🔻 Fiyatı Düşenler
- **Llama-3.3-70B-Instruct-Turbo-Free**: 10 → 0 kredi (ÜCRETSİZ!) 🎉
- **google/gemma-3n-E4B-it**: 12 → 2 kredi (-83%)
- **openai/gpt-oss-20b**: 14 → 8 kredi (-43%)
- **openai/gpt-oss-120b**: 30 → 24 kredi (-20%)
- **Llama-4-Scout**: 40 → 26 kredi (-35%)
- **Llama-4-Maverick**: 50 → 38 kredi (-24%)

### ⚖️ Sabit Kalanlar
- **Meta-Llama-3.1-8B-Instruct-Turbo**: 8 → 12 kredi (hafif artış)

## 🎯 Önerilen Modeller

### 💎 En İyi Değer (Performance/Price)
1. **Llama-3.3-70B-Instruct-Turbo-Free** - 0 kredi (70B parametre, ÜCRETSİZ!)
2. **openai/gpt-oss-20b** - 8 kredi (20B parametre)
3. **Meta-Llama-3.1-8B-Instruct-Turbo** - 12 kredi (8B parametre)

### ⚡ Hız + Kalite
- **openai/gpt-oss-120b** - 24 kredi (120B parametre, makul fiyat)
- **Llama-4-Scout** - 26 kredi (17Bx16E MoE)

### 🧠 Maksimum Performans
- **DeepSeek-R1** - 334 kredi (En gelişmiş reasoning model)
- **Meta-Llama-3.1-405B** - 234 kredi (405B parametre)
- **Qwen3-235B-Thinking** - 122 kredi (235B parametre + reasoning)

## 🚀 Kullanım Senaryoları

### Düşük Bütçe Projeleri
- **Gemma 3N E4B** (2 kredi) - Basit görevler
- **GPT-OSS 20B** (8 kredi) - Genel amaçlı
- **Llama 3.1 8B** (12 kredi) - Hızlı yanıtlar

### Orta Seviye İhtiyaçlar
- **Qwen2.5-7B Turbo** (20 kredi) - Hızlı ve dengeli
- **GPT-OSS 120B** (24 kredi) - Güçlü ve uygun fiyatlı

### Profesyonel Projeler
- **Llama-3.3-70B Turbo** (58 kredi) - Meta'nın son modeli
- **DeepSeek-V3.1** (76 kredi) - Yeni nesil AI
- **Qwen2.5-72B Turbo** (80 kredi) - Çince + İngilizce

### Araştırma ve Geliştirme
- **Qwen3-235B Thinking** (122 kredi) - Reasoning yetenekleri
- **DeepSeek-R1-Distill** (134 kredi) - Distilled reasoning
- **Meta-Llama-405B** (234 kredi) - En büyük açık model

## 📝 Notlar

1. **API Fiyatları**: Together AI'ın resmi 1M token fiyatlarına göre güncellendi
2. **Credit Multiplier**: Gemini 2.5-flash'ı baz alarak hesaplandı ($0.30/1M token = 1.0x)
3. **Input/Output**: Input ve output fiyatlarının ortalaması kullanıldı
4. **Free Modeller**: Llama-3.3-70B-Instruct-Turbo-Free tamamen ücretsiz (0 kredi)
5. **Yeni Modeller**: 7 model veritabanında bulunamadı (eklenebilir)

## 🔄 Backend Restart Gerekli

Fiyatlandırma değişiklikleri database'e yazıldı. Backend ve Celery worker'ı yeniden başlatmanız gerekiyor:

```powershell
# Backend'i yeniden başlat
cd mp4totext-backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Celery worker'ı yeniden başlat
.\start_celery.bat
```

Frontend otomatik olarak yeni fiyatları API'den çekecektir.

## ✅ Doğrulama

Güncellenmiş fiyatları test etmek için:

```python
python -c "from app.database import SessionLocal; from app.models.ai_model_pricing import AIModelPricing; db = SessionLocal(); models = db.query(AIModelPricing).filter_by(provider='together', is_active=True).order_by(AIModelPricing.credit_multiplier).all(); [print(f'{m.credit_multiplier}x | {int(20*m.credit_multiplier)} kredi | {m.model_key}') for m in models]; db.close()"
```
