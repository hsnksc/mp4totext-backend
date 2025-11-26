"""Check available models in Groq API"""
import requests
from app.settings import get_settings

settings = get_settings()

print("🔍 Checking Groq API models...")
print(f"API Key: {'✅ Set' if settings.GROQ_API_KEY else '❌ Not set'}")
print()

if not settings.GROQ_API_KEY:
    print("❌ GROQ_API_KEY not found in environment")
    exit(1)

try:
    print("📡 Fetching models from Groq API...")
    response = requests.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    )
    
    if response.status_code != 200:
        print(f"❌ API request failed: {response.status_code}")
        print(response.text)
        exit(1)
    
    data = response.json()
    models = data.get('data', [])
    
    print(f"\n=== ALL Groq Models ({len(models)} found) ===")
    for model in sorted(models, key=lambda x: x.get('id', '')):
        model_id = model.get('id', '')
        context = model.get('context_window', 'N/A')
        print(f"  • {model_id} (context: {context})")
    
    # Check for GPT models
    gpt_models = [m for m in models if 'gpt' in m.get('id', '').lower()]
    if gpt_models:
        print(f"\n=== GPT Models ({len(gpt_models)}) ===")
        for m in gpt_models:
            print(f"  • {m.get('id')} (context: {m.get('context_window', 'N/A')})")
    else:
        print(f"\n❌ No GPT models found in Groq")
        print("💡 'gpt-oss-120b' does NOT exist in Groq API")

except Exception as e:
    print(f"❌ Error fetching models: {e}")
    import traceback
    traceback.print_exc()
