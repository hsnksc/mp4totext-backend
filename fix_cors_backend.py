#!/usr/bin/env python3
"""
Backend CORS - Add all necessary headers
"""
import os

BACKEND_ROOT = r"C:\Users\hasan\OneDrive\Desktop\mp4totext-backend"

MAIN_PY = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, transcriptions
from app.database import engine
from app.models import user, transcription

# Create tables
user.Base.metadata.create_all(bind=engine)
transcription.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MP4toText API",
    description="Audio/Video Transcription Service",
    version="1.0.0"
)

# CORS - Allow all for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(transcriptions.router, prefix="/api/v1/transcriptions", tags=["transcriptions"])

@app.get("/")
async def root():
    return {"message": "MP4toText API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
"""

print("🔧 Backend CORS düzeltiliyor...\n")

main_path = os.path.join(BACKEND_ROOT, "main.py")
with open(main_path, "w", encoding="utf-8") as f:
    f.write(MAIN_PY)

print("✅ main.py güncellendi!")
print("\n📍 CORS ayarları:")
print("   • allow_origins: * (all)")
print("   • allow_methods: * (all)")
print("   • allow_headers: * (all)")
print("   • expose_headers: * (all)")
print("\n⚠️  Backend'i yeniden başlatın!")
