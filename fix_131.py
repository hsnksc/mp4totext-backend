"""Fix transcription #131 specifically"""
from app.database import SessionLocal
from app.models.transcription import Transcription
from app.models.credit_transaction import CreditTransaction, OperationType
from app.services.credit_service import get_credit_service

db = SessionLocal()

try:
    t = db.query(Transcription).filter_by(id=131).first()
    
    print(f"\n📊 Transcription #131: {t.filename}")
    print(f"Current duration: {t.duration}")
    
    # Calculate from segments
    if t.segments and len(t.segments) > 0:
        last_segment = t.segments[-1]
        actual_duration = int(last_segment.get('end', 0))
        
        print(f"Actual duration from segments: {actual_duration}s ({actual_duration/60:.1f} min)")
        
        # Update duration
        t.duration = actual_duration
        db.commit()
        print(f"✅ Duration updated to {actual_duration}s")
        
        # Check credit transactions
        transactions = db.query(CreditTransaction).filter_by(
            transcription_id=131,
            operation_type=OperationType.TRANSCRIPTION
        ).all()
        
        print(f"\n💳 Credit transactions:")
        for tx in transactions:
            print(f"   {tx.operation_type.value}: {tx.amount} kredi - {tx.description}")
        
        if transactions:
            original_amount = abs(transactions[0].amount)
            print(f"\n📊 Analysis:")
            print(f"   Original charge: {original_amount} kredi (assuming 1 min)")
            
            # Calculate correct amount
            credit_service = get_credit_service(db)
            correct_amount = credit_service.pricing.calculate_transcription_cost(
                duration_seconds=actual_duration,
                use_speaker_recognition=t.use_speaker_recognition,
                is_youtube=False
            )
            
            print(f"   Correct charge: {correct_amount:.2f} kredi ({actual_duration/60:.1f} min)")
            print(f"   Difference: {correct_amount - original_amount:.2f} kredi")
            print(f"\n   ⚠️ UNDERCHARGED by {correct_amount - original_amount:.2f} kredi!")
            print(f"   User should be charged additional {correct_amount - original_amount:.2f} kredi")
            
            # Ask for confirmation
            print(f"\n❓ Charge additional {correct_amount - original_amount:.2f} kredi? (yes/no)")
            response = input().strip().lower()
            
            if response == 'yes':
                credit_service.deduct_credits(
                    user_id=t.user_id,
                    amount=correct_amount - original_amount,
                    operation_type=OperationType.TRANSCRIPTION,
                    description=f"Duration correction: {t.original_filename} (retroactive charge for {actual_duration/60:.0f} min)",
                    transcription_id=t.id,
                    metadata={
                        "correction_type": "undercharge",
                        "original_duration_assumed": 60,
                        "actual_duration": actual_duration,
                        "original_charge": original_amount,
                        "additional_charge": correct_amount - original_amount
                    }
                )
                print(f"✅ Additional {correct_amount - original_amount:.2f} kredi charged")
            else:
                print("❌ Skipped charging")
    else:
        print("⚠️ No segments found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
