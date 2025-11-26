"""
Together AI Karakter Bazlı Fiyatlandırma Güncellemesi
======================================================
1000 karakter başına kredi maliyeti güncelleme scripti
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

# Together AI modelleri için 1000 karakter başına kredi maliyetleri
# Kullanıcının verdiği tabloya göre güncelleme
TOGETHER_PRICING = {
    # FREE MODELS (0.0020 kredi/1000 char)
    "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free": 0.0020,
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B": 0.0020,  # Free version exists
    
    # GEMMA MODELS
    "google/gemma-3n-E4B-it": 0.0035,
    
    # SMALL MODELS (3B-8B)
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": 0.0198,
    
    # MEDIUM MODELS (20B-70B)
    "openai/gpt-oss-20b": 0.0146,
    "openai/gpt-oss-120b": 0.0435,
    "meta-llama/Llama-3.3-70B-Instruct-Turbo": 0.0968,
    "llama-3.3-70b-together": 0.0968,
    
    # TURBO MODELS
    "Qwen/Qwen2.5-7B-Instruct-Turbo": 0.0330,
    "Qwen/Qwen2.5-72B-Instruct-Turbo": 0.1320,
    
    # LARGE MODELS (235B-405B)
    "Qwen/Qwen3-235B-A22B-Instruct-2507": 0.0461,
    "Qwen/Qwen3-235B-A22B-Thinking-2507": 0.2126,
    "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": 0.3849,
    "llama-3.1-405b-instruct-turbo": 0.3849,
    
    # SPECIALIST MODELS
    "meta-llama/Llama-4-Scout-17B-16E-Instruct": 0.0450,
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8": 0.0645,
    "mistralai/Mistral-Small-24B-Instruct-2501": 0.0879,
    "mistralai/Magistral-Small-2506": 0.0879,
    
    # DEEPSEEK V3 FAMILY
    "deepseek-ai/DeepSeek-V3.1": 0.1320,
    "deepseek-ai/DeepSeek-R1": 0.4350,
    
    # KIMI MODELS
    "moonshotai/Kimi-K2-Instruct-0905": 0.1850,
    
    # ARCEE AI
    "arcee-ai/virtuoso-medium-v2": 0.1095,
}

def update_together_models():
    """Update cost_per_1k_chars for existing Together AI models"""
    db = SessionLocal()
    
    try:
        updated_count = 0
        not_found = []
        
        print("� Updating Together AI model pricing (character-based)...")
        print("=" * 80)
        
        for model_key, cost in TOGETHER_PRICING.items():
            # Find model in database
            model = db.query(AIModelPricing).filter(
                AIModelPricing.model_key == model_key,
                AIModelPricing.provider == "together"
            ).first()
            
            if model:
                old_cost = model.cost_per_1k_chars
                model.cost_per_1k_chars = cost
                
                print(f"✅ {model.model_name}")
                print(f"   Model Key: {model_key}")
                print(f"   Old: {old_cost} → New: {cost:.4f} kredi/1000 karakter")
                print()
                
                updated_count += 1
            else:
                not_found.append(model_key)
        
        # Commit changes
        db.commit()
        
        print("=" * 80)
        print(f"✅ Successfully updated {updated_count} Together AI models")
        
        if not_found:
            print(f"\n⚠️ {len(not_found)} model(s) not found in database:")
            for key in not_found:
                print(f"   - {key}")
        
        # Show summary
        print("\n📊 PRICING SUMMARY (sorted by cost):")
        print("-" * 80)
        models = db.query(AIModelPricing).filter_by(provider="together").order_by(
            AIModelPricing.cost_per_1k_chars
        ).all()
        
        for m in models:
            if m.cost_per_1k_chars:
                # Example: 10,000 karakter = 10 × cost_per_1k_chars kredi
                example_chars = 10000
                example_cost = (example_chars / 1000) * m.cost_per_1k_chars
                print(f"   {m.cost_per_1k_chars:.4f} kredi/1K | {example_cost:.2f} kredi/10K | {m.model_name}")
        
        print("-" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_together_models()
