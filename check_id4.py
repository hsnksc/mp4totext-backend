import os
os.chdir(r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend")

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.transcription import Transcription

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 6).first()

if not t:
    print("❌ Transcription ID 4 not found!")
else:
    print(f"✅ Found transcription ID {t.id}")
    print(f"Status: {t.status}")
    print(f"use_gemini_enhancement: {t.use_gemini_enhancement}")
    print(f"gemini_status: {t.gemini_status}")
    print(f"\nOriginal Text (first 100): {t.text[:100] if t.text else 'NULL'}")
    print(f"\nEnhanced Text (first 100): {t.enhanced_text[:100] if t.enhanced_text else 'NULL'}")
    print(f"\nSummary (first 100): {t.summary[:100] if t.summary else 'NULL'}")

db.close()
