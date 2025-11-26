#!/usr/bin/env python3
"""Test Together AI API connectivity"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("🔑 Testing Together AI API Key")
print("=" * 60)

api_key = os.getenv("TOGETHER_API_KEY")
if not api_key:
    print("❌ TOGETHER_API_KEY not found in .env")
    exit(1)

print(f"✅ API Key found: {api_key[:20]}...{api_key[-10:]}")
print(f"   Length: {len(api_key)} chars")

print(f"\n🚀 Testing API connection...")

try:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.together.xyz/v1",
        timeout=30.0
    )
    
    print("📤 Sending simple test request...")
    
    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        messages=[
            {"role": "user", "content": "Say 'Hello' in JSON format: {\"message\": \"...\"}"}
        ],
        max_tokens=50,
        temperature=0.5
    )
    
    result = response.choices[0].message.content
    print(f"\n✅ SUCCESS! Together AI responded:")
    print(f"   {result[:100]}...")
    
    print(f"\n📊 Response details:")
    print(f"   Model: {response.model}")
    print(f"   Finish reason: {response.choices[0].finish_reason}")
    
    if hasattr(response, 'usage'):
        print(f"   Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")
    
    print(f"\n✅ Together AI API is working correctly!")
    
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}")
    print(f"   Message: {str(e)}")
    
    error_str = str(e).lower()
    if "authentication" in error_str or "401" in error_str:
        print(f"\n💡 Suggestion: Check if your API key is valid")
        print(f"   Visit: https://api.together.xyz/settings/api-keys")
    elif "rate" in error_str or "429" in error_str:
        print(f"\n💡 Suggestion: Rate limit reached, wait a moment")
    elif "timeout" in error_str:
        print(f"\n💡 Suggestion: Connection timeout, check network")
    else:
        print(f"\n💡 Suggestion: Check Together AI status")
        print(f"   Visit: https://status.together.xyz")
    
    import traceback
    print(f"\n🔍 Full traceback:")
    traceback.print_exc()
    
    exit(1)

print("\n" + "=" * 60)
