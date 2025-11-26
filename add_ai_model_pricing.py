"""
AI Model Pricing Migration
Farklı AI modelleri için fiyatlandırma tablosu oluştur ve seed data ekle
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from app.database import Base, get_db
from app.settings import get_settings
from app.models.ai_model_pricing import AIModelPricing

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def create_table():
    """Tablo yoksa oluştur"""
    inspector = inspect(engine)
    if not inspector.has_table("ai_model_pricing"):
        print("✅ Creating ai_model_pricing table...")
        AIModelPricing.__table__.create(engine)
        print("✅ Table created successfully")
    else:
        print("ℹ️  Table ai_model_pricing already exists")


def seed_model_pricing():
    """
    AI model fiyatlandırma verilerini ekle
    
    Kredi çarpanları (credit_multiplier):
    Base işlem maliyetine göre çarpan (Lecture Notes: 30 kredi base)
    - Gemini 2.5 Flash: 1.0x (varsayılan, dengeli)
    - Gemini 2.5 Pro: 2.5x (en güçlü, en pahalı)
    - Gemini 2.0 Flash: 0.5x (eski nesil, ucuz)
    - OpenAI GPT-4o-mini: 1.5x (dengeli, hızlı)
    - Groq Llama 3.3 70B: 0.8x (ultra hızlı, ucuz)
    """
    db = SessionLocal()
    try:
        # Mevcut kayıtları kontrol et
        existing_count = db.query(AIModelPricing).count()
        if existing_count > 0:
            print(f"ℹ️  {existing_count} model pricing configs already exist. Skipping seed.")
            return

        models = [
            # ============ GEMINI MODELS ============
            {
                "model_key": "gemini-2.5-flash",
                "model_name": "Gemini 2.5 Flash",
                "provider": "gemini",
                "credit_multiplier": 1.0,
                "description": "Hybrid reasoning model with 1M context. Fastest and most balanced. Recommended for all tasks.",
                "api_cost_per_1m_input": 0.30,
                "api_cost_per_1m_output": 2.50,
                "is_default": True,
                "is_active": True
            },
            {
                "model_key": "gemini-2.5-pro",
                "model_name": "Gemini 2.5 Pro",
                "provider": "gemini",
                "credit_multiplier": 2.5,
                "description": "State-of-the-art model excelling at coding and complex reasoning. Highest quality, slower speed.",
                "api_cost_per_1m_input": 2.50,
                "api_cost_per_1m_output": 10.00,
                "is_default": False,
                "is_active": True
            },
            {
                "model_key": "gemini-2.0-flash",
                "model_name": "Gemini 2.0 Flash",
                "provider": "gemini",
                "credit_multiplier": 0.5,
                "description": "Previous generation model. Balanced performance, lowest cost. Good for budget-conscious users.",
                "api_cost_per_1m_input": 0.10,
                "api_cost_per_1m_output": 0.40,
                "is_default": False,
                "is_active": True
            },
            
            # ============ OPENAI MODELS ============
            {
                "model_key": "gpt-4o-mini",
                "model_name": "GPT-4o Mini",
                "provider": "openai",
                "credit_multiplier": 1.5,
                "description": "Fast and intelligent small model for everyday tasks. Great for quick responses.",
                "api_cost_per_1m_input": 0.15,
                "api_cost_per_1m_output": 0.60,
                "is_default": False,
                "is_active": True
            },
            
            # ============ GROQ MODELS ============
            {
                "model_key": "llama-3.3-70b-versatile",
                "model_name": "Llama 3.3 70B (Groq)",
                "provider": "groq",
                "credit_multiplier": 0.8,
                "description": "Ultra-fast inference with Groq. Meta's Llama 3.3 optimized for speed. 10x faster than OpenAI.",
                "api_cost_per_1m_input": 0.08,
                "api_cost_per_1m_output": 0.10,
                "is_default": False,
                "is_active": True
            },
            {
                "model_key": "llama-3.1-8b-instant",
                "model_name": "Llama 3.1 8B Instant (Groq)",
                "provider": "groq",
                "credit_multiplier": 0.3,
                "description": "Extremely fast and cheap. Good for simple tasks. Lightning-fast responses.",
                "api_cost_per_1m_input": 0.05,
                "api_cost_per_1m_output": 0.08,
                "is_default": False,
                "is_active": True
            }
        ]

        for model_data in models:
            model = AIModelPricing(**model_data)
            db.add(model)
        
        db.commit()
        print(f"✅ Seeded {len(models)} AI model pricing configs:")
        for model_data in models:
            multiplier = model_data['credit_multiplier']
            default_str = " (DEFAULT)" if model_data['is_default'] else ""
            print(f"   • {model_data['model_name']}: {multiplier}x{default_str}")
            print(f"     API Cost: ${model_data['api_cost_per_1m_input']}/1M in, ${model_data['api_cost_per_1m_output']}/1M out")
            
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Starting AI Model Pricing migration...")
    create_table()
    seed_model_pricing()
    print("✅ Migration completed successfully!")
