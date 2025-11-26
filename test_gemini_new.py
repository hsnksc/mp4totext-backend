"""
Gemini Enhancement Test - Yeni Model Testi
"""
from dotenv import load_dotenv
load_dotenv()

import os
from app.services.gemini_enhancement import create_gemini_service

print("=" * 60)
print("GEMINI ENHANCEMENT TEST - gemini-2.5-flash")
print("=" * 60)

# Test metni
test_text = """
Merhaba ben bir test metiniyim. Bu metin Gemini tarafından
iyileştirilecek ve özetlenecek. Noktalama işaretleri eksik
olabilir büyük küçük harf hatası olabilir ama Gemini bunları
düzeltecek.
"""

print("\n1. Gemini Servisi Oluşturuluyor...")
try:
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_service = create_gemini_service(api_key, model)
    if gemini_service:
        print(f"   ✅ Servis oluşturuldu: {gemini_service.model_name}")
    else:
        print("   ❌ Servis oluşturulamadı (API key eksik)")
        exit(1)
except Exception as e:
    print(f"   ❌ Hata: {e}")
    exit(1)

print("\n2. Test Metni Gönderiliyor...")
print(f"   Original: {test_text[:80]}...")

try:
    result = gemini_service.enhance_transcription(test_text, language="tr")
    print(f"   ✅ İşlem başarılı!")
    print(f"\n3. Sonuçlar:")
    print(f"   - Enhanced Text: {result.get('enhanced_text', 'N/A')[:100]}...")
    print(f"   - Summary: {result.get('summary', 'N/A')}")
    print(f"   - Improvements: {len(result.get('improvements', []))} adet")
    print(f"   - Model: {result.get('metadata', {}).get('model', 'N/A')}")
except Exception as e:
    print(f"   ❌ Hata: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test Tamamlandı!")
print("=" * 60)
