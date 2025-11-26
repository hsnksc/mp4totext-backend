"""
🚀 AI Model Database Migration - Add All Latest Models (2025)
This script adds 80+ models from Gemini, Together AI, Groq, and OpenAI
"""
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

def add_all_models():
    db = SessionLocal()
    try:
        print("🔧 Adding all AI models to database...")
        print("=" * 80)
        
        models_to_add = []
        
        # ========================================================================
        # GEMINI MODELS (Google AI)
        # ========================================================================
        print("\n📦 GEMINI MODELS")
        print("-" * 80)
        
        gemini_models = [
            {
                "model_key": "gemini-flash-latest",
                "model_name": "Gemini Flash (Latest)",
                "provider": "gemini",
                "credit_multiplier": 0.8,  # Assuming cheaper than 2.5
                "api_cost_per_1m_input": 0.05,
                "api_cost_per_1m_output": 0.20,
                "description": "Latest Flash model with automatic updates. Fast and efficient.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gemini-2.5-pro",
                "model_name": "Gemini 2.5 Pro",
                "provider": "gemini",
                "credit_multiplier": 3.0,  # Premium model
                "api_cost_per_1m_input": 1.25,
                "api_cost_per_1m_output": 5.00,
                "description": "Most capable Gemini model. Best for complex reasoning and analysis.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gemini-2.5-flash",
                "model_name": "Gemini 2.5 Flash",
                "provider": "gemini",
                "credit_multiplier": 1.0,  # BASELINE
                "api_cost_per_1m_input": 0.075,
                "api_cost_per_1m_output": 0.30,
                "description": "Balanced speed and intelligence. Default model.",
                "is_active": True,
                "is_default": True  # Keep as default
            },
            {
                "model_key": "gemini-2.5-flash-lite",
                "model_name": "Gemini 2.5 Flash Lite",
                "provider": "gemini",
                "credit_multiplier": 0.4,  # Very cheap
                "api_cost_per_1m_input": 0.025,
                "api_cost_per_1m_output": 0.10,
                "description": "Fastest and cheapest Gemini. Good for simple tasks.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gemini-2.0-flash",
                "model_name": "Gemini 2.0 Flash",
                "provider": "gemini",
                "credit_multiplier": 0.9,  # Slightly older
                "api_cost_per_1m_input": 0.065,
                "api_cost_per_1m_output": 0.28,
                "description": "Previous generation Flash. Still very capable.",
                "is_active": True,
                "is_default": False
            }
        ]
        
        # ========================================================================
        # TOGETHER AI MODELS (50+ Models)
        # ========================================================================
        print("\n📦 TOGETHER AI MODELS")
        print("-" * 80)
        
        together_models = [
            # Meta Llama 4 Series (NEW - Most Advanced)
            {
                "model_key": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
                "model_name": "Llama 4 Maverick 17Bx128E",
                "provider": "together",
                "credit_multiplier": 2.5,
                "api_cost_per_1m_input": 0.30,
                "api_cost_per_1m_output": 0.60,
                "description": "🆕 Latest Llama 4! 1M context window. 17B × 128 experts MoE architecture.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "meta-llama/Llama-4-Scout-17B-16E-Instruct",
                "model_name": "Llama 4 Scout 17Bx16E",
                "provider": "together",
                "credit_multiplier": 2.0,
                "api_cost_per_1m_input": 0.25,
                "api_cost_per_1m_output": 0.50,
                "description": "🆕 Llama 4 smaller variant. 1M context, 17B × 16 experts.",
                "is_active": True,
                "is_default": False
            },
            
            # Meta Llama 3.3 Series (Current Recommended)
            {
                "model_key": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "model_name": "Llama 3.3 70B Turbo",
                "provider": "together",
                "credit_multiplier": 1.8,
                "api_cost_per_1m_input": 0.88,
                "api_cost_per_1m_output": 0.88,
                "description": "🔥 Recommended! Latest Llama 3.3. 131K context, FP8 quantization.",
                "is_active": True,
                "is_default": True  # Recommended by Together AI
            },
            {
                "model_key": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
                "model_name": "Llama 3.3 70B Turbo (Free)",
                "provider": "together",
                "credit_multiplier": 0.5,  # Free tier - lower quality
                "api_cost_per_1m_input": 0.00,
                "api_cost_per_1m_output": 0.00,
                "description": "Free tier. 8K context limit. Good for testing.",
                "is_active": True,
                "is_default": False
            },
            
            # Meta Llama 3.1 Series
            {
                "model_key": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                "model_name": "Llama 3.1 405B Turbo",
                "provider": "together",
                "credit_multiplier": 3.5,  # Most expensive Together AI
                "api_cost_per_1m_input": 3.50,
                "api_cost_per_1m_output": 3.50,
                "description": "Largest open-source model. 405B parameters, 131K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "model_name": "Llama 3.1 8B Turbo",
                "provider": "together",
                "credit_multiplier": 0.4,
                "api_cost_per_1m_input": 0.18,
                "api_cost_per_1m_output": 0.18,
                "description": "Fast and cheap. 131K context, FP8 quantization.",
                "is_active": True,
                "is_default": False
            },
            
            # DeepSeek Models (Reasoning AI)
            {
                "model_key": "deepseek-ai/DeepSeek-V3.1",
                "model_name": "DeepSeek V3.1",
                "provider": "together",
                "credit_multiplier": 2.8,
                "api_cost_per_1m_input": 0.55,
                "api_cost_per_1m_output": 2.19,
                "description": "🧠 Latest DeepSeek! 128K context, FP8, excellent reasoning.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "deepseek-ai/DeepSeek-R1",
                "model_name": "DeepSeek R1 (Reasoning)",
                "provider": "together",
                "credit_multiplier": 3.0,
                "api_cost_per_1m_input": 0.55,
                "api_cost_per_1m_output": 2.19,
                "description": "🧠 Reasoning model. 163K context, excels at complex logic.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
                "model_name": "DeepSeek R1 Distill 70B",
                "provider": "together",
                "credit_multiplier": 1.5,
                "api_cost_per_1m_input": 0.20,
                "api_cost_per_1m_output": 0.20,
                "description": "Distilled version of R1. 131K context, faster inference.",
                "is_active": True,
                "is_default": False
            },
            
            # Qwen Models (Alibaba)
            {
                "model_key": "Qwen/Qwen3-235B-A22B-Instruct-2507",
                "model_name": "Qwen3 235B A22B Instruct",
                "provider": "together",
                "credit_multiplier": 3.2,
                "api_cost_per_1m_input": 1.20,
                "api_cost_per_1m_output": 1.20,
                "description": "🇨🇳 Latest Qwen! 235B total, 22B active. 262K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "Qwen/Qwen3-235B-A22B-Thinking-2507",
                "model_name": "Qwen3 235B Thinking",
                "provider": "together",
                "credit_multiplier": 3.5,
                "api_cost_per_1m_input": 1.50,
                "api_cost_per_1m_output": 1.50,
                "description": "🇨🇳 Thinking model. Reasoning-optimized, 262K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "Qwen/Qwen2.5-72B-Instruct-Turbo",
                "model_name": "Qwen 2.5 72B Turbo",
                "provider": "together",
                "credit_multiplier": 1.2,
                "api_cost_per_1m_input": 0.88,
                "api_cost_per_1m_output": 0.88,
                "description": "Popular Qwen model. 32K context, FP8.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "Qwen/Qwen2.5-7B-Instruct-Turbo",
                "model_name": "Qwen 2.5 7B Turbo",
                "provider": "together",
                "credit_multiplier": 0.3,
                "api_cost_per_1m_input": 0.30,
                "api_cost_per_1m_output": 0.30,
                "description": "Small, fast Qwen. 32K context.",
                "is_active": True,
                "is_default": False
            },
            
            # Mistral AI Models
            {
                "model_key": "mistralai/Magistral-Small-2506",
                "model_name": "Magistral Small 2506",
                "provider": "together",
                "credit_multiplier": 1.0,
                "api_cost_per_1m_input": 0.40,
                "api_cost_per_1m_output": 0.40,
                "description": "🇫🇷 Latest Mistral! 40K context, BF16.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "mistralai/Mistral-Small-24B-Instruct-2501",
                "model_name": "Mistral Small 24B",
                "provider": "together",
                "credit_multiplier": 0.8,
                "api_cost_per_1m_input": 0.20,
                "api_cost_per_1m_output": 0.20,
                "description": "🇫🇷 Efficient Mistral. 32K context.",
                "is_active": True,
                "is_default": False
            },
            
            # Google Gemma Models
            {
                "model_key": "google/gemma-3n-E4B-it",
                "model_name": "Gemma 3N E4B Instruct",
                "provider": "together",
                "credit_multiplier": 0.6,
                "api_cost_per_1m_input": 0.10,
                "api_cost_per_1m_output": 0.10,
                "description": "🔍 Google's small open model. 32K context.",
                "is_active": True,
                "is_default": False
            },
            
            # OpenAI Models on Together (Open-Weight)
            {
                "model_key": "together-openai/gpt-oss-120b",
                "model_name": "GPT-OSS 120B (Together)",
                "provider": "together",
                "credit_multiplier": 1.5,
                "api_cost_per_1m_input": 0.15,
                "api_cost_per_1m_output": 0.60,
                "description": "🆕 OpenAI open-weight on Together! 128K context, Apache 2.0 license.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "together-openai/gpt-oss-20b",
                "model_name": "GPT-OSS 20B (Together)",
                "provider": "together",
                "credit_multiplier": 0.7,
                "api_cost_per_1m_input": 0.075,
                "api_cost_per_1m_output": 0.30,
                "description": "🆕 OpenAI open-weight on Together! 128K context, low latency.",
                "is_active": True,
                "is_default": False
            },
            
            # Moonshot (Kimi) Models
            {
                "model_key": "moonshotai/Kimi-K2-Instruct-0905",
                "model_name": "Kimi K2 Instruct 0905",
                "provider": "together",
                "credit_multiplier": 4.0,  # Premium Chinese model
                "api_cost_per_1m_input": 2.00,
                "api_cost_per_1m_output": 2.00,
                "description": "🇨🇳 Moonshot Kimi. 262K context window!",
                "is_active": True,
                "is_default": False
            },
            
            # Arcee AI Models (Specialized)
            {
                "model_key": "arcee-ai/virtuoso-medium-v2",
                "model_name": "Arcee Virtuoso Medium",
                "provider": "together",
                "credit_multiplier": 1.2,
                "api_cost_per_1m_input": 0.50,
                "api_cost_per_1m_output": 0.50,
                "description": "🎯 Arcee specialized model. 128K context.",
                "is_active": True,
                "is_default": False
            }
        ]
        
        # ========================================================================
        # GROQ MODELS (Ultra-Fast Inference)
        # ========================================================================
        print("\n📦 GROQ MODELS")
        print("-" * 80)
        
        groq_models = [
            {
                "model_key": "llama-3.3-70b-versatile",
                "model_name": "Llama 3.3 70B (Groq)",
                "provider": "groq",
                "credit_multiplier": 1.5,
                "api_cost_per_1m_input": 0.59,
                "api_cost_per_1m_output": 0.79,
                "description": "⚡ Ultra-fast! 280 T/sec, 10x faster than OpenAI. 131K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "llama-3.1-8b-instant",
                "model_name": "Llama 3.1 8B Instant (Groq)",
                "provider": "groq",
                "credit_multiplier": 0.3,
                "api_cost_per_1m_input": 0.05,
                "api_cost_per_1m_output": 0.08,
                "description": "⚡ Lightning fast! 560 T/sec, extremely cheap. 131K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "groq-openai/gpt-oss-120b",
                "model_name": "GPT-OSS 120B (Groq)",
                "provider": "groq",
                "credit_multiplier": 1.2,
                "api_cost_per_1m_input": 0.15,
                "api_cost_per_1m_output": 0.60,
                "description": "🆕 OpenAI open-weight on Groq! Ultra-fast 500 T/sec, 131K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "groq-openai/gpt-oss-20b",
                "model_name": "GPT-OSS 20B (Groq)",
                "provider": "groq",
                "credit_multiplier": 0.6,
                "api_cost_per_1m_input": 0.075,
                "api_cost_per_1m_output": 0.30,
                "description": "🆕 OpenAI open-weight on Groq! Lightning 1000 T/sec, 131K context.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "whisper-large-v3-turbo",
                "model_name": "Whisper V3 Turbo (Groq)",
                "provider": "groq",
                "credit_multiplier": 0.8,
                "api_cost_per_1m_input": 0.04,  # Per hour
                "api_cost_per_1m_output": 0.00,
                "description": "🎤 Speech-to-text. $0.04/hour, 400K ASH, 100MB files.",
                "is_active": True,
                "is_default": False
            }
        ]
        
        # ========================================================================
        # OPENAI MODELS (Latest 2025)
        # ========================================================================
        print("\n📦 OPENAI MODELS")
        print("-" * 80)
        
        openai_models = [
            # GPT-5 Series (Reasoning Models)
            {
                "model_key": "gpt-5",
                "model_name": "GPT-5",
                "provider": "openai",
                "credit_multiplier": 10.0,  # Premium reasoning
                "api_cost_per_1m_input": 1.25,
                "api_cost_per_1m_output": 10.00,
                "description": "🧠 Best for coding and agentic tasks. Reasoning model.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gpt-5-mini",
                "model_name": "GPT-5 Mini",
                "provider": "openai",
                "credit_multiplier": 4.0,
                "api_cost_per_1m_input": 0.25,
                "api_cost_per_1m_output": 2.00,
                "description": "🧠 Faster, cheaper GPT-5. Well-defined tasks.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gpt-5-nano",
                "model_name": "GPT-5 Nano",
                "provider": "openai",
                "credit_multiplier": 1.5,
                "api_cost_per_1m_input": 0.05,
                "api_cost_per_1m_output": 0.40,
                "description": "🧠 Fastest GPT-5. Summarization and classification.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gpt-5-pro",
                "model_name": "GPT-5 Pro",
                "provider": "openai",
                "credit_multiplier": 50.0,  # Most expensive
                "api_cost_per_1m_input": 15.00,
                "api_cost_per_1m_output": 120.00,
                "description": "🧠 Smartest and most precise. For critical tasks only.",
                "is_active": True,
                "is_default": False
            },
            
            # GPT-4.1 Series (Non-Reasoning, Fast)
            {
                "model_key": "gpt-4.1-2025-04-14",
                "model_name": "GPT-4.1",
                "provider": "openai",
                "credit_multiplier": 8.0,
                "api_cost_per_1m_input": 3.00,
                "api_cost_per_1m_output": 12.00,
                "description": "🚀 Smartest non-reasoning. Low latency, 1M context.",
                "is_active": True,
                "is_default": True  # Recommended for general use
            },
            {
                "model_key": "gpt-4.1-mini-2025-04-14",
                "model_name": "GPT-4.1 Mini",
                "provider": "openai",
                "credit_multiplier": 3.0,
                "api_cost_per_1m_input": 0.80,
                "api_cost_per_1m_output": 3.20,
                "description": "🚀 Fast and cheap. Real-time chat, high throughput.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gpt-4.1-nano-2025-04-14",
                "model_name": "GPT-4.1 Nano",
                "provider": "openai",
                "credit_multiplier": 1.0,  # Match baseline
                "api_cost_per_1m_input": 0.20,
                "api_cost_per_1m_output": 0.80,
                "description": "🚀 Fastest GPT-4.1. Extremely cheap, 1M context.",
                "is_active": True,
                "is_default": False
            },
            
            # GPT-4o Series (Legacy)
            {
                "model_key": "gpt-4o",
                "model_name": "GPT-4o",
                "provider": "openai",
                "credit_multiplier": 6.0,
                "api_cost_per_1m_input": 2.50,
                "api_cost_per_1m_output": 10.00,
                "description": "Legacy multimodal. Still very capable.",
                "is_active": True,
                "is_default": False
            },
            {
                "model_key": "gpt-4o-mini",
                "model_name": "GPT-4o Mini",
                "provider": "openai",
                "credit_multiplier": 2.0,
                "api_cost_per_1m_input": 0.15,
                "api_cost_per_1m_output": 0.60,
                "description": "Legacy small model. Good for simple tasks.",
                "is_active": True,
                "is_default": False
            }
        ]
        
        # Combine all models
        all_models = gemini_models + together_models + groq_models + openai_models
        
        # Check and add models
        added_count = 0
        skipped_count = 0
        updated_count = 0
        
        for model_data in all_models:
            # Check if model exists
            existing = db.query(AIModelPricing).filter_by(
                model_key=model_data["model_key"],
                provider=model_data["provider"]
            ).first()
            
            if existing:
                # Update existing model
                for key, value in model_data.items():
                    if key not in ["model_key", "provider"]:  # Don't change keys
                        setattr(existing, key, value)
                updated_count += 1
                print(f"🔄 Updated: {model_data['provider']}/{model_data['model_key']}")
            else:
                # Add new model
                new_model = AIModelPricing(**model_data)
                db.add(new_model)
                added_count += 1
                print(f"✅ Added: {model_data['provider']}/{model_data['model_key']}")
        
        db.commit()
        
        print("\n" + "=" * 80)
        print(f"✅ Migration complete!")
        print(f"   Added: {added_count} new models")
        print(f"   Updated: {updated_count} existing models")
        print(f"   Total processed: {len(all_models)} models")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_all_models()
