"""
Gemini Character-Based Pricing Update
1000 karakter basina kredi maliyeti guncelleme scripti
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

GEMINI_PRICING = {
    "gemini-2.5-flash-lite": 0.0322,
    "gemini-flash-latest": 0.0644,
    "gemini-2.0-flash": 0.0725,
    "gemini-2.5-flash": 0.0805,
    "gemini-2.5-pro": 0.2415,
}

def update_gemini_models():
    db = SessionLocal()
    try:
        updated_count = 0
        print("Updating Gemini model pricing (character-based)...")
        print("=" * 80)
        
        for model_key, cost in GEMINI_PRICING.items():
            model = db.query(AIModelPricing).filter(
                AIModelPricing.model_key == model_key,
                AIModelPricing.provider == "gemini"
            ).first()
            
            if model:
                old_cost = model.cost_per_1k_chars
                model.cost_per_1k_chars = cost
                print(f"OK {model.model_name}")
                print(f"   Old: {old_cost} - New: {cost:.4f} kredi/1000 karakter")
                print()
                updated_count += 1
            else:
                print(f"NOT FOUND: {model_key}")
                print()
        
        db.commit()
        print("=" * 80)
        print(f"Successfully updated {updated_count} Gemini models")
        
        print("\nPRICING SUMMARY:")
        print("-" * 80)
        models = db.query(AIModelPricing).filter_by(provider="gemini").order_by(
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
    update_gemini_models()
