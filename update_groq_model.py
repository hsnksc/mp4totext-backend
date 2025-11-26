"""
Update Groq model in database to new supported model
Groq deprecated llama-3.1-70b-versatile, replace with llama-3.3-70b-versatile
"""

from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

def update_groq_model():
    db = SessionLocal()
    try:
        # Find old Groq model
        old_model = db.query(AIModelPricing).filter_by(
            model_key="llama-3.1-70b-versatile",
            provider="groq"
        ).first()
        
        if old_model:
            print(f"📝 Found old model: {old_model.model_name}")
            print(f"   Key: {old_model.model_key}")
            print(f"   Multiplier: {old_model.credit_multiplier}")
            print(f"   Active: {old_model.is_active}")
            
            # Update to new model
            old_model.model_key = "llama-3.3-70b-versatile"
            old_model.model_name = "Llama 3.3 70B Versatile"
            old_model.description = "Groq's latest Llama 3.3 70B - Fast & accurate"
            
            db.commit()
            print("✅ Model updated successfully!")
            print(f"   New key: {old_model.model_key}")
            print(f"   New name: {old_model.model_name}")
        else:
            print("⚠️ Old model not found in database")
            
            # Check if new model already exists
            new_model = db.query(AIModelPricing).filter_by(
                model_key="llama-3.3-70b-versatile",
                provider="groq"
            ).first()
            
            if new_model:
                print(f"✅ New model already exists: {new_model.model_name}")
            else:
                print("❌ Neither old nor new model found!")
                print("\n📋 All Groq models in database:")
                groq_models = db.query(AIModelPricing).filter_by(provider="groq").all()
                for m in groq_models:
                    print(f"   - {m.model_key} ({m.model_name}) - Active: {m.is_active}")
                    
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Updating Groq model in database...\n")
    update_groq_model()
