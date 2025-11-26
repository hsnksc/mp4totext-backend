"""
Veritabanı tablolarını oluştur
"""
from app.database import engine, Base

def init_db():
    """Tüm tabloları oluştur"""
    print("📊 Veritabanı tabloları oluşturuluyor...")
    
    try:
        # Tüm tabloları oluştur
        Base.metadata.create_all(bind=engine)
        print("✅ Veritabanı tabloları başarıyla oluşturuldu!")
    except Exception as e:
        print(f"❌ Hata: {e}")
        raise

if __name__ == "__main__":
    init_db()
