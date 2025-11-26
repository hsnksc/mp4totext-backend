import sys
sys.path.insert(0, 'C:\\Users\\hasan\\OneDrive\\Desktop\\mp4totext\\mp4totext-backend')

from app.database import SessionLocal
from app.models.transcription import Transcription
import json

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 252).first()

print(f"\n{'='*80}")
print(f"ID 252 - Speech Understanding Results")
print(f"{'='*80}\n")

print(f"sentiment_analysis: {t.sentiment_analysis}")
print(f"\nauto_chapters: ", end="")
if t.auto_chapters:
    print(json.dumps(t.auto_chapters, indent=2))
else:
    print("None")

print(f"\nentities count: {len(t.entities) if t.entities else 0}")
print(f"highlights count: {len(t.highlights) if t.highlights else 0}")

db.close()
