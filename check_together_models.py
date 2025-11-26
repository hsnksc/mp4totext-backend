"""Check available models in Together AI API using REST"""
import requests
from app.settings import get_settings

settings = get_settings()

print("🔍 Checking Together AI models...")
print(f"API Key: {'✅ Set' if settings.TOGETHER_API_KEY else '❌ Not set'}")
print()

if not settings.TOGETHER_API_KEY:
    print("❌ TOGETHER_API_KEY not found in environment")
    exit(1)

try:
    print("📡 Fetching models from Together AI REST API...")
    response = requests.get(
        "https://api.together.xyz/v1/models",
        headers={"Authorization": f"Bearer {settings.TOGETHER_API_KEY}"}
    )
    
    if response.status_code != 200:
        print(f"❌ API request failed: {response.status_code}")
        print(response.text)
        exit(1)
    
    models = response.json()
    
    # Filter for GPT models
    gpt_models = [m for m in models if 'gpt' in m.get('id', '').lower() or 'openai' in m.get('id', '').lower()]
    
    print(f"\n=== GPT/OpenAI Models in Together AI ({len(gpt_models)} found) ===")
    if gpt_models:
        for model in sorted(gpt_models, key=lambda x: x.get('id', '')):
            print(f"  • {model.get('id')}")
    else:
        print("  ❌ No GPT/OpenAI models found")
    
    # Check if our problematic model exists
    print(f"\n🔍 Checking for 'gpt-oss-120b'...")
    gpt_oss_models = [m for m in models if 'gpt-oss' in m.get('id', '').lower()]
    if gpt_oss_models:
        print(f"✅ Found {len(gpt_oss_models)} gpt-oss models:")
        for m in gpt_oss_models:
            print(f"  • {m.get('id')}")
    else:
        print("❌ No 'gpt-oss' models found in Together AI")
        print("\n💡 Suggestion: This model may have been removed from Together AI's API")
        print("   Update database to mark this model as inactive")
    
    # Show all Llama models (these are the working ones)
    llama_models = [m for m in models if 'llama' in m.get('id', '').lower()][:10]
    print(f"\n=== Available Llama Models (first 10) ===")
    for model in llama_models:
        print(f"  • {model.get('id')}")
    
    # Show all Mistral models
    mistral_models = [m for m in models if 'mistral' in m.get('id', '').lower()]
    if mistral_models:
        print(f"\n=== Available Mistral Models ===")
        for model in mistral_models:
            print(f"  • {model.get('id')}")
    
    # Show DeepSeek models
    deepseek_models = [m for m in models if 'deepseek' in m.get('id', '').lower()]
    if deepseek_models:
        print(f"\n=== Available DeepSeek Models ===")
        for model in deepseek_models:
            print(f"  • {model.get('id')}")
    
    print(f"\n📊 Total models available: {len(models)}")

except Exception as e:
    print(f"❌ Error fetching models: {e}")
    import traceback
    traceback.print_exc()
