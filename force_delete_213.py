"""Force delete ID #213 with absolute certainty"""
from app.database import get_db, SessionLocal
from app.models.transcription import Transcription
import sys

def force_delete_213():
    """Delete ID #213 with full verification"""
    
    # Use SessionLocal directly for clean transaction
    db = SessionLocal()
    
    try:
        # Check before
        before = db.query(Transcription).filter(Transcription.id == 213).first()
        if not before:
            print("❌ ID #213 zaten silinmiş")
            return False
        
        print(f"✅ ID #213 bulundu:")
        print(f"   Filename: {before.filename}")
        print(f"   Speakers: {before.speakers}")
        print(f"   Status: {before.status}")
        
        # Delete
        print("\n🗑️ Siliniyor...")
        db.delete(before)
        db.commit()
        print("✅ DELETE ve COMMIT başarılı")
        
        # Verify after deletion
        after = db.query(Transcription).filter(Transcription.id == 213).first()
        if after is None:
            print("✅ DOĞRULANDI: ID #213 başarıyla silindi!")
            return True
        else:
            print("❌ HATA: Silme sonrası hala kayıt mevcut!")
            return False
            
    except Exception as e:
        print(f"❌ Hata: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = force_delete_213()
    sys.exit(0 if success else 1)
