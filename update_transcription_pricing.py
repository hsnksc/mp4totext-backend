"""
Transkripsiyon Fiyatlandırma Güncellemesi
==========================================
Yeni dakika başı fiyatlandırma:
- Transcription: 10 kredi/dk → 1 kredi/dk  
- Speaker Recognition: 5 kredi/dk → 1 kredi per 2 dk (0.5 kredi/dk efektif)

Not: SQLite INTEGER kullandığı için 0.5 değeri tutamıyoruz.
Çözüm: cost_per_unit=1 ile "per 2 dakika" tanımı → kod hesaplamada 0.5x kullanacak
"""

from app.database import SessionLocal
from app.models.credit_pricing import CreditPricingConfig

def update_transcription_pricing():
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("🔄 UPDATING TRANSCRIPTION PRICING")
        print("="*80 + "\n")
        
        # Update transcription base cost
        transcription = db.query(CreditPricingConfig).filter_by(
            operation_key="transcription_base"
        ).first()
        
        if transcription:
            old_cost = transcription.cost_per_unit
            transcription.cost_per_unit = 1  # 10 → 1 kredi/dk
            
            print(f"✅ UPDATED: Transcription Base")
            print(f"   OLD: {old_cost} kredi/dakika")
            print(f"   NEW: 1 kredi/dakika")
            print(f"   Example: 5 dakikalık dosya = {old_cost * 5} kredi → 5 kredi (10x cheaper)")
            print()
        else:
            print("⚠️  Transcription base config not found!")
            print()
        
        # Update speaker recognition cost
        # IMPORTANT: SQLite doesn't support decimals, so we use a workaround:
        # - Database: cost_per_unit=1, unit_description="per 2 dakika"
        # - Code will calculate: minutes * (cost_per_unit / 2) = minutes * 0.5
        speaker = db.query(CreditPricingConfig).filter_by(
            operation_key="speaker_recognition"
        ).first()
        
        if speaker:
            old_cost = speaker.cost_per_unit
            speaker.cost_per_unit = 1  # Will represent "1 credit per 2 minutes" 
            speaker.unit_description = "per 2 dakika"  # KEY: This signals 0.5x calculation
            speaker.description = "Farklı konuşmacıları ayırt etme (ek maliyet - dakikada 0.5 kredi)"
            
            print(f"✅ UPDATED: Speaker Recognition")
            print(f"   OLD: {old_cost} kredi/dakika")
            print(f"   NEW: 1 kredi per 2 dakika (efektif: 0.5 kredi/dakika)")
            print(f"   Example: 5 dakikalık dosya = {old_cost * 5} kredi → 2.5 kredi (10x cheaper)")
            print()
        else:
            print("⚠️  Speaker recognition config not found!")
            print()
        
        db.commit()
        
        print("="*80)
        print("✅ DATABASE UPDATE COMPLETE")
        print("="*80 + "\n")
        
        # Show all pricing
        print("\n📊 NEW PRICING STRUCTURE:")
        print("-" * 80)
        
        all_configs = db.query(CreditPricingConfig).filter_by(is_active=True).all()
        
        print(f"\n{'Operation':<30} | {'Cost':<25} | {'Unit':<20}")
        print("-" * 80)
        for c in all_configs:
            if c.operation_key == "transcription_base":
                cost_display = "1 kredi/dakika"
            elif c.operation_key == "speaker_recognition":
                cost_display = "0.5 kredi/dakika (1/2dk)"
            else:
                cost_display = f"{c.cost_per_unit} {c.unit_description}"
            
            print(f"{c.operation_name:<30} | {cost_display:<25} | {c.unit_description:<20}")
        
        print("\n" + "="*80)
        print("💰 COST EXAMPLES:")
        print("-" * 80)
        
        print("\n1️⃣  1 dakikalık dosya (sadece transkripsiyon):")
        print(f"   NEW: 1 kredi")
        print(f"   OLD: 10 kredi")
        print(f"   💵 Savings: 9 kredi (90% cheaper)")
        
        print("\n2️⃣  5 dakikalık dosya (transkripsiyon + speaker recognition):")
        print(f"   Transcription: 5 × 1 = 5 kredi")
        print(f"   Speaker Recog: 5 × 0.5 = 2.5 kredi")
        print(f"   NEW TOTAL: 7.5 kredi")
        print(f"   OLD TOTAL: (5×10) + (5×5) = 75 kredi")
        print(f"   💵 Savings: 67.5 kredi (90% cheaper)")
        
        print("\n3️⃣  10 dakikalık dosya + AI enhancement (gemini-2.5-flash):")
        print(f"   Transcription: 10 × 1 = 10 kredi")
        print(f"   AI Enhancement: 20 kredi (sabit)")
        print(f"   NEW TOTAL: 30 kredi")
        print(f"   OLD TOTAL: (10×10) + 20 = 120 kredi")
        print(f"   💵 Savings: 90 kredi (75% cheaper)")
        
        print("\n4️⃣  20 dakikalık dosya + speaker + lecture notes (gpt-4o-mini 1.5x):")
        print(f"   Transcription: 20 × 1 = 20 kredi")
        print(f"   Speaker Recog: 20 × 0.5 = 10 kredi")
        print(f"   Lecture Notes: 30 × 1.5 = 45 kredi")
        print(f"   NEW TOTAL: 75 kredi")
        print(f"   OLD TOTAL: (20×10) + (20×5) + 45 = 345 kredi")
        print(f"   💵 Savings: 270 kredi (78% cheaper)")
        
        print("\n" + "="*80)
        print("⚠️  NEXT STEPS:")
        print("="*80)
        print("1. Update credit_service.py to handle 'per 2 dakika' unit")
        print("2. Test transcription cost calculation")
        print("3. Restart backend: .\debug_backend_clean.ps1")
        print("4. Restart Celery: .\start_celery.bat")
        print("5. Upload test file and verify cost deduction")
        print("="*80 + "\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_transcription_pricing()
