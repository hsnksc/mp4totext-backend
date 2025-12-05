"""
🚀 Update AI Model Pricing - %50 Kar Marjlı Yeni Fiyatlar
Aralık 2025 - Gistify Pricing Analysis'e göre güncellenmiş çarpanlar

Formül: Piyasa Maliyeti × 1.5 ÷ $0.02 = Kredi Çarpanı
Base Rate: Gemini 2.5 Flash = 1.0x referans (~$1.0/M blended)
"""
import requests
import json

# Production API
API_URL = "https://api.gistify.pro/api/v1"

# %50 Karlı Yeni Model Çarpanları (Aralık 2025)
UPDATED_MODELS = [
    # ========== GEMINI (Blended Rate hesaplaması) ==========
    {"model_key": "gemini-2.5-flash-lite", "credit_multiplier": 0.27, "cost_per_1k_chars": 0.005},
    {"model_key": "gemini-2.0-flash", "credit_multiplier": 0.27, "cost_per_1k_chars": 0.005},
    {"model_key": "gemini-flash-latest", "credit_multiplier": 0.60, "cost_per_1k_chars": 0.012},
    {"model_key": "gemini-2.5-flash", "credit_multiplier": 1.50, "cost_per_1k_chars": 0.030},  # Yeni default
    {"model_key": "gemini-2.5-pro", "credit_multiplier": 6.00, "cost_per_1k_chars": 0.120},

    # ========== TOGETHER AI - LLAMA ==========
    {"model_key": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "credit_multiplier": 0.27, "cost_per_1k_chars": 0.005},
    {"model_key": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "credit_multiplier": 0.08, "cost_per_1k_chars": 0.002},
    {"model_key": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "credit_multiplier": 1.32, "cost_per_1k_chars": 0.026},
    {"model_key": "llama-3.3-70b-together", "credit_multiplier": 1.32, "cost_per_1k_chars": 0.026},
    {"model_key": "meta-llama/Llama-4-Scout-17B-16E-Instruct", "credit_multiplier": 0.26, "cost_per_1k_chars": 0.005},
    {"model_key": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", "credit_multiplier": 0.45, "cost_per_1k_chars": 0.009},
    {"model_key": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "credit_multiplier": 5.25, "cost_per_1k_chars": 0.105},
    {"model_key": "llama-3.1-405b-instruct-turbo", "credit_multiplier": 5.25, "cost_per_1k_chars": 0.105},

    # ========== TOGETHER AI - QWEN ==========
    {"model_key": "Qwen/Qwen2.5-7B-Instruct-Turbo", "credit_multiplier": 0.45, "cost_per_1k_chars": 0.009},
    {"model_key": "Qwen/Qwen2.5-72B-Instruct-Turbo", "credit_multiplier": 1.35, "cost_per_1k_chars": 0.027},
    {"model_key": "Qwen/Qwen3-235B-A22B-Instruct-2507", "credit_multiplier": 0.45, "cost_per_1k_chars": 0.009},
    {"model_key": "Qwen/Qwen3-235B-A22B-Thinking-2507", "credit_multiplier": 1.86, "cost_per_1k_chars": 0.037},

    # ========== TOGETHER AI - DEEPSEEK ==========
    {"model_key": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B", "credit_multiplier": 1.44, "cost_per_1k_chars": 0.029},
    {"model_key": "deepseek-ai/DeepSeek-V3.1", "credit_multiplier": 1.88, "cost_per_1k_chars": 0.038},
    {"model_key": "deepseek-ai/DeepSeek-R1", "credit_multiplier": 6.00, "cost_per_1k_chars": 0.120},

    # ========== TOGETHER AI - DİĞER ==========
    {"model_key": "moonshotai/Kimi-K2-Instruct-0905", "credit_multiplier": 2.25, "cost_per_1k_chars": 0.045},
    {"model_key": "mistralai/Magistral-Small-2506", "credit_multiplier": 0.60, "cost_per_1k_chars": 0.012},
    {"model_key": "mistralai/Mistral-Small-24B-Instruct-2501", "credit_multiplier": 0.30, "cost_per_1k_chars": 0.006},
    {"model_key": "google/gemma-3n-E4B-it", "credit_multiplier": 0.15, "cost_per_1k_chars": 0.003},
    {"model_key": "openai/gpt-oss-120b", "credit_multiplier": 0.39, "cost_per_1k_chars": 0.008},
    {"model_key": "openai/gpt-oss-20b", "credit_multiplier": 0.20, "cost_per_1k_chars": 0.004},
    {"model_key": "arcee-ai/virtuoso-medium-v2", "credit_multiplier": 0.75, "cost_per_1k_chars": 0.015},

    # ========== GROQ (ULTRA HIZLI) ==========
    {"model_key": "llama-3.1-8b-instant", "credit_multiplier": 0.09, "cost_per_1k_chars": 0.002},
    {"model_key": "llama-3.3-70b-versatile", "credit_multiplier": 0.96, "cost_per_1k_chars": 0.019},
    # Groq'taki GPT-OSS modelleri - ayrı key'ler ile
    
    # ========== OPENAI ==========
    {"model_key": "gpt-4.1-nano-2025-04-14", "credit_multiplier": 0.27, "cost_per_1k_chars": 0.005},
    {"model_key": "gpt-5-nano", "credit_multiplier": 0.39, "cost_per_1k_chars": 0.008},
    {"model_key": "gpt-4o-mini", "credit_multiplier": 0.39, "cost_per_1k_chars": 0.008},
    {"model_key": "gpt-4.1-mini-2025-04-14", "credit_multiplier": 1.05, "cost_per_1k_chars": 0.021},
    {"model_key": "gpt-5-mini", "credit_multiplier": 2.10, "cost_per_1k_chars": 0.042},
    {"model_key": "gpt-4-turbo", "credit_multiplier": 22.50, "cost_per_1k_chars": 0.450},  # Legacy - çok pahalı
    {"model_key": "gpt-4o", "credit_multiplier": 6.57, "cost_per_1k_chars": 0.131},
    {"model_key": "gpt-4.1-2025-04-14", "credit_multiplier": 5.25, "cost_per_1k_chars": 0.105},
    {"model_key": "gpt-5", "credit_multiplier": 6.57, "cost_per_1k_chars": 0.131},
    {"model_key": "gpt-5-pro", "credit_multiplier": 56.25, "cost_per_1k_chars": 1.125},
]

# Pricing configs to update
PRICING_CONFIGS = [
    # Transkripsiyon
    {"operation_key": "transcription_base", "cost_per_unit": 0.45, "unit_description": "dakika başına"},
    {"operation_key": "transcription_per_minute", "cost_per_unit": 0.45, "unit_description": "dakika başına"},
    {"operation_key": "speaker_recognition", "cost_per_unit": 0.15, "unit_description": "dakika başına (ek)"},
    {"operation_key": "speaker_diarization", "cost_per_unit": 0.15, "unit_description": "dakika başına (ek)"},
    {"operation_key": "youtube_download", "cost_per_unit": 0.75, "unit_description": "video başına"},
    
    # Web Arama
    {"operation_key": "tavily_web_search", "cost_per_unit": 0.75, "unit_description": "arama başına"},
    
    # Görsel Üretimi
    {"operation_key": "image_generation_sdxl", "cost_per_unit": 1.0, "unit_description": "görsel başına"},
    {"operation_key": "image_generation_flux", "cost_per_unit": 3.0, "unit_description": "görsel başına"},
    {"operation_key": "image_generation_imagen", "cost_per_unit": 4.5, "unit_description": "görsel başına"},
    
    # Video Üretimi
    {"operation_key": "video_generation_base", "cost_per_unit": 7.5, "unit_description": "video başına"},
    {"operation_key": "video_generation_per_segment", "cost_per_unit": 0.75, "unit_description": "segment başına"},
    {"operation_key": "video_tts_narration", "cost_per_unit": 1.13, "unit_description": "dakika başına"},
    
    # AssemblyAI
    {"operation_key": "assemblyai_sentiment", "cost_per_unit": 0.38, "unit_description": "dakika başına (ek)"},
    {"operation_key": "assemblyai_chapters", "cost_per_unit": 0.38, "unit_description": "dakika başına (ek)"},
    {"operation_key": "assemblyai_entity", "cost_per_unit": 0.23, "unit_description": "dakika başına (ek)"},
    {"operation_key": "assemblyai_highlights", "cost_per_unit": 0.38, "unit_description": "dakika başına (ek)"},
    {"operation_key": "assemblyai_llm_gateway", "cost_per_unit": 3.75, "unit_description": "istek başına"},
    {"operation_key": "assemblyai_speech_understanding", "cost_per_unit": 0.90, "unit_description": "dakika başına"},
]


def update_via_api():
    """Update pricing via production API"""
    print("🚀 Updating AI Model Pricing via API...")
    print(f"   API: {API_URL}")
    print("=" * 60)
    
    print("\n⚠️ You need to get an admin token first!")
    print("   1. Login to production as admin")
    print("   2. Copy the access_token from the response")
    print("   3. Paste it below\n")
    
    token = input("Enter admin access_token: ").strip()
    if not token:
        print("❌ No token provided!")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Update models
    print("\n📤 Updating AI model multipliers...")
    success_count = 0
    error_count = 0
    
    for model in UPDATED_MODELS:
        try:
            response = requests.patch(
                f"{API_URL}/credits/admin/models/{model['model_key']}",
                headers=headers,
                json={
                    "credit_multiplier": model["credit_multiplier"],
                    "cost_per_1k_chars": model.get("cost_per_1k_chars")
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ {model['model_key']}: {model['credit_multiplier']}x")
                success_count += 1
            else:
                print(f"   ❌ {model['model_key']}: {response.status_code} - {response.text[:100]}")
                error_count += 1
                
        except Exception as e:
            print(f"   ❌ {model['model_key']}: Error - {e}")
            error_count += 1
    
    print(f"\n📊 Model Update Summary:")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    
    # Update pricing configs
    print("\n📤 Updating pricing configs...")
    success_count = 0
    error_count = 0
    
    for config in PRICING_CONFIGS:
        try:
            response = requests.patch(
                f"{API_URL}/credits/admin/pricing/{config['operation_key']}",
                headers=headers,
                json={
                    "cost_per_unit": config["cost_per_unit"],
                    "unit_description": config.get("unit_description")
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"   ✅ {config['operation_key']}: {config['cost_per_unit']} kr/{config.get('unit_description', 'birim')}")
                success_count += 1
            else:
                print(f"   ❌ {config['operation_key']}: {response.status_code}")
                error_count += 1
                
        except Exception as e:
            print(f"   ❌ {config['operation_key']}: Error - {e}")
            error_count += 1
    
    print(f"\n📊 Pricing Config Update Summary:")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    
    print("\n" + "=" * 60)
    print("✅ Pricing update completed!")
    print("=" * 60)


def update_local_db():
    """Update pricing in local database"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app.database import SessionLocal
    from app.models.ai_model_pricing import AIModelPricing
    from app.models.credit_pricing import CreditPricingConfig
    
    db = SessionLocal()
    
    try:
        print("🚀 Updating Local Database Pricing...")
        print("=" * 60)
        
        # Update AI models
        print("\n📤 Updating AI model multipliers...")
        for model in UPDATED_MODELS:
            existing = db.query(AIModelPricing).filter_by(model_key=model["model_key"]).first()
            if existing:
                existing.credit_multiplier = model["credit_multiplier"]
                if model.get("cost_per_1k_chars"):
                    existing.cost_per_1k_chars = model["cost_per_1k_chars"]
                print(f"   ✅ Updated: {model['model_key']} → {model['credit_multiplier']}x")
            else:
                print(f"   ⚠️ Not found: {model['model_key']}")
        
        # Update pricing configs
        print("\n📤 Updating pricing configs...")
        for config in PRICING_CONFIGS:
            existing = db.query(CreditPricingConfig).filter_by(operation_key=config["operation_key"]).first()
            if existing:
                existing.cost_per_unit = config["cost_per_unit"]
                if config.get("unit_description"):
                    existing.unit_description = config["unit_description"]
                print(f"   ✅ Updated: {config['operation_key']} → {config['cost_per_unit']}")
            else:
                # Create new
                new_config = CreditPricingConfig(
                    operation_key=config["operation_key"],
                    operation_name=config["operation_key"].replace("_", " ").title(),
                    cost_per_unit=config["cost_per_unit"],
                    unit_description=config.get("unit_description", "birim başına"),
                    is_active=True
                )
                db.add(new_config)
                print(f"   ✅ Created: {config['operation_key']} → {config['cost_per_unit']}")
        
        db.commit()
        print("\n" + "=" * 60)
        print("✅ Local database updated successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║      GISTIFY PRICING UPDATE - %50 KAR MARJI                ║
║                    Aralık 2025                              ║
╠════════════════════════════════════════════════════════════╣
║  1. Update Local Database                                   ║
║  2. Update Production via API                               ║
║  3. Show Price Comparison                                   ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    choice = input("Select option (1/2/3): ").strip()
    
    if choice == "1":
        update_local_db()
    elif choice == "2":
        update_via_api()
    elif choice == "3":
        print("\n📊 Price Comparison (Old → New):")
        print("-" * 60)
        print("TRANSKRIPSIYON:")
        print("  Base:        1.0  → 0.45 kr/dk  (-%55)")
        print("  Diarization: 0.5  → 0.15 kr/dk  (-%70)")
        print("  YouTube:     10.0 → 0.75 kr     (-%93)")
        print("\nGÖRSEL ÜRETİMİ:")
        print("  SDXL:        1.0  → 1.0 kr      (=)")
        print("  FLUX:        2.0  → 3.0 kr      (+%50)")
        print("  Imagen:      4.0  → 4.5 kr      (+%13)")
        print("\nVİDEO ÜRETİMİ:")
        print("  Base:        20   → 7.5 kr      (-%63)")
        print("  Segment:     2.0  → 0.75 kr     (-%63)")
        print("  TTS:         0.5  → 1.13 kr/dk  (+%126)")
        print("\nAI MODEL ÖRNEKLERİ:")
        print("  Gemini 2.5 Flash Lite: 0.4x → 0.27x  (-%33)")
        print("  Gemini 2.5 Pro:        3.0x → 6.00x  (+%100)")
        print("  Llama 4 Maverick:      2.5x → 0.45x  (-%82)")
        print("  GPT-4o Mini:           2.0x → 0.39x  (-%81)")
        print("  GPT-5 Pro:             50x  → 56.25x (+%13)")
    else:
        print("Invalid option")
