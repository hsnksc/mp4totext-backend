"""
Add Credit Pricing Configuration Table
Dinamik fiyatlandırma sistemi için tablo ekler ve varsayılan değerlerle doldurur
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.settings import get_settings
from app.database import Base
from app.models.credit_pricing import CreditPricingConfig

# Create engine
settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def add_pricing_configs():
    """Pricing configs tablosunu oluştur ve varsayılan değerlerle doldur"""
    
    print("🔵 Creating credit_pricing_configs table...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Varsayılan fiyatlandırma yapılandırmaları
        default_configs = [
            {
                "operation_key": "transcription_base",
                "operation_name": "Transkripsiyon (Temel)",
                "cost_per_unit": 10,
                "unit_description": "dakika başı",
                "description": "Ses dosyasını metne dönüştürme işlemi",
            },
            {
                "operation_key": "speaker_recognition",
                "operation_name": "Konuşmacı Tanıma",
                "cost_per_unit": 5,
                "unit_description": "dakika başı",
                "description": "Farklı konuşmacıları ayırt etme (ek maliyet)",
            },
            {
                "operation_key": "youtube_download",
                "operation_name": "YouTube İndirme",
                "cost_per_unit": 10,
                "unit_description": "işlem başı",
                "description": "YouTube videosundan ses çıkarma",
            },
            {
                "operation_key": "ai_enhancement",
                "operation_name": "AI Metin İyileştirme",
                "cost_per_unit": 20,
                "unit_description": "işlem başı",
                "description": "Gemini AI ile metin düzeltme ve özet",
            },
            {
                "operation_key": "lecture_notes",
                "operation_name": "Ders Notu Oluşturma",
                "cost_per_unit": 30,
                "unit_description": "işlem başı",
                "description": "Gemini AI ile akademik ders notu formatı",
            },
            {
                "operation_key": "custom_prompt",
                "operation_name": "Özel Prompt İşleme",
                "cost_per_unit": 25,
                "unit_description": "işlem başı",
                "description": "Gemini AI ile kullanıcı tanımlı işlem",
            },
            {
                "operation_key": "exam_questions",
                "operation_name": "Sınav Soruları Oluşturma",
                "cost_per_unit": 35,
                "unit_description": "işlem başı",
                "description": "Gemini AI ile test soruları üretme",
            },
            {
                "operation_key": "translation",
                "operation_name": "Çeviri",
                "cost_per_unit": 15,
                "unit_description": "işlem başı",
                "description": "Gemini AI ile çok dilli çeviri",
            },
        ]
        
        print("🔵 Checking existing configs...")
        existing_keys = {config.operation_key for config in db.query(CreditPricingConfig).all()}
        
        added_count = 0
        for config_data in default_configs:
            if config_data["operation_key"] not in existing_keys:
                config = CreditPricingConfig(**config_data)
                db.add(config)
                print(f"  ✅ Added: {config_data['operation_name']} ({config_data['cost_per_unit']} kredi/{config_data['unit_description']})")
                added_count += 1
            else:
                print(f"  ⏭️  Skipped (exists): {config_data['operation_name']}")
        
        db.commit()
        print(f"\n✅ Migration completed! Added {added_count} new pricing configs.")
        
        # Tüm config'leri göster
        print("\n📊 Current pricing configurations:")
        all_configs = db.query(CreditPricingConfig).filter_by(is_active=True).all()
        for config in all_configs:
            print(f"  • {config.operation_name}: {config.cost_per_unit} kredi/{config.unit_description}")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting Credit Pricing Configuration Migration...\n")
    add_pricing_configs()
    print("\n🎉 Migration completed successfully!")
