"""
Add Together AI Llama 3.1 405B Instruct Turbo model to database
This is the world's largest open-source model with 405B parameters
"""
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

def add_together_405b_model():
    db = SessionLocal()
    try:
        # Check if model already exists
        existing = db.query(AIModelPricing).filter(
            AIModelPricing.model_key == "llama-3.1-405b-instruct-turbo"
        ).first()
        
        if existing:
            print(f"⚠️ Model already exists: {existing.model_name}")
            return
        
        print("🚀 Adding Together AI Llama 3.1 405B Instruct Turbo...")
        
        # Add Llama 3.1 405B Instruct Turbo
        model_405b = AIModelPricing(
            model_key="llama-3.1-405b-instruct-turbo",
            model_name="Llama 3.1 405B Instruct Turbo",
            provider="together",
            credit_multiplier=1.8,  # Premium large model, but cheaper than GPT-4
            description="World's largest open-source model with 405B parameters. Best for complex tasks and highest quality output. May be slower but delivers premium results.",
            api_cost_per_1m_input=3.50,  # Together AI pricing
            api_cost_per_1m_output=3.50,
            is_default=False,
            is_active=True
        )
        
        db.add(model_405b)
        db.commit()
        
        print("\n✅ Added Together AI 405B model successfully:")
        print(f"   • {model_405b.model_name}: {model_405b.credit_multiplier}x")
        print(f"     API Cost: ${model_405b.api_cost_per_1m_input}/1M in, ${model_405b.api_cost_per_1m_output}/1M out")
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_together_405b_model()
