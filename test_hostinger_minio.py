"""
Test Hostinger MinIO Connection
"""
from minio import Minio
import sys

def test_minio():
    print("\n" + "="*60)
    print("  TESTING HOSTINGER MINIO CONNECTION")
    print("="*60 + "\n")
    
    try:
        # Connect to Hostinger MinIO
        client = Minio(
            'minio-wg8wok0k48soko0wsgk40www.gistify.pro',
            access_key='KLQh6SIhgOSvmo32',
            secret_key='R2Vf2f28ZxCsmhH5iM3GlUBEXwwB0JBX',
            secure=True
        )
        
        print("✅ Connection successful!")
        
        # List buckets
        buckets = list(client.list_buckets())
        print(f"\n📦 Existing buckets: {[b.name for b in buckets]}")
        
        # Check if mp4totext bucket exists
        bucket_exists = any(b.name == 'mp4totext' for b in buckets)
        
        if bucket_exists:
            print("✅ 'mp4totext' bucket already exists!")
        else:
            print("📦 Creating 'mp4totext' bucket...")
            client.make_bucket('mp4totext')
            print("✅ 'mp4totext' bucket created!")
        
        # Set public policy for bucket
        from minio.commonconfig import ENABLED
        from minio.versioningconfig import VersioningConfig
        
        print("\n🔓 Setting public read policy...")
        
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::mp4totext/*"]
                }
            ]
        }
        
        import json
        client.set_bucket_policy('mp4totext', json.dumps(policy))
        print("✅ Public read policy set!")
        
        print("\n" + "="*60)
        print("  ✅ HOSTINGER MINIO READY!")
        print("="*60)
        print("\n🌐 MinIO: https://minio-wg8wok0k48soko0wsgk40www.gistify.pro")
        print("🎛️ Console: https://console-wg8wok0k48soko0wsgk40www.gistify.pro")
        print("📦 Bucket: mp4totext (public read)")
        print("\n🚀 Ready to test upload from frontend!")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_minio()
    sys.exit(0 if success else 1)
