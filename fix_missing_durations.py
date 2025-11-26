"""
Fix missing durations for existing transcriptions
Recalculates duration from segments and refunds/charges the difference
"""
from app.database import SessionLocal
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.credit_transaction import CreditTransaction, OperationType
from app.services.credit_service import get_credit_service
import json

db = SessionLocal()

try:
    # Find all completed transcriptions with missing duration
    transcriptions = db.query(Transcription).filter(
        Transcription.status == TranscriptionStatus.COMPLETED,
        Transcription.duration.is_(None)
    ).all()
    
    print(f"\n🔍 Found {len(transcriptions)} transcriptions with missing duration\n")
    
    for t in transcriptions:
        print(f"📊 Transcription #{t.id}: {t.filename}")
        
        # Calculate duration from segments
        if t.segments and isinstance(t.segments, list) and len(t.segments) > 0:
            last_segment = t.segments[-1]
            actual_duration = int(last_segment.get('end', 0))
            
            print(f"   Calculated duration: {actual_duration}s ({actual_duration/60:.1f} min)")
            
            # Get the original credit transaction
            original_transaction = db.query(CreditTransaction).filter(
                CreditTransaction.transcription_id == t.id,
                CreditTransaction.operation_type == OperationType.TRANSCRIPTION
            ).first()
            
            if original_transaction:
                # Original amount (negative value)
                original_amount = abs(original_transaction.amount)
                print(f"   Original charge: {original_amount} kredi")
                
                # Calculate correct amount
                credit_service = get_credit_service(db)
                correct_amount = credit_service.pricing.calculate_transcription_cost(
                    duration_seconds=actual_duration,
                    use_speaker_recognition=t.use_speaker_recognition,
                    is_youtube=False
                )
                
                print(f"   Correct charge: {correct_amount} kredi")
                
                difference = correct_amount - original_amount
                
                if abs(difference) > 0.01:  # More than 1 cent difference
                    if difference > 0:
                        # Need to charge more
                        print(f"   ⚠️ UNDERCHARGED by {difference:.2f} kredi")
                        
                        # Deduct additional credits
                        credit_service.deduct_credits(
                            user_id=t.user_id,
                            amount=difference,
                            operation_type=OperationType.TRANSCRIPTION,
                            description=f"Duration correction: {t.original_filename} (retroactive charge)",
                            transcription_id=t.id,
                            metadata={
                                "correction_type": "undercharge",
                                "original_duration": 60,
                                "actual_duration": actual_duration,
                                "original_amount": original_amount,
                                "additional_amount": difference
                            }
                        )
                        print(f"   ✅ Additional {difference:.2f} kredi charged")
                    else:
                        # Need to refund
                        refund = abs(difference)
                        print(f"   💰 OVERCHARGED by {refund:.2f} kredi - REFUNDING")
                        
                        # Refund credits
                        credit_service.add_credits(
                            user_id=t.user_id,
                            amount=refund,
                            operation_type=OperationType.REFUND,
                            description=f"Duration correction refund: {t.original_filename}",
                            metadata={
                                "transcription_id": t.id,
                                "correction_type": "overcharge",
                                "original_duration": 60,
                                "actual_duration": actual_duration,
                                "original_amount": original_amount,
                                "refund_amount": refund
                            }
                        )
                        print(f"   ✅ {refund:.2f} kredi refunded")
                else:
                    print(f"   ✅ Amount correct (difference: {difference:.2f})")
            
            # Update duration in database
            t.duration = actual_duration
            db.commit()
            print(f"   ✅ Duration updated in database\n")
        else:
            print(f"   ⚠️ No segments found, cannot calculate duration\n")
    
    print(f"\n✅ Fixed {len(transcriptions)} transcriptions")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    db.rollback()
    raise
finally:
    db.close()
