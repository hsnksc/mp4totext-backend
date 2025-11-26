"""
Direct API test without login - uses database query
"""
import os
os.chdir(r"C:\Users\hasan\OneDrive\Desktop\mp4totext\mp4totext-backend")

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionResponse
from pydantic import TypeAdapter

db = SessionLocal()
transcription = db.query(Transcription).filter(Transcription.id == 2).first()

if not transcription:
    print("❌ Transcription ID 2 not found!")
else:
    print(f"✅ Found transcription ID {transcription.id}")
    print(f"Status: {transcription.status}")
    
    # Convert to Pydantic schema (this is what API does)
    try:
        adapter = TypeAdapter(TranscriptionResponse)
        response_data = adapter.validate_python(transcription)
        response_dict = response_data.model_dump()
        
        print("\n=== PYDANTIC SCHEMA CONVERSION ===")
        print(f"Has 'enhanced_text' field: {'enhanced_text' in response_dict}")
        print(f"Has 'summary' field: {'summary' in response_dict}")
        print(f"Has 'gemini_status' field: {'gemini_status' in response_dict}")
        
        if 'enhanced_text' in response_dict:
            enhanced = response_dict['enhanced_text']
            print(f"\n✨ Enhanced Text: {enhanced[:100] if enhanced else 'NULL'}...")
        else:
            print("\n❌ 'enhanced_text' NOT in Pydantic response!")
            
        if 'summary' in response_dict:
            summary = response_dict['summary']
            print(f"\n📊 Summary: {summary[:100] if summary else 'NULL'}...")
        else:
            print("\n❌ 'summary' NOT in Pydantic response!")
            
        if 'gemini_status' in response_dict:
            print(f"\n🎯 Gemini Status: {response_dict['gemini_status']}")
        else:
            print("\n❌ 'gemini_status' NOT in Pydantic response!")
            
        print(f"\n=== ALL FIELDS IN PYDANTIC RESPONSE ===")
        import json
        print(json.dumps(list(response_dict.keys()), indent=2))
        
    except Exception as e:
        print(f"\n❌ Pydantic conversion error: {e}")
        import traceback
        traceback.print_exc()

db.close()
