"""
Quick test for Tavily web search integration
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.services.web_search_service import get_web_search_service

async def test_web_search():
    print("🧪 Testing Tavily Web Search Service\n")
    
    service = get_web_search_service()
    
    if not service.is_enabled():
        print("❌ Web search is not enabled!")
        print("   Check TAVILY_API_KEY and ENABLE_WEB_SEARCH in .env")
        return
    
    print("✅ Web search service initialized\n")
    
    # Test 1: Extract keywords
    test_text = """
    Almanya'daki İAA forında Tevon Feinin tanıtılmasının ardından uygun fiyatlı 
    yeni modeli içinde marka CEO'su Türkiye pazarında da satışa sunulacağını duyurdu.
    T8X modeli elektrikli SUV segmentinde yer alacak.
    """
    
    print(f"📝 Test Text:\n{test_text}\n")
    
    keywords = service.extract_keywords(test_text, max_keywords=5)
    print(f"🔑 Extracted Keywords: {keywords}\n")
    
    # Test 2: Web search
    print("🔍 Searching web for context...\n")
    
    result = await service.search_context(
        query=keywords,
        language="tr",
        max_results=3
    )
    
    if result.get("success"):
        print(f"✅ Search successful!")
        print(f"   Query: {result.get('query_used')}")
        print(f"   Results: {result.get('num_results')}")
        print(f"   Answer: {result.get('answer', 'N/A')[:100]}...")
        print(f"\n📄 Context Preview (first 500 chars):")
        print(f"{result.get('context', '')[:500]}...\n")
    else:
        print(f"❌ Search failed: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_web_search())
