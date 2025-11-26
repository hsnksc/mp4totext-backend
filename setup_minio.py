"""
MinIO Storage Setup Script
Bucket oluştur ve test et
"""
from minio import Minio
from minio.error import S3Error
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def setup_minio():
    """MinIO client oluştur ve bucket'ı hazırla"""
    
    # MinIO bağlantı bilgileri
    endpoint = os.getenv("STORAGE_ENDPOINT", "localhost:9000")
    access_key = os.getenv("STORAGE_ACCESS_KEY", "dev_minio")
    secret_key = os.getenv("STORAGE_SECRET_KEY", "dev_minio_123")
    bucket_name = os.getenv("STORAGE_BUCKET", "mp4totext")
    secure = os.getenv("STORAGE_SECURE", "false").lower() == "true"
    
    print(f"\n📦 MinIO Setup başlatılıyor...")
    print(f"   Endpoint: {endpoint}")
    print(f"   Bucket: {bucket_name}")
    print(f"   Secure: {secure}\n")
    
    try:
        # MinIO client oluştur
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        
        print("✅ MinIO bağlantısı başarılı!")
        
        # Bucket var mı kontrol et
        if client.bucket_exists(bucket_name):
            print(f"✅ Bucket '{bucket_name}' zaten mevcut!")
        else:
            # Bucket oluştur
            client.make_bucket(bucket_name)
            print(f"✅ Bucket '{bucket_name}' başarıyla oluşturuldu!")
        
        # Test dosyası yükle
        test_content = b"MinIO test file - MP4toText Backend"
        test_file = "test/test.txt"
        
        from io import BytesIO
        client.put_object(
            bucket_name,
            test_file,
            BytesIO(test_content),
            len(test_content),
            content_type="text/plain"
        )
        print(f"✅ Test dosyası yüklendi: {test_file}")
        
        # Test dosyasını oku
        response = client.get_object(bucket_name, test_file)
        content = response.read()
        response.close()
        response.release_conn()
        
        if content == test_content:
            print("✅ Test dosyası okuma başarılı!")
        
        # Test dosyasını sil
        client.remove_object(bucket_name, test_file)
        print("✅ Test dosyası temizlendi!")
        
        # Bucket listele
        buckets = client.list_buckets()
        print(f"\n📊 Mevcut bucket'lar:")
        for bucket in buckets:
            print(f"   • {bucket.name} (Created: {bucket.creation_date})")
        
        print("\n🎉 MinIO setup tamamlandı!")
        return True
        
    except S3Error as e:
        print(f"❌ MinIO hatası: {e}")
        return False
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

if __name__ == "__main__":
    success = setup_minio()
    exit(0 if success else 1)
