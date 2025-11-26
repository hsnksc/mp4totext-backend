"""
OpenAI Character-Based Pricing Update
1000 karakter basina kredi maliyeti guncelleme scripti
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

OPENAI_PRICING = {
    "gpt-5-nano": 0.0265,
    "gpt-4.1-nano-2025-04-14": 0.0290,
    "gpt-4o-mini": 0.0435,
    "gpt-4.1-mini-2025-04-14": 0.1160,
    "gpt-5-mini": 0.1325,
    "gpt-4.1-2025-04-14": 0.5799,
    "gpt-5": 0.6624,
    "gpt-4o": 0.7249,
    "gpt-4o-2024-05-13": 1.1498,
    "gpt-5-pro": 7.9493,
}

def update_openai_models():
    db = SessionLocal()
    try:
        updated_count = 0
        not_found = []
        print("Updating OpenAI model pricing (character-based)...")
        print("=" * 80)
        
        for model_key, cost in OPENAI_PRICING.items():
            model = db.query(AIModelPricing).filter(
                AIModelPricing.model_key == model_key,
                AIModelPricing.provider == "openai"
            ).first()
            
            if model:
                old_cost = model.cost_per_1k_chars
                model.cost_per_1k_chars = cost
                print(f"OK {model.model_name}")
                print(f"   Old: {old_cost} - New: {cost:.4f} kredi/1000 karakter")
                print()
                updated_count += 1
            else:
                not_found.append(model_key)
                print(f"NOT FOUND: {model_key}")
                print()
        
        db.commit()
        print("=" * 80)
        print(f"Successfully updated {updated_count} OpenAI models")
        
        if not_found:
            print(f"\n{len(not_found)} model(s) not found:")
            for key in not_found:
                print(f"   - {key}")
        
        print("\nPRICING SUMMARY:")
        print("-" * 80)
        models = db.query(AIModelPricing).filter_by(provider="openai").order_by(
            AIModelPricing.cost_per_1k_chars
        ).all()
        
        for m in models:
            if m.cost_per_1k_chars:
                example_cost = (10000 / 1000) * m.cost_per_1k_chars
                print(f"   {m.cost_per_1k_chars:.4f} kredi/1K | {example_cost:.2f} kredi/10K | {m.model_name}")
        print("-" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_openai_models()
