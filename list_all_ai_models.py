"""
Check all AI models in database - grouped by provider
"""
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

def check_all_models():
    db = SessionLocal()
    try:
        # Get all models
        all_models = db.query(AIModelPricing).order_by(
            AIModelPricing.provider,
            AIModelPricing.credit_multiplier
        ).all()
        
        print("🤖 ALL AI MODELS IN DATABASE")
        print("=" * 100)
        
        # Group by provider
        providers = {}
        for model in all_models:
            if model.provider not in providers:
                providers[model.provider] = []
            providers[model.provider].append(model)
        
        # Display by provider
        for provider, models in sorted(providers.items()):
            print(f"\n📦 {provider.upper()} ({len(models)} models)")
            print("-" * 100)
            
            for model in models:
                status = "✅" if model.is_active else "❌"
                default = "⭐ DEFAULT" if model.is_default else ""
                
                print(f"{status} {model.model_name} {default}")
                print(f"   Key: {model.model_key}")
                print(f"   Multiplier: {model.credit_multiplier}x")
                if model.api_cost_per_1m_input:
                    print(f"   API Cost: ${model.api_cost_per_1m_input:.3f} in / ${model.api_cost_per_1m_output:.3f} out per 1M tokens")
                print(f"   {model.description}")
                print()
        
        print("=" * 100)
        print(f"📊 SUMMARY: {len(all_models)} total models across {len(providers)} providers")
        
        # Count by provider
        for provider, models in sorted(providers.items()):
            active_count = sum(1 for m in models if m.is_active)
            print(f"   {provider}: {active_count}/{len(models)} active")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_all_models()
