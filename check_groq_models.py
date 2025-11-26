"""
Check all Groq models in database
"""
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

def check_groq_models():
    db = SessionLocal()
    try:
        # Get all Groq models
        groq_models = db.query(AIModelPricing).filter_by(provider="groq").all()
        
        print("📊 Groq models in database:")
        print("-" * 80)
        
        for model in groq_models:
            status = "✅ Active" if model.is_active else "❌ Inactive"
            default = "⭐ DEFAULT" if model.is_default else ""
            print(f"{status} {default}")
            print(f"   Model Key: {model.model_key}")
            print(f"   Model Name: {model.model_name}")
            print(f"   Credit Multiplier: {model.credit_multiplier}x")
            print(f"   Description: {model.description}")
            print("-" * 80)
        
        if not groq_models:
            print("⚠️ No Groq models found in database!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_groq_models()
