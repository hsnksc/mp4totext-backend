"""
%75 Kar Marjlı Fiyat Güncellemesi (Aralık 2025)
==============================================

Bu script ai_model_pricing tablosundaki credit_multiplier değerlerini
%75 kar marjıyla günceller.

NOT: Temel fiyatlar (transcription_base, speaker_diarization vb.) 
     credit_service.py içindeki DEFAULT_PRICING'den alınıyor.
     Bu script sadece AI model çarpanlarını günceller.

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

# AI Model çarpanları (base fiyat × çarpan = final kredi)
AI_MODEL_MULTIPLIERS = {
    # Google Gemini Modelleri
    "gemini-2.0-flash-lite": 0.32,
    "gemini-2.0-flash": 1.49,
    "gemini-2.0-flash-thinking": 3.50,
    "gemini-2.5-flash-preview": 2.41,
    "gemini-2.5-pro-preview": 6.02,
    
    # OpenAI Modelleri
    "gpt-4o-mini": 0.46,
    "gpt-4o": 2.19,
    "gpt-4.1-mini": 0.53,
    "gpt-4.1": 1.75,
    
    # Meta Llama Modelleri (Together AI)
    "meta-llama/llama-4-scout-17b-16e-instruct": 0.35,
    "meta-llama/llama-4-maverick-17b-128e-instruct": 0.53,
    "meta-llama/llama-3.3-70b-instruct-turbo": 0.74,
    
    # Groq Modelleri  
    "llama-3.3-70b-versatile": 0.05,
    "llama-3.3-70b-specdec": 0.05,
    "llama-3.1-8b-instant": 0.01,
    "mixtral-8x7b-32768": 0.02,
    "gemma2-9b-it": 0.01,
    
    # DeepSeek Modelleri
    "deepseek-r1": 7.00,
    "deepseek-r1-distill-llama-70b": 0.74,
    
    # Qwen Modelleri
    "qwen-qwq-32b": 0.26,
    "qwen-2.5-72b-instruct": 1.05,
    "qwen-2.5-coder-32b-instruct": 0.74,
    
    # Diğer Modeller
    "llama-3.2-90b-vision-instruct-turbo": 1.05,
    "llama-3.2-11b-vision-instruct-turbo": 0.35,
    "dbrx-instruct": 1.05,
    
    # Görsel Modeller
    "sdxl": 1.31,
    "flux": 3.50,
    "imagen": 5.25,
}


def check_table_structure():
    """Veritabanı tablo yapısını kontrol et"""
    print("\n" + "="*60)
    print("🔍 Veritabanı Yapısı Kontrolü")
    print("="*60)
    
    with engine.connect() as conn:
        # Tabloları listele
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        print(f"\n📋 Mevcut tablolar: {', '.join(tables)}")
        
        # ai_model_pricing tablosunun sütunlarını kontrol et
        if 'ai_model_pricing' in tables:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'ai_model_pricing'
                ORDER BY ordinal_position
            """))
            columns = [(row[0], row[1]) for row in result]
            print(f"\n🗂️ ai_model_pricing sütunları:")
            for col, dtype in columns:
                print(f"   • {col}: {dtype}")
            return [col for col, _ in columns]
        else:
            print("⚠️ ai_model_pricing tablosu bulunamadı!")
            return []


def update_ai_model_pricing(columns):
    """AIModelPricing tablosunu güncelle - sadece mevcut kayıtları güncelle"""
    print("\n" + "="*60)
    print("🤖 AIModelPricing Güncellemesi (%75 Kar Marjı)")
    print("="*60)
    
    updated = 0
    skipped = 0
    
    with engine.connect() as conn:
        for model_name, multiplier in AI_MODEL_MULTIPLIERS.items():
            try:
                # Sadece UPDATE yap, INSERT yapma
                result = conn.execute(text(
                    "UPDATE ai_model_pricing SET credit_multiplier = :multiplier WHERE model_name = :name"
                ), {"multiplier": multiplier, "name": model_name})
                
                if result.rowcount > 0:
                    print(f"  ✅ {model_name}: {multiplier}x")
                    updated += 1
                else:
                    print(f"  ⏭️ {model_name}: kayıt yok (atlandı)")
                    skipped += 1
                    
            except Exception as e:
                print(f"  ❌ {model_name}: Hata - {str(e)[:100]}")
        
        conn.commit()
        print(f"\n📊 Sonuç: {updated} güncellendi, {skipped} atlandı")


def show_current_pricing():
    """Mevcut fiyatları göster"""
    print("\n" + "="*60)
    print("📊 Mevcut AI Model Fiyatları")
    print("="*60)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT model_name, provider, credit_multiplier, is_active
            FROM ai_model_pricing
            ORDER BY provider, model_name
        """))
        
        current_provider = None
        for row in result:
            model_name, provider, multiplier, is_active = row
            if provider != current_provider:
                print(f"\n  📁 {provider}:")
                current_provider = provider
            status = "✅" if is_active else "❌"
            print(f"     {status} {model_name}: {multiplier}x")


def print_summary():
    """Özet bilgi yazdır"""
    print("\n" + "="*60)
    print("📋 %75 KAR MARJI ÖZET")
    print("="*60)
    print("""
    🎯 Temel Fiyatlar (credit_service.py'de tanımlı):
       • Transkripsiyon: 0.53 kr/dk
       • Speaker Diarization: 0.18 kr/dk
       • YouTube Download: 0.88 kr/video
       • AssemblyAI Speech Understanding: 1.05 kr/dk
       • AssemblyAI LLM Gateway: 4.38 kr/istek
       • Entity Detection: 0.26 kr/dk
       • Tavily Web Search: 0.88 kr/arama
    
    🖼️ Görsel Üretim (transcription_worker.py'de tanımlı):
       • SDXL: 1.31 kr/görsel
       • FLUX: 3.50 kr/görsel
       • Imagen: 5.25 kr/görsel
    
    🎬 Video Üretim (transcription_worker.py'de tanımlı):
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
        # 1. Tablo yapısını kontrol et
        columns = check_table_structure()
        
        if not columns:
            print("\n❌ ai_model_pricing tablosu bulunamadı!")
            print("   Lütfen önce migration'ları çalıştırın.")
            sys.exit(1)
        
        # 2. Mevcut fiyatları göster
        show_current_pricing()
        
        # 3. AI model fiyatlarını güncelle
        update_ai_model_pricing(columns)
        
        # 4. Güncel fiyatları tekrar göster
        print("\n" + "="*60)
        print("📊 Güncelleme Sonrası AI Model Fiyatları")
        print("="*60)
        show_current_pricing()
        
        # 5. Özet
        print_summary()
        
        print("\n✅ Tüm güncellemeler tamamlandı!")
        print("\n⚠️ NOT: Temel fiyatlar (transcription, diarization vb.)")
        print("   credit_service.py içinde tanımlıdır ve backend")
        print("   yeniden deploy edildiğinde otomatik uygulanır.")
        
    except Exception as e:
        print(f"\n❌ Güncelleme sırasında hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
