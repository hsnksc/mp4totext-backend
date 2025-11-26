"""
Test Gemini Text Enhancement
Simple test to verify Gemini integration works
"""

import asyncio
from app.services.gemini_service import get_gemini_service


async def test_gemini():
    """Test Gemini service"""
    
    print("\n" + "="*60)
    print("🧪 Testing Gemini AI Text Enhancement")
    print("="*60 + "\n")
    
    # Get Gemini service
    gemini = get_gemini_service()
    
    # Check if enabled
    print(f"✓ Gemini service enabled: {gemini.is_enabled()}")
    
    if not gemini.is_enabled():
        print("\n❌ Gemini service is not enabled!")
        print("   Please set a valid GEMINI_API_KEY in .env file")
        return
    
    # Test text (Turkish)
    test_text = """
    merhaba ben bugün bir toplantı yaptım eh şirkette yeni projeler var
    sanırım gelecek ay başlayacağız ama ee henüz detayları bilmiyorum
    acaba ne zaman bilgi verilecek bilmiyorum ama umuyoruz ki yakında olur
    toplantıda 5 kişi vardı hepsi proje hakkında konuştu
    """
    
    print("\n📝 Original Text:")
    print("-" * 60)
    print(test_text.strip())
    print("-" * 60)
    
    try:
        print("\n🚀 Calling Gemini API...")
        print("   (This may take 5-10 seconds)")
        
        result = await gemini.enhance_text(
            text=test_text,
            language="tr",
            include_summary=True
        )
        
        print("\n✅ Enhancement Completed!")
        print("\n" + "="*60)
        print("🎨 ENHANCED TEXT:")
        print("="*60)
        print(result["enhanced_text"])
        
        if result.get("summary"):
            print("\n" + "="*60)
            print("📋 SUMMARY:")
            print("="*60)
            print(result["summary"])
        
        print("\n" + "="*60)
        print("📊 METADATA:")
        print("="*60)
        print(f"Model: {result.get('model_used')}")
        print(f"Original length: {result.get('original_length')} chars")
        print(f"Enhanced length: {result.get('enhanced_length')} chars")
        print(f"Word count: {result.get('word_count')} words")
        print(f"Language: {result.get('language')}")
        
        if result.get("improvements"):
            print("\n" + "="*60)
            print("🔧 IMPROVEMENTS:")
            print("="*60)
            for i, improvement in enumerate(result["improvements"], 1):
                print(f"{i}. {improvement}")
        
        print("\n" + "="*60)
        print("✅ TEST PASSED!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_gemini())
