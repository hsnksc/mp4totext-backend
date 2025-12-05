"""
%75 Kar Marjlı Fiyat Güncellemesi (Aralık 2025)
==============================================

Bu script tüm CreditPricingConfig ve AIModelPricing tablolarını
%75 kar marjıyla günceller.

Formül: Piyasa Maliyeti × 1.75 ÷ $0.02 = Kredi
1 kredi = $0.02 USD
500 kredi = $10.00 USD

Coolify'da Çalıştırma:
    cd /app && python update_pricing_75_percent_margin.py

Gerekli: DATABASE_URL ortam değişkeni
"""

import os
import sys

# SQL Alchemy import
try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("❌ sqlalchemy bulunamadı. Yükleniyor...")
    os.system("pip install sqlalchemy psycopg2-binary")
    from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL ortam değişkeni bulunamadı!")
    print("   Örnek: postgresql://user:pass@host:5432/dbname")
    sys.exit(1)

print(f"🔌 Veritabanına bağlanılıyor...")
print(f"   URL: {DATABASE_URL[:50]}...")

engine = create_engine(DATABASE_URL)

# ============================================================
# %75 KAR MARJLI YENİ FİYATLAR
# Formül: Piyasa Maliyeti × 1.75 ÷ $0.02 = Kredi
# ============================================================

CREDIT_PRICING_VALUES = {
    # Temel Transkripsiyon
    "transcription_base": 0.53,       # $0.006/dk × 1.75 ÷ $0.02 = 0.525 → 0.53 kr/dk
    "speaker_recognition": 0.18,      # $0.002/dk × 1.75 ÷ $0.02 = 0.175 → 0.18 kr/dk
    "speaker_diarization": 0.18,      # pyannote.audio Modal GPU ücreti
    "youtube_download": 0.88,         # $0.01/video × 1.75 ÷ $0.02 = 0.875 → 0.88 kr/video
    
    # AssemblyAI
    "assemblyai_speech_understanding_per_minute": 1.05,  # $0.012/dk × 1.75 ÷ $0.02 = 1.05 kr/dk
    "assemblyai_llm_gateway": 4.38,   # ~$0.05/istek × 1.75 ÷ $0.02 = 4.375 → 4.38 kr/istek
    "entity_detection_per_minute": 0.26,  # $0.003/dk × 1.75 ÷ $0.02 = 0.263 → 0.26 kr/dk
    
    # Tavily Web Arama
    "tavily_web_search": 0.88,        # $0.01/arama × 1.75 ÷ $0.02 = 0.875 → 0.88 kr/arama
}

# AI Model çarpanları (base fiyat × çarpan = final kredi)
AI_MODEL_MULTIPLIERS = {
    # Google Gemini Modelleri
    "gemini-2.0-flash-lite": 0.32,      # Ultra ucuz - $0.075/1M input
    "gemini-2.0-flash": 1.49,           # Default - $0.34/1M input  
    "gemini-2.0-flash-thinking": 3.50,  # Reasoning - $0.80/1M input
    "gemini-2.5-flash-preview": 2.41,   # Preview - $0.55/1M input
    "gemini-2.5-pro-preview": 6.02,     # Pro - $1.37/1M input
    
    # OpenAI Modelleri
    "gpt-4o-mini": 0.46,                # Mini - $0.15/1M input
    "gpt-4o": 2.19,                     # Standard - $5/1M input
    "gpt-4.1-mini": 0.53,               # Updated mini
    "gpt-4.1": 1.75,                    # Updated standard
    
    # Meta Llama Modelleri (Together AI)
    "meta-llama/llama-4-scout-17b-16e-instruct": 0.35,  # Scout 17B
    "meta-llama/llama-4-maverick-17b-128e-instruct": 0.53,  # Maverick 17B
    "meta-llama/llama-3.3-70b-instruct-turbo": 0.74,    # 70B Turbo
    
    # Groq Modelleri  
    "llama-3.3-70b-versatile": 0.05,    # Çok ucuz - $0.59/1M input
    "llama-3.3-70b-specdec": 0.05,      # SpecDec
    "llama-3.1-8b-instant": 0.01,       # 8B instant - $0.05/1M
    "mixtral-8x7b-32768": 0.02,         # Mixtral - $0.24/1M
    "gemma2-9b-it": 0.01,               # Gemma2 - $0.10/1M
    
    # DeepSeek Modelleri
    "deepseek-r1": 7.00,                # Reasoning - $0.55/1M (cache'siz)
    "deepseek-r1-distill-llama-70b": 0.74,  # Distill versiyonu
    
    # Qwen Modelleri
    "qwen-qwq-32b": 0.26,               # QwQ 32B
    "qwen-2.5-72b-instruct": 1.05,      # Qwen 2.5 72B
    "qwen-2.5-coder-32b-instruct": 0.74,  # Coder
    
    # Diğer Modeller
    "llama-3.2-90b-vision-instruct-turbo": 1.05,  # Vision
    "llama-3.2-11b-vision-instruct-turbo": 0.35,  # Vision küçük
    "dbrx-instruct": 1.05,              # DBRX
    
    # Görsel Modeller
    "sdxl": 1.31,                       # $0.015 × 1.75 ÷ $0.02 = 1.31 kr/görsel
    "flux": 3.50,                       # $0.04 × 1.75 ÷ $0.02 = 3.50 kr/görsel
    "imagen": 5.25,                     # $0.06 × 1.75 ÷ $0.02 = 5.25 kr/görsel
}


