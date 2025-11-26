#!/usr/bin/env python3
"""Test Together AI Custom Prompt functionality"""
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.gemini_service import get_gemini_service
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_together_custom_prompt():
    """Test Together AI custom prompt enhancement"""
    
    print("=" * 60)
    print("🧪 Testing Together AI Custom Prompt")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY not found in environment")
        return False
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    # Sample text
    test_text = """
    Python is a high-level programming language. 
    It was created by Guido van Rossum in 1991.
    Python is known for its simple syntax and readability.
    """
    
    # Sample custom prompt
    custom_prompt = "Make this text more professional and add technical details."
    
    print(f"\n📝 Test Text: {test_text[:100]}...")
    print(f"📝 Custom Prompt: {custom_prompt}")
    
    try:
        # Get service
        gemini_service = get_gemini_service()
        print(f"\n🔧 Service initialized")
        
        # Call method with use_together=True
        print(f"\n🚀 Calling enhance_with_custom_prompt with use_together=True...")
        
        result = await gemini_service.enhance_with_custom_prompt(
            text=test_text,
            custom_prompt=custom_prompt,
            language="English",
            use_together=True
        )
        
        print(f"\n✅ SUCCESS! Result received:")
        print(f"  - Type: {type(result)}")
        print(f"  - Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        
        if isinstance(result, dict):
            if 'result' in result:
                print(f"\n📄 Result text: {result['result'][:200]}...")
            if 'metadata' in result:
                print(f"\n📊 Metadata: {result['metadata']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        
        # Print full traceback
        import traceback
        print("\n🔍 Full Traceback:")
        traceback.print_exc()
        
        return False

if __name__ == "__main__":
    success = asyncio.run(test_together_custom_prompt())
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test PASSED")
    else:
        print("❌ Test FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
