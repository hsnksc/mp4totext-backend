from app.database import SessionLocal
from app.models.ai_model_pricing import AIModelPricing

db = SessionLocal()

try:
    models = db.query(AIModelPricing).filter(AIModelPricing.is_active == True).all()
    
    print('\n' + '='*80)
    print('ACTIVE AI MODELS IN DATABASE')
    print('='*80)
    print(f"{'Provider':<15} | {'Model Key':<35} | Model Name")
    print('-'*80)
    
    for m in models:
        print(f"{m.provider:<15} | {m.model_key:<35} | {m.model_name}")
    
    print('='*80)
    print(f'Total active models: {len(models)}')
    
finally:
    db.close()
