"""
Simplified run script for backend API
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    
    print("🚀 Starting MP4toText Backend API...")
    print("📍 Running on: http://localhost:8002")
    print("📚 API Docs: http://localhost:8002/docs")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
