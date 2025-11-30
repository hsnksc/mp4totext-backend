"""
🚀 Push AI Models to Production via API
Reads models from migrate_all_ai_models.py and sends to production
"""
import requests
import json

# Production API
API_URL = "https://api.gistify.pro/api/v1"

# All models to add (from migrate_all_ai_models.py)
MODELS = [
    # ========== GEMINI ==========
    {"model_key": "gemini-flash-latest", "model_name": "Gemini Flash (Latest)", "provider": "gemini", "credit_multiplier": 0.8, "api_cost_per_1m_input": 0.05, "api_cost_per_1m_output": 0.20, "description": "Latest Flash model with automatic updates. Fast and efficient.", "is_active": True, "is_default": False},
    {"model_key": "gemini-2.5-pro", "model_name": "Gemini 2.5 Pro", "provider": "gemini", "credit_multiplier": 3.0, "api_cost_per_1m_input": 1.25, "api_cost_per_1m_output": 5.00, "description": "Most capable Gemini model. Best for complex reasoning and analysis.", "is_active": True, "is_default": False},
    {"model_key": "gemini-2.5-flash", "model_name": "Gemini 2.5 Flash", "provider": "gemini", "credit_multiplier": 1.0, "api_cost_per_1m_input": 0.075, "api_cost_per_1m_output": 0.30, "description": "Balanced speed and intelligence. Default model.", "is_active": True, "is_default": True},
    {"model_key": "gemini-2.5-flash-lite", "model_name": "Gemini 2.5 Flash Lite", "provider": "gemini", "credit_multiplier": 0.4, "api_cost_per_1m_input": 0.025, "api_cost_per_1m_output": 0.10, "description": "Fastest and cheapest Gemini. Good for simple tasks.", "is_active": True, "is_default": False},
    {"model_key": "gemini-2.0-flash", "model_name": "Gemini 2.0 Flash", "provider": "gemini", "credit_multiplier": 0.9, "api_cost_per_1m_input": 0.065, "api_cost_per_1m_output": 0.28, "description": "Previous generation Flash. Still very capable.", "is_active": True, "is_default": False},

    # ========== TOGETHER AI ==========
    # Llama 4 Series
    {"model_key": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", "model_name": "Llama 4 Maverick 17Bx128E", "provider": "together", "credit_multiplier": 2.5, "api_cost_per_1m_input": 0.30, "api_cost_per_1m_output": 0.60, "description": "Latest Llama 4! 1M context window. 17B × 128 experts MoE architecture.", "is_active": True, "is_default": False},
    {"model_key": "meta-llama/Llama-4-Scout-17B-16E-Instruct", "model_name": "Llama 4 Scout 17Bx16E", "provider": "together", "credit_multiplier": 2.0, "api_cost_per_1m_input": 0.25, "api_cost_per_1m_output": 0.50, "description": "Llama 4 smaller variant. 1M context, 17B × 16 experts.", "is_active": True, "is_default": False},
    
    # Llama 3.3 Series
    {"model_key": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "model_name": "Llama 3.3 70B Turbo", "provider": "together", "credit_multiplier": 1.8, "api_cost_per_1m_input": 0.88, "api_cost_per_1m_output": 0.88, "description": "Recommended! Latest Llama 3.3. 131K context, FP8 quantization.", "is_active": True, "is_default": False},
    {"model_key": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "model_name": "Llama 3.3 70B Turbo (Free)", "provider": "together", "credit_multiplier": 0.5, "api_cost_per_1m_input": 0.00, "api_cost_per_1m_output": 0.00, "description": "Free tier. 8K context limit. Good for testing.", "is_active": True, "is_default": False},
    
    # Llama 3.1 Series
    {"model_key": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "model_name": "Llama 3.1 405B Turbo", "provider": "together", "credit_multiplier": 3.5, "api_cost_per_1m_input": 3.50, "api_cost_per_1m_output": 3.50, "description": "Largest open-source model. 405B parameters, 131K context.", "is_active": True, "is_default": False},
    {"model_key": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo", "model_name": "Llama 3.1 8B Turbo", "provider": "together", "credit_multiplier": 0.4, "api_cost_per_1m_input": 0.18, "api_cost_per_1m_output": 0.18, "description": "Fast and cheap. 131K context, FP8 quantization.", "is_active": True, "is_default": False},
    {"model_key": "llama-3.1-405b-instruct-turbo", "model_name": "Llama 3.1 405B Instruct Turbo", "provider": "together", "credit_multiplier": 3.5, "api_cost_per_1m_input": 3.50, "api_cost_per_1m_output": 3.50, "description": "Largest open-source model - alternative key.", "is_active": True, "is_default": False},
    {"model_key": "llama-3.3-70b-together", "model_name": "Llama 3.3 70B (Together AI)", "provider": "together", "credit_multiplier": 1.8, "api_cost_per_1m_input": 0.88, "api_cost_per_1m_output": 0.88, "description": "Alternative key for Llama 3.3 70B.", "is_active": True, "is_default": False},
    
    # DeepSeek Models
    {"model_key": "deepseek-ai/DeepSeek-V3.1", "model_name": "DeepSeek V3.1", "provider": "together", "credit_multiplier": 2.8, "api_cost_per_1m_input": 0.55, "api_cost_per_1m_output": 2.19, "description": "Latest DeepSeek! 128K context, FP8, excellent reasoning.", "is_active": True, "is_default": False},
    {"model_key": "deepseek-ai/DeepSeek-R1", "model_name": "DeepSeek R1 (Reasoning)", "provider": "together", "credit_multiplier": 3.0, "api_cost_per_1m_input": 0.55, "api_cost_per_1m_output": 2.19, "description": "Reasoning model. 163K context, excels at complex logic.", "is_active": True, "is_default": False},
    {"model_key": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B", "model_name": "DeepSeek R1 Distill 70B", "provider": "together", "credit_multiplier": 1.5, "api_cost_per_1m_input": 0.20, "api_cost_per_1m_output": 0.20, "description": "Distilled version of R1. 131K context, faster inference.", "is_active": True, "is_default": False},
    
    # Qwen Models
    {"model_key": "Qwen/Qwen3-235B-A22B-Instruct-2507", "model_name": "Qwen3 235B A22B Instruct", "provider": "together", "credit_multiplier": 3.2, "api_cost_per_1m_input": 1.20, "api_cost_per_1m_output": 1.20, "description": "Latest Qwen! 235B total, 22B active. 262K context.", "is_active": True, "is_default": False},
    {"model_key": "Qwen/Qwen3-235B-A22B-Thinking-2507", "model_name": "Qwen3 235B Thinking", "provider": "together", "credit_multiplier": 3.5, "api_cost_per_1m_input": 1.50, "api_cost_per_1m_output": 1.50, "description": "Thinking model. Reasoning-optimized, 262K context.", "is_active": True, "is_default": False},
    {"model_key": "Qwen/Qwen2.5-72B-Instruct-Turbo", "model_name": "Qwen 2.5 72B Turbo", "provider": "together", "credit_multiplier": 1.2, "api_cost_per_1m_input": 0.88, "api_cost_per_1m_output": 0.88, "description": "Popular Qwen model. 32K context, FP8.", "is_active": True, "is_default": False},
    {"model_key": "Qwen/Qwen2.5-7B-Instruct-Turbo", "model_name": "Qwen 2.5 7B Turbo", "provider": "together", "credit_multiplier": 0.3, "api_cost_per_1m_input": 0.30, "api_cost_per_1m_output": 0.30, "description": "Small, fast Qwen. 32K context.", "is_active": True, "is_default": False},
    
    # Mistral Models
    {"model_key": "mistralai/Magistral-Small-2506", "model_name": "Magistral Small 2506", "provider": "together", "credit_multiplier": 1.0, "api_cost_per_1m_input": 0.40, "api_cost_per_1m_output": 0.40, "description": "Latest Mistral! 40K context, BF16.", "is_active": True, "is_default": False},
    {"model_key": "mistralai/Mistral-Small-24B-Instruct-2501", "model_name": "Mistral Small 24B", "provider": "together", "credit_multiplier": 0.8, "api_cost_per_1m_input": 0.20, "api_cost_per_1m_output": 0.20, "description": "Efficient Mistral. 32K context.", "is_active": True, "is_default": False},
    
    # Google Gemma
    {"model_key": "google/gemma-3n-E4B-it", "model_name": "Gemma 3N E4B Instruct", "provider": "together", "credit_multiplier": 0.6, "api_cost_per_1m_input": 0.10, "api_cost_per_1m_output": 0.10, "description": "Google's small open model. 32K context.", "is_active": True, "is_default": False},
    
    # OpenAI OSS on Together
    {"model_key": "openai/gpt-oss-120b", "model_name": "GPT-OSS 120B (Together)", "provider": "together", "credit_multiplier": 1.5, "api_cost_per_1m_input": 0.15, "api_cost_per_1m_output": 0.60, "description": "OpenAI open-weight on Together! 128K context, Apache 2.0 license.", "is_active": True, "is_default": False},
    {"model_key": "openai/gpt-oss-20b", "model_name": "GPT-OSS 20B (Together)", "provider": "together", "credit_multiplier": 0.7, "api_cost_per_1m_input": 0.075, "api_cost_per_1m_output": 0.30, "description": "OpenAI open-weight on Together! 128K context, low latency.", "is_active": True, "is_default": False},
    
    # Moonshot Kimi
    {"model_key": "moonshotai/Kimi-K2-Instruct-0905", "model_name": "Kimi K2 Instruct 0905", "provider": "together", "credit_multiplier": 4.0, "api_cost_per_1m_input": 2.00, "api_cost_per_1m_output": 2.00, "description": "Moonshot Kimi. 262K context window!", "is_active": True, "is_default": False},
    
    # Arcee
    {"model_key": "arcee-ai/virtuoso-medium-v2", "model_name": "Arcee Virtuoso Medium", "provider": "together", "credit_multiplier": 1.2, "api_cost_per_1m_input": 0.50, "api_cost_per_1m_output": 0.50, "description": "Arcee specialized model. 128K context.", "is_active": True, "is_default": False},

    # ========== GROQ ==========
    {"model_key": "llama-3.3-70b-versatile", "model_name": "Llama 3.3 70B (Groq)", "provider": "groq", "credit_multiplier": 1.5, "api_cost_per_1m_input": 0.59, "api_cost_per_1m_output": 0.79, "description": "Ultra-fast! 280 T/sec, 10x faster than OpenAI. 131K context.", "is_active": True, "is_default": False},
    {"model_key": "llama-3.1-8b-instant", "model_name": "Llama 3.1 8B Instant (Groq)", "provider": "groq", "credit_multiplier": 0.3, "api_cost_per_1m_input": 0.05, "api_cost_per_1m_output": 0.08, "description": "Lightning fast! 560 T/sec, extremely cheap. 131K context.", "is_active": True, "is_default": False},
    {"model_key": "openai/gpt-oss-120b", "model_name": "GPT-OSS 120B (Groq)", "provider": "groq", "credit_multiplier": 1.2, "api_cost_per_1m_input": 0.15, "api_cost_per_1m_output": 0.60, "description": "OpenAI open-weight on Groq! Ultra-fast 500 T/sec, 131K context.", "is_active": True, "is_default": False},
    {"model_key": "openai/gpt-oss-20b", "model_name": "GPT-OSS 20B (Groq)", "provider": "groq", "credit_multiplier": 0.6, "api_cost_per_1m_input": 0.075, "api_cost_per_1m_output": 0.30, "description": "OpenAI open-weight on Groq! Lightning 1000 T/sec, 131K context.", "is_active": True, "is_default": False},

    # ========== OPENAI ==========
    # GPT-5 Series
    {"model_key": "gpt-5", "model_name": "GPT-5", "provider": "openai", "credit_multiplier": 10.0, "api_cost_per_1m_input": 1.25, "api_cost_per_1m_output": 10.00, "description": "Best for coding and agentic tasks. Reasoning model.", "is_active": True, "is_default": False},
    {"model_key": "gpt-5-mini", "model_name": "GPT-5 Mini", "provider": "openai", "credit_multiplier": 4.0, "api_cost_per_1m_input": 0.25, "api_cost_per_1m_output": 2.00, "description": "Faster, cheaper GPT-5. Well-defined tasks.", "is_active": True, "is_default": False},
    {"model_key": "gpt-5-nano", "model_name": "GPT-5 Nano", "provider": "openai", "credit_multiplier": 1.5, "api_cost_per_1m_input": 0.05, "api_cost_per_1m_output": 0.40, "description": "Fastest GPT-5. Summarization and classification.", "is_active": True, "is_default": False},
    {"model_key": "gpt-5-pro", "model_name": "GPT-5 Pro", "provider": "openai", "credit_multiplier": 50.0, "api_cost_per_1m_input": 15.00, "api_cost_per_1m_output": 120.00, "description": "Smartest and most precise. For critical tasks only.", "is_active": True, "is_default": False},
    
    # GPT-4.1 Series
    {"model_key": "gpt-4.1-2025-04-14", "model_name": "GPT-4.1", "provider": "openai", "credit_multiplier": 8.0, "api_cost_per_1m_input": 3.00, "api_cost_per_1m_output": 12.00, "description": "Smartest non-reasoning. Low latency, 1M context.", "is_active": True, "is_default": False},
    {"model_key": "gpt-4.1-mini-2025-04-14", "model_name": "GPT-4.1 Mini", "provider": "openai", "credit_multiplier": 3.0, "api_cost_per_1m_input": 0.80, "api_cost_per_1m_output": 3.20, "description": "Fast and cheap. Real-time chat, high throughput.", "is_active": True, "is_default": False},
    {"model_key": "gpt-4.1-nano-2025-04-14", "model_name": "GPT-4.1 Nano", "provider": "openai", "credit_multiplier": 1.0, "api_cost_per_1m_input": 0.20, "api_cost_per_1m_output": 0.80, "description": "Fastest GPT-4.1. Extremely cheap, 1M context.", "is_active": True, "is_default": False},
    
    # GPT-4o Series
    {"model_key": "gpt-4o", "model_name": "GPT-4o", "provider": "openai", "credit_multiplier": 6.0, "api_cost_per_1m_input": 2.50, "api_cost_per_1m_output": 10.00, "description": "Legacy multimodal. Still very capable.", "is_active": True, "is_default": False},
    {"model_key": "gpt-4o-mini", "model_name": "GPT-4o Mini", "provider": "openai", "credit_multiplier": 2.0, "api_cost_per_1m_input": 0.15, "api_cost_per_1m_output": 0.60, "description": "Legacy small model. Good for simple tasks.", "is_active": True, "is_default": False},
    {"model_key": "gpt-4-turbo", "model_name": "GPT-4 Turbo", "provider": "openai", "credit_multiplier": 5.0, "api_cost_per_1m_input": 10.00, "api_cost_per_1m_output": 30.00, "description": "GPT-4 Turbo. 128K context.", "is_active": True, "is_default": False},
]


def main():
    print("🚀 Pushing AI Models to Production...")
    print(f"   API: {API_URL}")
    print(f"   Total models: {len(MODELS)}")
    print("=" * 60)
    
    # Get admin token - you need to login first
    print("\n⚠️ You need to get an admin token first!")
    print("   1. Login to production as admin")
    print("   2. Copy the access_token from the response")
    print("   3. Paste it below\n")
    
    token = input("Enter admin access_token: ").strip()
    if not token:
        print("❌ No token provided!")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Use bulk endpoint
    print("\n📤 Sending bulk request...")
    
    try:
        response = requests.post(
            f"{API_URL}/credits/admin/models/bulk",
            headers=headers,
            json={"models": MODELS},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Success!")
            print(f"   Created: {result.get('created', 0)} models")
            print(f"   Skipped: {result.get('skipped', 0)} (already exist)")
            if result.get('errors'):
                print(f"   Errors: {len(result['errors'])}")
                for err in result['errors'][:5]:
                    print(f"      - {err}")
        else:
            print(f"\n❌ Failed! Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
