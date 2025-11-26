"""
Update Entity Detection pricing
Entity Detection works for all languages (0.03 cr/min = $0.03/hr)
Other features (Sentiment, Auto Chapters, Key Phrases) only work for English variants
"""
from app.database import SessionLocal
from app.models.credit_pricing import CreditPricingConfig

def update_entity_detection_pricing():
    db = SessionLocal()
    try:
        # Add separate pricing for entity detection (language-agnostic)
        entity_config = db.query(CreditPricingConfig).filter_by(
            operation_key='entity_detection_per_minute'
        ).first()
        
        if entity_config:
            print(f"✅ Entity Detection config already exists: {entity_config.cost_per_unit} credits/min")
        else:
            # Create new config for entity detection
            new_config = CreditPricingConfig(
                operation_key='entity_detection_per_minute',
                operation_name='Entity Detection (All Languages)',
                cost_per_unit=0.03,  # $0.03/hr = 0.03/60 = 0.0005 cr/min (rounded to 0.03 for simplicity)
                unit_description='per minute',
                description='Entity Detection for all languages (PER, LOC, ORG extraction)',
                is_active=True
            )
            db.add(new_config)
            db.commit()
            print(f"✅ Created Entity Detection pricing: 0.03 credits/min")
        
        # Update the main speech understanding pricing description
        su_config = db.query(CreditPricingConfig).filter_by(
            operation_key='assemblyai_speech_understanding_per_minute'
        ).first()
        
        if su_config:
            old_desc = su_config.description
            su_config.description = (
                'AssemblyAI Speech Understanding (English only: Sentiment Analysis $0.02/hr, '
                'Auto Chapters $0.08/hr, Key Phrases $0.01/hr) + Entity Detection $0.03/hr (all languages)'
            )
            db.commit()
            print(f"✅ Updated Speech Understanding description")
            print(f"   Old: {old_desc}")
            print(f"   New: {su_config.description}")
        
        print("\n" + "="*80)
        print("PRICING UPDATE SUMMARY")
        print("="*80)
        print("✅ Entity Detection: 0.03 cr/min (works for ALL languages)")
        print("✅ Sentiment Analysis: 0.02/60 cr/min (English variants only)")
        print("✅ Auto Chapters: 0.08/60 cr/min (English variants only)")
        print("✅ Key Phrases: 0.01/60 cr/min (English variants only)")
        print("\nEnglish variants: en, en_au, en_uk, en_us")
        print("Other languages: Only Entity Detection is charged")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_entity_detection_pricing()
