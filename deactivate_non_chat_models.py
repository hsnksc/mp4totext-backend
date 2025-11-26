"""
Deactivate non-chat models (Whisper, TTS, etc.) from AI enhancement selection
These models are specialized for other tasks, not text generation
"""
from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

# Models that should NOT be used for AI enhancement (chat completions)
NON_CHAT_MODELS = [
    "whisper-large-v3-turbo",  # Speech-to-text only
    "whisper-large-v3",  # Speech-to-text only
    "playai-tts",  # Text-to-speech only
    "playai-tts-arabic",  # Text-to-speech only
]

def deactivate_non_chat_models():
    db = SessionLocal()
    try:
        print("🔧 Deactivating non-chat models...")
        print("=" * 80)
        
        total_deactivated = 0
        
        for model_key in NON_CHAT_MODELS:
            models = db.query(AIModelPricing).filter_by(model_key=model_key).all()
            
            for model in models:
                if model.is_active:
                    print(f"\n🔇 Deactivating: {model.model_key}")
                    print(f"   Provider: {model.provider}")
                    print(f"   Model name: {model.model_name}")
                    print(f"   Reason: Not a chat model (specialized for other tasks)")
                    
                    model.is_active = False
                    
                    # Update description to indicate why it's disabled
                    if not model.description or "Not for chat" not in model.description:
                        original_desc = model.description or ""
                        model.description = f"⚠️ Not for chat completions. {original_desc}".strip()
                    
                    total_deactivated += 1
                else:
                    print(f"\n⏭️  Already inactive: {model.model_key} ({model.provider})")
        
        if total_deactivated > 0:
            db.commit()
            print(f"\n" + "=" * 80)
            print(f"✅ Deactivated {total_deactivated} non-chat model(s)")
            print("=" * 80)
        else:
            print(f"\n" + "=" * 80)
            print("ℹ️  No models needed deactivation")
            print("=" * 80)
        
        # Show all inactive models
        print("\n📊 All inactive models:")
        print("-" * 80)
        inactive = db.query(AIModelPricing).filter_by(is_active=False).all()
        if inactive:
            for m in inactive:
                print(f"🔴 {m.provider:10} | {m.model_key:40} | {m.model_name}")
        else:
            print("None")
        print("-" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    deactivate_non_chat_models()
