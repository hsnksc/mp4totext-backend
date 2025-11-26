from app.database import SessionLocal
from app.models.transcription import Transcription

db = SessionLocal()
t = db.query(Transcription).filter_by(id=124).first()

print(f"ID: {t.id}")
print(f"Status: {t.status}")
print(f"Gemini Status: {t.gemini_status}")
print(f"AI Provider: {t.ai_provider}")
print(f"AI Model: {t.ai_model}")
print(f"Cleaned length: {len(t.cleaned_text) if t.cleaned_text else 0}")
print(f"Enhanced length: {len(t.enhanced_text) if t.enhanced_text else 0}")
print(f"Texts are identical: {t.enhanced_text == t.cleaned_text if t.enhanced_text and t.cleaned_text else None}")
print(f"Summary preview: {t.summary[:100] if t.summary else 'None'}")

db.close()