def update_credit_pricing():
    """CreditPricingConfig tablosunu güncelle"""
    print("\n" + "="*60)
    print("📊 CreditPricingConfig Güncellemesi (%75 Kar Marjı)")
    print("="*60)
    
    with engine.connect() as conn:
        for key, value in CREDIT_PRICING_VALUES.items():
            try:
                result = conn.execute(text(
                    "UPDATE credit_pricing_config SET base_cost = :value WHERE operation_name = :key"
                ), {"value": value, "key": key})
                
                if result.rowcount > 0:
                    print(f"  ✅ {key}: {value} kredi (güncellendi)")
                else:
                    # Kayıt yoksa ekle
                    conn.execute(text("""
                        INSERT INTO credit_pricing_config (operation_name, base_cost, is_active)
                        VALUES (:key, :value, TRUE)
                    """), {"key": key, "value": value})
                    print(f"  ➕ {key}: {value} kredi (eklendi)")
                    
            except Exception as e:
                print(f"  ❌ {key}: Hata - {e}")
        
        conn.commit()
        print("\n✅ CreditPricingConfig güncellendi!")


def update_ai_model_pricing():
    """AIModelPricing tablosunu güncelle"""
    print("\n" + "="*60)
    print("🤖 AIModelPricing Güncellemesi (%75 Kar Marjı)")
    print("="*60)
    
    with engine.connect() as conn:
        for model_name, multiplier in AI_MODEL_MULTIPLIERS.items():
            try:
                result = conn.execute(text(
                    "UPDATE ai_model_pricing SET credit_multiplier = :multiplier WHERE model_name = :name"
                ), {"multiplier": multiplier, "name": model_name})
                
                if result.rowcount > 0:
                    print(f"  ✅ {model_name}: {multiplier}x (güncellendi)")
                else:
                    # Kayıt yoksa ekle
                    # Model type belirleme
                    if model_name in ["sdxl", "flux", "imagen"]:
                        model_type = "image"
                    elif "gemini" in model_name.lower():
                        model_type = "gemini"
                    elif "gpt" in model_name.lower():
                        model_type = "openai"
                    elif "llama" in model_name.lower():
                        model_type = "together"
                    elif "deepseek" in model_name.lower() or "qwen" in model_name.lower():
                        model_type = "together"
                    else:
                        model_type = "groq"
                    
                    conn.execute(text("""
                        INSERT INTO ai_model_pricing (model_name, provider, credit_multiplier, is_active, model_type)
                        VALUES (:name, :model_type, :multiplier, TRUE, 'enhancement')
                    """), {"name": model_name, "model_type": model_type, "multiplier": multiplier})
                    print(f"  ➕ {model_name}: {multiplier}x (eklendi, provider: {model_type})")
                    
            except Exception as e:
                print(f"  ❌ {model_name}: Hata - {e}")
        
        conn.commit()
        print("\n✅ AIModelPricing güncellendi!")


def print_summary():
    """Özet bilgi yazdır"""
    print("\n" + "="*60)
    print("📋 %75 KAR MARJI ÖZET")
    print("="*60)
    print("""
    🎯 Temel Fiyatlar:
       • Transkripsiyon: 0.53 kr/dk
       • Speaker Diarization: 0.18 kr/dk
       • YouTube Download: 0.88 kr/video
       • AssemblyAI Speech Understanding: 1.05 kr/dk
       • AssemblyAI LLM Gateway: 4.38 kr/istek
       • Entity Detection: 0.26 kr/dk
       • Tavily Web Search: 0.88 kr/arama
    
    🖼️ Görsel Üretim:
       • SDXL: 1.31 kr/görsel
       • FLUX: 3.50 kr/görsel
       • Imagen: 5.25 kr/görsel
    
    🎬 Video Üretim:
       • Base: 8.75 kr/video
       • Segment (SDXL): 1.31 kr/segment
       • TTS: 1.31 kr/dk
    
    📈 Kar Marjı: %75
    💰 1 kredi = $0.02 USD
    💵 500 kredi = $10.00 USD
    """)


if __name__ == "__main__":
    print("🚀 Gistify %75 Kar Marjlı Fiyat Güncellemesi")
    print("=" * 60)
    
    try:
        update_credit_pricing()
        update_ai_model_pricing()
        print_summary()
        print("\n✅ Tüm fiyatlar başarıyla güncellendi!")
    except Exception as e:
        print(f"\n❌ Güncelleme sırasında hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
