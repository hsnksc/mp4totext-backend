from app.database import SessionLocal
from app.models.transcription import Transcription
import time

db = SessionLocal()

print("\n🔍 Monitoring Transcription #149...")
print("=" * 60)

for i in range(6):  # 30 seconds total (6 x 5 sec)
    t = db.query(Transcription).filter(Transcription.id == 149).first()
    
    if t:
        text_len = len(t.text or '')
        enhanced_len = len(t.enhanced_text or '')
        
        print(f"\n[{i*5}s] Status: {t.status.value}")
        print(f"      Text: {text_len} chars")
        print(f"      Enhanced: {enhanced_len} chars")
        
        if t.status.value == 'completed':
            print("\n✅ COMPLETED!")
            break
        elif t.status.value == 'failed':
            print(f"\n❌ FAILED: {t.error_message}")
            break
    
    if i < 5:
        time.sleep(5)

db.close()
