from app.database import SessionLocal
from app.models.generated_image import GeneratedImage

db = SessionLocal()
images = db.query(GeneratedImage).filter(
    GeneratedImage.transcription_id == 258
).order_by(GeneratedImage.created_at).all()

print(f"\n📊 Toplam: {len(images)} görsel\n")
print("=" * 80)

for img in images:
    print(f"ID={img.id:2d} | Style={img.style:12s} | Active={img.is_active} | Created={img.created_at}")

print("=" * 80)

# Active olanları say
active_count = sum(1 for img in images if img.is_active)
print(f"\n✅ Aktif: {active_count} / {len(images)}")

db.close()
