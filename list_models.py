"""List available Gemini models"""
import google.generativeai as genai
from app.settings import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

print("\n" + "="*60)
print("Available Gemini Models:")
print("="*60)

for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n✓ {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Description: {model.description[:80]}...")
