from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.transcription import Transcription

db = SessionLocal()
t = db.query(Transcription).order_by(Transcription.id.desc()).first()

print("=" * 80)
print(f"ID: {t.id}")
print(f"Filename: {t.filename}")
print(f"Status: {t.status}")
print(f"AI Provider: {t.ai_provider}")
print(f"AI Model: {t.ai_model}")
print(f"Gemini Status: {t.gemini_status}")
print("=" * 80)
print("\n📝 ORIGINAL TEXT (first 300 chars):")
print("-" * 80)
print(t.text[:300] if t.text else "NONE")
print("\n✨ ENHANCED TEXT (first 300 chars):")
print("-" * 80)
print(t.enhanced_text[:300] if t.enhanced_text else "NONE")
print("\n📊 SUMMARY:")
print("-" * 80)
print(t.summary if t.summary else "NONE")
print("=" * 80)

db.close()
