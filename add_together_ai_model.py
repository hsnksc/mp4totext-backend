"""
Together AI Model Ekleme
Together AI için Llama 3.3 70B modelini ekle
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import get_settings
from app.models.ai_model_pricing import AIModelPricing

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def add_together_ai_model():
    """Together AI modeli ekle"""
    db = SessionLocal()
    try:
        # Mevcut kaydı kontrol et
        existing = db.query(AIModelPricing).filter(
            AIModelPricing.model_key == "llama-3.3-70b-together"
        ).first()
        
        if existing:
            print(f"ℹ️  Together AI model already exists: {existing.model_name}")
            return
        
        # Together AI modeli ekle
        together_model = AIModelPricing(
            model_key="llama-3.3-70b-together",
            model_name="Llama 3.3 70B (Together AI)",
            provider="together",
            credit_multiplier=0.9,
            description="Meta's Llama 3.3 70B on Together AI. Good balance of speed and quality.",
            api_cost_per_1m_input=0.18,
            api_cost_per_1m_output=0.18,
            is_default=False,
            is_active=True
        )
        
        db.add(together_model)
        db.commit()
        
        print("✅ Together AI model added successfully:")
        print(f"   • {together_model.model_name}: {together_model.credit_multiplier}x")
        print(f"     API Cost: ${together_model.api_cost_per_1m_input}/1M in, ${together_model.api_cost_per_1m_output}/1M out")
        
    except Exception as e:
        print(f"❌ Error adding Together AI model: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Adding Together AI model...")
    add_together_ai_model()
    print("✅ Migration completed successfully!")
