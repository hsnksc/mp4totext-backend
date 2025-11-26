"""Fix model keys in database to match actual API model names"""
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

# Strategy: Since model_key must be unique, we'll DELETE old wrong entries 
# and rely on the correct ones that may already exist
# If correct one doesn't exist, we'll update the old one

MODELS_TO_FIX = {
    # Together AI - Fix incorrect prefixes
    "together": {
        "together-openai/gpt-oss-120b": "openai/gpt-oss-120b",
        "together-openai/gpt-oss-20b": "openai/gpt-oss-20b",
    },
    # Groq - Fix incorrect prefixes
    "groq": {
        "groq-openai/gpt-oss-120b": "openai/gpt-oss-120b",
        "groq-openai/gpt-oss-20b": "openai/gpt-oss-20b",
    }
}

def fix_model_keys():
    db = SessionLocal()
    try:
        print("🔧 Fixing model keys in database...")
        print("=" * 80)
        
        total_deleted = 0
        total_updated = 0
        
        for provider, mappings in MODELS_TO_FIX.items():
            print(f"\n📦 Processing {provider.upper()} models...")
            
            for old_key, new_key in mappings.items():
                old_model = db.query(AIModelPricing).filter_by(
                    model_key=old_key, 
                    provider=provider
                ).first()
                
                if not old_model:
                    print(f"   ⏭️  Skip: {old_key} (not found)")
                    continue
                
                print(f"\n   ✏️  Found: {old_key}")
                print(f"      Old key: {old_key}")
                print(f"      New key: {new_key}")
                print(f"      Model name: {old_model.model_name}")
                
                # Check if correct key already exists for this provider
                correct_model = db.query(AIModelPricing).filter_by(
                    model_key=new_key,
                    provider=provider
                ).first()
                
                if correct_model:
                    # Correct one exists, delete the old one
                    print(f"      ✅ Correct model already exists (ID: {correct_model.id})")
                    print(f"      🗑️  Deleting old incorrect entry (ID: {old_model.id})")
                    db.delete(old_model)
                    total_deleted += 1
                else:
                    # Correct one doesn't exist, update the old one
                    print(f"      🔄 Updating to correct key")
                    old_model.model_key = new_key
                    # Commit immediately to avoid unique constraint conflicts
                    db.commit()
                    total_updated += 1
        
        if total_deleted > 0:
            db.commit()
            print(f"\n" + "=" * 80)
            print(f"✅ Successfully fixed models:")
            print(f"   🗑️  Deleted: {total_deleted}")
            print(f"   🔄 Updated: {total_updated}")
            print("=" * 80)
        else:
            print(f"\n" + "=" * 80)
            print("ℹ️  No models to fix")
            print("=" * 80)
        
        # Verify fixes
        print("\n📊 Verification - GPT-OSS models after fix:")
        print("-" * 80)
        gpt_models = db.query(AIModelPricing).filter(
            AIModelPricing.model_key.like('%gpt-oss%')
        ).all()
        
        for m in gpt_models:
            status = "✅ Active" if m.is_active else "❌ Inactive"
            print(f"{status} | {m.model_key} | {m.provider} | {m.model_name}")
        print("-" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_model_keys()
