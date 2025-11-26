"""Manual credit fix for transcription 250 - LLM Gateway"""
from app.database import SessionLocal
from app.services.credit_service import CreditService
from app.models.transcription import Transcription

def fix_id_250():
    db = SessionLocal()
    
    try:
        # Deduct 3.0 credits for LLM Gateway
        credit_service = CreditService(db)
        
        # Find transcription
        transcription = db.query(Transcription).filter(Transcription.id == 250).first()
        if not transcription:
            print("❌ Transcription 250 not found")
            return
        
        # Deduct credits
        credit_service.deduct_credits(
            user_id=transcription.user_id,
            amount=3.0,
            operation_type="transcription",
            description="AssemblyAI LLM Gateway: Manual fix for ID 250",
            transcription_id=250,
            metadata={
                "feature": "llm_gateway",
                "fixed_cost": 3.0,
                "manual_fix": True
            }
        )
        
        db.commit()
        print("✅ 3.0 credits successfully deducted for LLM Gateway (ID 250)")
        
        # Show updated balance
        from app.models.user import User
        user = db.query(User).filter(User.id == transcription.user_id).first()
        print(f"💰 New balance: {user.credits:.2f} credits")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_id_250()
