"""
Groq Character-Based Pricing Update
1000 karakter basina kredi maliyeti guncelleme scripti
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

GROQ_PRICING = {
    "llama-3.1-8b-instant": 0.0073,
    "openai/gpt-oss-20b": 0.0217,
    "meta-llama/llama-guard-4-12b": 0.0220,
    "openai/gpt-oss-120b": 0.0435,
    "llama-3.3-70b-versatile": 0.0769,
}

def update_groq_models():
    db = SessionLocal()
    try:
        updated_count = 0
        not_found = []
        print("Updating Groq model pricing (character-based)...")
        print("=" * 80)
        
        for model_key, cost in GROQ_PRICING.items():
            model = db.query(AIModelPricing).filter(
                AIModelPricing.model_key == model_key,
                AIModelPricing.provider == "groq"
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
        print(f"Successfully updated {updated_count} Groq models")
        
        if not_found:
            print(f"\n{len(not_found)} model(s) not found:")
            for key in not_found:
                print(f"   - {key}")
        
        print("\nPRICING SUMMARY:")
        print("-" * 80)
        models = db.query(AIModelPricing).filter_by(provider="groq").order_by(
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
    update_groq_models()
