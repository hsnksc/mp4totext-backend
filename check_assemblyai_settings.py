"""
USE_ASSEMBLYAI ve AssemblyAI service durumunu kontrol et
"""
from app.settings import get_settings
from app.services.assemblyai_service import get_assemblyai_service

settings = get_settings()

print("🔍 AssemblyAI Ayarları:")
print("="*60)
print(f"USE_ASSEMBLYAI: {settings.USE_ASSEMBLYAI}")
print(f"ASSEMBLYAI_API_KEY: {'*' * 20 if settings.ASSEMBLYAI_API_KEY else 'NOT SET'}")
print()

# Service test
try:
    service = get_assemblyai_service()
    print(f"✅ AssemblyAI Service Enabled: {service.is_enabled()}")
except Exception as e:
    print(f"❌ AssemblyAI Service Error: {e}")
