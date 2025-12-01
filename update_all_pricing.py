"""
Update All Pricing Descriptions
Migration script to add detailed descriptions with examples to ALL pricing configs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.credit_pricing import CreditPricingConfig
from app.models.source import Source  # Import to resolve relationships


def update_all_pricing_descriptions():
    """Update all pricing configs with detailed descriptions and examples"""
    db = SessionLocal()
    
    try:
        # Complete pricing configuration with detailed descriptions
        all_pricing = [
            # ==================== TRANSCRIPTION ====================
            {
                "operation_key": "transcription_base",
                "operation_name": "Transkripsiyon (Base)",
                "cost_per_unit": 1.0,
                "unit_description": "dakika başına",
                "description": "Ses/video dosyasını metne çevirme. Örnek: 30 dk video = 30 kredi"
            },
            {
                "operation_key": "transcription_per_minute",
                "operation_name": "Transkripsiyon (Dakika)",
                "cost_per_unit": 1.0,
                "unit_description": "dakika başına",
                "description": "AssemblyAI/Whisper ile transkripsiyon. Örnek: 60 dk = 60 kredi"
            },
            {
                "operation_key": "speaker_recognition",
                "operation_name": "Konuşmacı Tanıma (Diarization)",
                "cost_per_unit": 0.5,
                "unit_description": "dakika başına (ek)",
                "description": "Kimin konuştuğunu belirleme. Base fiyata ek. Örnek: 30 dk = +15 kredi"
            },
            {
                "operation_key": "youtube_download",
                "operation_name": "YouTube İndirme",
                "cost_per_unit": 5.0,
                "unit_description": "video başına",
                "description": "YouTube'dan video indirme. Sabit ücret, süre farketmez."
            },
            
            # ==================== AI ENHANCEMENT ====================
            {
                "operation_key": "ai_enhancement",
                "operation_name": "AI Metin İyileştirme",
                "cost_per_unit": 0.02,
                "unit_description": "1000 karakter başına",
                "description": "Gemini/GPT ile metin düzeltme. Örnek: 50.000 karakter = 1 kredi"
            },
            {
                "operation_key": "lecture_notes",
                "operation_name": "Ders Notu Oluşturma",
                "cost_per_unit": 0.03,
                "unit_description": "1000 karakter başına",
                "description": "AI ile ders notu özeti. Örnek: 30.000 karakter metin = ~1 kredi"
            },
            {
                "operation_key": "custom_prompt",
                "operation_name": "Özel AI Prompt",
                "cost_per_unit": 0.025,
                "unit_description": "1000 karakter başına",
                "description": "Kendi prompt'unuzla AI işleme. Örnek: 40.000 karakter = 1 kredi"
            },
            {
                "operation_key": "exam_questions",
                "operation_name": "Sınav Sorusu Üretme",
                "cost_per_unit": 0.04,
                "unit_description": "1000 karakter başına",
                "description": "Metinden sınav soruları oluşturma. Örnek: 25.000 karakter = 1 kredi"
            },
            {
                "operation_key": "translation",
                "operation_name": "Çeviri",
                "cost_per_unit": 0.03,
                "unit_description": "1000 karakter başına",
                "description": "AI ile dil çevirisi. Örnek: 30.000 karakterlik metin = ~1 kredi"
            },
            {
                "operation_key": "tavily_web_search",
                "operation_name": "Web Arama (Tavily)",
                "cost_per_unit": 2.0,
                "unit_description": "arama başına",
                "description": "Konuyla ilgili web'den bilgi toplama. Her arama 2 kredi."
            },
            
            # ==================== IMAGE GENERATION ====================
            {
                "operation_key": "image_generation_sdxl",
                "operation_name": "Görsel Üretimi (SDXL)",
                "cost_per_unit": 2.0,
                "unit_description": "görsel başına",
                "description": "Modal A10G GPU - Dengeli kalite/hız. Örnek: 5 görsel = 10 kredi"
            },
            {
                "operation_key": "image_generation_flux",
                "operation_name": "Görsel Üretimi (FLUX)",
                "cost_per_unit": 5.0,
                "unit_description": "görsel başına",
                "description": "Modal H100 GPU - Ultra kalite. Örnek: 5 görsel = 25 kredi"
            },
            {
                "operation_key": "image_generation_imagen",
                "operation_name": "Görsel Üretimi (Imagen-4)",
                "cost_per_unit": 8.0,
                "unit_description": "görsel başına",
                "description": "Google Imagen-4 - Fotorealistik. Örnek: 5 görsel = 40 kredi"
            },
            
            # ==================== VIDEO GENERATION ====================
            {
                "operation_key": "video_generation_base",
                "operation_name": "Video Üretimi (Sabit)",
                "cost_per_unit": 20.0,
                "unit_description": "video başına",
                "description": "Video oluşturma başlangıç ücreti. Her video için 1 kez."
            },
            {
                "operation_key": "video_generation_per_segment",
                "operation_name": "Video Segment Görseli",
                "cost_per_unit": 2.0,
                "unit_description": "segment başına",
                "description": "Her segment için AI görsel. Örnek: 10 segmentli video = +20 kredi"
            },
            {
                "operation_key": "video_tts_narration",
                "operation_name": "Video Seslendirme (TTS)",
                "cost_per_unit": 0.5,
                "unit_description": "dakika başına",
                "description": "OpenAI TTS ile seslendirme. Örnek: 10 dk video = 5 kredi"
            },
            
            # ==================== ASSEMBLYAI FEATURES ====================
            {
                "operation_key": "assemblyai_sentiment",
                "operation_name": "Duygu Analizi",
                "cost_per_unit": 0.3,
                "unit_description": "dakika başına (ek)",
                "description": "Konuşmadaki duygu tespiti. Sadece İngilizce. Örnek: 10 dk = +3 kredi"
            },
            {
                "operation_key": "assemblyai_chapters",
                "operation_name": "Otomatik Bölümler",
                "cost_per_unit": 0.3,
                "unit_description": "dakika başına (ek)",
                "description": "Konuşmayı bölümlere ayırma. Sadece İngilizce. Örnek: 10 dk = +3 kredi"
            },
            {
                "operation_key": "assemblyai_entity",
                "operation_name": "Varlık Tespiti",
                "cost_per_unit": 0.3,
                "unit_description": "dakika başına (ek)",
                "description": "İsim, yer, tarih tespiti. Tüm diller. Örnek: 10 dk = +3 kredi"
            },
            {
                "operation_key": "assemblyai_highlights",
                "operation_name": "Otomatik Öne Çıkanlar",
                "cost_per_unit": 0.3,
                "unit_description": "dakika başına (ek)",
                "description": "Önemli kısımları belirleme. Sadece İngilizce. Örnek: 10 dk = +3 kredi"
            },
            {
                "operation_key": "assemblyai_llm_gateway",
                "operation_name": "LLM Gateway",
                "cost_per_unit": 3.0,
                "unit_description": "istek başına",
                "description": "AssemblyAI LLM özet/analiz. Sabit ücret per istek."
            },
        ]
        
        added = 0
        updated = 0
        
        for config in all_pricing:
            existing = db.query(CreditPricingConfig).filter_by(
                operation_key=config["operation_key"]
            ).first()
            
            if existing:
                # Update existing
                existing.operation_name = config["operation_name"]
                existing.cost_per_unit = config["cost_per_unit"]
                existing.unit_description = config["unit_description"]
                existing.description = config["description"]
                existing.is_active = True
                updated += 1
                print(f"📝 Updated: {config['operation_key']}")
            else:
                # Create new
                new_config = CreditPricingConfig(**config, is_active=True)
                db.add(new_config)
                added += 1
                print(f"✅ Added: {config['operation_key']}")
        
        db.commit()
        
        print(f"""
