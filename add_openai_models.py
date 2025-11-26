"""
OpenAI Models Ekleme
GPT-4o ve GPT-4-turbo modellerini ekle
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


def add_openai_models():
    """OpenAI modellerini ekle"""
    db = SessionLocal()
    try:
        # Mevcut kayıtları kontrol et
        existing_gpt4o = db.query(AIModelPricing).filter(
            AIModelPricing.model_key == "gpt-4o"
        ).first()
        
        existing_gpt4turbo = db.query(AIModelPricing).filter(
            AIModelPricing.model_key == "gpt-4-turbo"
        ).first()
        
        models_to_add = []
        
        # GPT-4o ekle
        if not existing_gpt4o:
            gpt4o = AIModelPricing(
                model_key="gpt-4o",
                model_name="GPT-4o",
                provider="openai",
                credit_multiplier=3.0,  # Premium model
                description="OpenAI's most advanced model. Best quality, multimodal capabilities.",
                api_cost_per_1m_input=2.50,
                api_cost_per_1m_output=10.00,
                is_default=False,
                is_active=True
            )
            models_to_add.append(gpt4o)
            print("✅ GPT-4o will be added")
        else:
            print("ℹ️  GPT-4o already exists")
        
        # GPT-4-turbo ekle
        if not existing_gpt4turbo:
            gpt4turbo = AIModelPricing(
                model_key="gpt-4-turbo",
                model_name="GPT-4 Turbo",
                provider="openai",
                credit_multiplier=2.0,  # Fast premium model
                description="Faster version of GPT-4. Great balance of speed and quality.",
                api_cost_per_1m_input=10.00,
                api_cost_per_1m_output=30.00,
                is_default=False,
                is_active=True
            )
            models_to_add.append(gpt4turbo)
            print("✅ GPT-4-turbo will be added")
        else:
            print("ℹ️  GPT-4-turbo already exists")
        
        if models_to_add:
            for model in models_to_add:
                db.add(model)
            db.commit()
            
            print(f"\n✅ Added {len(models_to_add)} OpenAI models successfully:")
            for model in models_to_add:
                print(f"   • {model.model_name}: {model.credit_multiplier}x")
                print(f"     API Cost: ${model.api_cost_per_1m_input}/1M in, ${model.api_cost_per_1m_output}/1M out")
        else:
            print("\nℹ️  All OpenAI models already exist, no changes made")
        
    except Exception as e:
        print(f"❌ Error adding OpenAI models: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Adding OpenAI models...")
    add_openai_models()
    print("✅ Migration completed successfully!")
