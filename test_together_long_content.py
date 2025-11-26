#!/usr/bin/env python3
"""Test Together AI with long content request"""
import os
import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.gemini_service import get_gemini_service
from dotenv import load_dotenv

load_dotenv()

async def test_long_content():
    print("=" * 60)
    print("📝 Testing Together AI with '5 sayfa makale' request")
    print("=" * 60)
    
    # Turkish transcription text
    test_text = """
    İki bin yirmi dört, yirmi beş öğretim döneminde, Akdeniz Üniversitesi, Sosyoloji bölümünde yeni bir ders planlıyoruz.
    Bu dersin adı Rüşvet ve Yolsuzluğun Sosyolojisi. Aslında bu ders sosyolojik bir bakış açısıyla, eşitsizliklerin 
    temel nedenlerini ve küresel düzeydeki tartışmaları incelemeyi amaçlıyor.
    """
    
    # Request 5-page article
    custom_prompt = "Bu metinden yola çıkarak 5 sayfalık detaylı bir akademik makale yaz. Başlık, giriş, ana bölümler ve sonuç olsun."
    
    print(f"\n📄 Test Text: {test_text[:100]}...")
    print(f"📝 Custom Prompt: {custom_prompt}")
    
    try:
        gemini_service = get_gemini_service()
        print(f"\n🚀 Calling Together AI (Llama 3.1 405B)...")
        
        result = await gemini_service.enhance_with_custom_prompt(
            text=test_text,
            custom_prompt=custom_prompt,
            language="Turkish",
            use_together=True
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"  - Word count: {result.get('metadata', {}).get('word_count', 'N/A')}")
        
        processed_text = result.get('processed_text', '')
        print(f"  - Character count: {len(processed_text)}")
        print(f"  - Estimated pages: {len(processed_text.split()) / 350:.1f} pages (350 words/page)")
        
        print(f"\n📄 First 500 chars of result:")
        print(processed_text[:500] + "...\n")
        
        # Check if it meets 5-page requirement (1500+ words)
        word_count = result.get('metadata', {}).get('word_count', 0)
        if word_count >= 1500:
            print(f"✅ Length requirement MET: {word_count} words ≈ {word_count/350:.1f} pages")
            return True
        else:
            print(f"⚠️ Length requirement NOT MET: {word_count} words ≈ {word_count/350:.1f} pages (expected: 1500+ words)")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_long_content())
    print("\n" + "=" * 60)
    print("✅ Test PASSED" if success else "⚠️ Test COMPLETED (check results)")
    print("=" * 60)
