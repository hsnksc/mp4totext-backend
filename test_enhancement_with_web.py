"""
Test web search integration in enhance_text
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.services.gemini_service import GeminiService

async def test_enhancement_with_web():
    print("🧪 Testing AI Enhancement with Web Search\n")
    
    # Sample transcription text
    test_text = """
    Almanya'daki İAA forında Tevon Feinin tanıtılmasının ardından uygun fiyatlı 
    yeni modeli içinde marka CEO'su Gürcan Karakaş Türkiye pazarında da satışa 
    sunulacağını duyurdu. T8X modeli elektrikli SUV segmentinde yer alacak ve 
    2024 yılında piyasaya sürülecek.
    """
    
    print(f"📝 Original Text:\n{test_text}\n")
    
    # Test with OpenAI
    print("=" * 70)
    print("TEST 1: OpenAI GPT-4o-mini with Web Search")
    print("=" * 70)
    
    gemini = GeminiService(preferred_provider="openai", preferred_model="gpt-4o-mini")
    
    result = await gemini.enhance_text(
        text=test_text,
        language="tr",
        include_summary=True,
        enable_web_search=True  # 🔍 WEB SEARCH ENABLED
    )
    
    print(f"\n✅ Enhancement Complete!")
    print(f"   Provider: {result.get('provider')}")
    print(f"   Model: {result.get('model_used')}")
    print(f"   Web Search: {result.get('web_search_enabled')}")
    print(f"   Search Query: {result.get('web_search_query', 'N/A')}")
    print(f"   Search Results: {result.get('web_search_results_count', 0)}")
    
    print(f"\n📄 Enhanced Text:\n{result.get('enhanced_text')}\n")
    print(f"📊 Summary:\n{result.get('summary', 'N/A')}\n")
    
    if result.get('web_search_enabled'):
        print("✅ Web search was used!")
    else:
        print("⚠️  Web search was NOT used")

if __name__ == "__main__":
    asyncio.run(test_enhancement_with_web())
