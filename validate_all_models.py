"""
Comprehensive model validation report
Compares database models with actual API models
"""
import requests
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing
from app.settings import get_settings

settings = get_settings()

def check_together_ai():
    print("\n" + "=" * 80)
    print("🔍 TOGETHER AI MODELS")
    print("=" * 80)
    
    # Get API models
    try:
        response = requests.get(
            "https://api.together.xyz/v1/models",
            headers={"Authorization": f"Bearer {settings.TOGETHER_API_KEY}"}
        )
        api_models = {m.get('id') for m in response.json()}
        print(f"\n📡 API has {len(api_models)} total models")
    except Exception as e:
        print(f"❌ API error: {e}")
        return
    
    # Get database models
    db = SessionLocal()
    try:
        db_models = db.query(AIModelPricing).filter_by(provider='together').all()
        print(f"💾 Database has {len(db_models)} Together AI models")
        
        print("\n📊 Database Models Status:")
        print("-" * 80)
        for model in db_models:
            exists_in_api = model.model_key in api_models
            status = "✅" if exists_in_api else "❌"
            active = "🟢 Active" if model.is_active else "🔴 Inactive"
            print(f"{status} {active} | {model.model_key}")
            if not exists_in_api and model.is_active:
                print(f"   ⚠️  WARNING: Active in DB but NOT in API!")
        print("-" * 80)
        
    finally:
        db.close()

def check_groq():
    print("\n" + "=" * 80)
    print("⚡ GROQ MODELS")
    print("=" * 80)
    
    # Get API models
    try:
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
        )
        api_models = {m.get('id') for m in response.json().get('data', [])}
        print(f"\n📡 API has {len(api_models)} total models")
        
        # Show chat models
        chat_models = {m for m in api_models if any(x in m.lower() for x in ['llama', 'gpt', 'mixtral', 'qwen', 'gemma'])}
        print(f"💬 Chat models: {len(chat_models)}")
        for m in sorted(chat_models):
            print(f"   • {m}")
            
    except Exception as e:
        print(f"❌ API error: {e}")
        return
    
    # Get database models
    db = SessionLocal()
    try:
        db_models = db.query(AIModelPricing).filter_by(provider='groq').all()
        print(f"\n💾 Database has {len(db_models)} Groq models")
        
        print("\n📊 Database Models Status:")
        print("-" * 80)
        for model in db_models:
            exists_in_api = model.model_key in api_models
            status = "✅" if exists_in_api else "❌"
            active = "🟢 Active" if model.is_active else "🔴 Inactive"
            print(f"{status} {active} | {model.model_key}")
            if not exists_in_api and model.is_active:
                print(f"   ⚠️  WARNING: Active in DB but NOT in API!")
        print("-" * 80)
        
        # Check for new models in API not in DB
        db_model_keys = {m.model_key for m in db_models}
        new_models = chat_models - db_model_keys
        if new_models:
            print(f"\n🆕 New models available in API (not in database):")
            for m in sorted(new_models):
                print(f"   • {m}")
        
    finally:
        db.close()

def check_openai():
    print("\n" + "=" * 80)
    print("🤖 OPENAI MODELS")
    print("=" * 80)
    
    # Get database models
    db = SessionLocal()
    try:
        db_models = db.query(AIModelPricing).filter_by(provider='openai').all()
        print(f"💾 Database has {len(db_models)} OpenAI models")
        
        print("\n📊 Database Models:")
        print("-" * 80)
        for model in db_models:
            active = "🟢 Active" if model.is_active else "🔴 Inactive"
            print(f"{active} | {model.model_key} | {model.model_name}")
        print("-" * 80)
        
    finally:
        db.close()

def check_gemini():
    print("\n" + "=" * 80)
    print("✨ GEMINI MODELS")
    print("=" * 80)
    
    # Get database models
    db = SessionLocal()
    try:
        db_models = db.query(AIModelPricing).filter_by(provider='gemini').all()
        print(f"💾 Database has {len(db_models)} Gemini models")
        
        print("\n📊 Database Models:")
        print("-" * 80)
        for model in db_models:
            active = "🟢 Active" if model.is_active else "🔴 Inactive"
            print(f"{active} | {model.model_key} | {model.model_name}")
        print("-" * 80)
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 COMPREHENSIVE MODEL VALIDATION REPORT")
    print("=" * 80)
    
    check_together_ai()
    check_groq()
    check_openai()
    check_gemini()
    
    print("\n" + "=" * 80)
    print("✅ Report complete!")
    print("=" * 80)