╔════════════════════════════════════════════════════════════════════╗
║              ALL PRICING CONFIGS UPDATED                           ║
╠════════════════════════════════════════════════════════════════════╣
║  Added:    {added:2d} new pricing configs                                ║
║  Updated:  {updated:2d} existing configs                                  ║
╚════════════════════════════════════════════════════════════════════╝
        """)
        
        # List all pricing configs with descriptions
        print("\n" + "="*80)
        print("📋 COMPLETE PRICING TABLE")
        print("="*80)
        
        all_prices = db.query(CreditPricingConfig).order_by(CreditPricingConfig.operation_key).all()
        
        current_category = ""
        for p in all_prices:
            # Detect category from operation_key
            if p.operation_key.startswith("transcription") or p.operation_key.startswith("speaker") or p.operation_key.startswith("youtube"):
                category = "📝 TRANSCRIPTION"
            elif p.operation_key.startswith("ai_") or p.operation_key.startswith("lecture") or p.operation_key.startswith("custom") or p.operation_key.startswith("exam") or p.operation_key.startswith("translation") or p.operation_key.startswith("tavily"):
                category = "🤖 AI ENHANCEMENT"
            elif p.operation_key.startswith("image"):
                category = "🖼️ IMAGE GENERATION"
            elif p.operation_key.startswith("video"):
                category = "🎬 VIDEO GENERATION"
            elif p.operation_key.startswith("assemblyai"):
                category = "🎙️ ASSEMBLYAI FEATURES"
            else:
                category = "📦 OTHER"
            
            if category != current_category:
                print(f"\n{category}")
                print("-"*60)
                current_category = category
            
            status = "✅" if p.is_active else "❌"
            print(f"  {status} {p.operation_name}")
            print(f"     💰 {p.cost_per_unit} kredi / {p.unit_description}")
            if p.description:
                print(f"     📖 {p.description}")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_all_pricing_descriptions()
