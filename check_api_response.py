from app.database import SessionLocal
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionResponse
import json

db = SessionLocal()
t = db.query(Transcription).filter(Transcription.id == 244).first()

# Check what the schema returns
schema = TranscriptionResponse.model_validate(t)
data = schema.model_dump()

print("=== API Response Check ===")
print(f"speech_understanding exists: {data.get('speech_understanding') is not None}")
print(f"speech_understanding type: {type(data.get('speech_understanding'))}")
print(f"llm_gateway exists: {data.get('llm_gateway') is not None}")
print(f"llm_gateway type: {type(data.get('llm_gateway'))}")

if data.get('speech_understanding'):
    print(f"\nspeech_understanding keys: {list(data['speech_understanding'].keys())}")
    print(f"speech_understanding length: {len(str(data['speech_understanding']))}")

if data.get('llm_gateway'):
    print(f"\nllm_gateway keys: {list(data['llm_gateway'].keys())}")
    print(f"llm_gateway length: {len(str(data['llm_gateway']))}")

db.close()
