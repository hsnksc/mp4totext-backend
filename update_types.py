"""
Update TypeScript types for new features
"""

from pathlib import Path

FRONTEND_PATH = Path(r"C:\Users\hasan\OneDrive\Desktop\mp4totext-web")
TYPES_FILE = FRONTEND_PATH / "src" / "types" / "transcription.ts"

NEW_TYPES = '''export interface Transcription {
  id: number;
  user_id: number;
  file_id: string;
  filename: string;
  file_size: number;
  file_path: string;
  content_type: string;
  
  // Transcription settings
  language: string | null;
  whisper_model: string;  // NEW: Model used (tiny, base, small, medium, large, turbo)
  use_speaker_recognition: boolean;
  use_gemini_enhancement: boolean;
  
  // Status and progress
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  progress_message: string | null;
  
  // Results
  text: string | null;
  enhanced_text: string | null;  // NEW: AI-enhanced text from Gemini
  summary: string | null;  // NEW: AI-generated summary from Gemini
  
  // Timing
  duration: number | null;
  processing_time: number | null;
  
  // Speaker recognition
  speaker_count: number | null;
  speakers: string[] | null;
  segments: TranscriptionSegment[] | null;
  
  // Gemini AI metadata
  gemini_status: string | null;  // NEW: 'pending', 'completed', 'failed', 'skipped'
  gemini_improvements: GeminiImprovement[] | null;  // NEW: List of improvements
  gemini_metadata: Record<string, any> | null;  // NEW: Additional metadata
  
  // Timestamps
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  
  // Error handling
  error_message: string | null;
}

export interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
  speaker: string;
}

export interface GeminiImprovement {
  type: string;  // e.g., 'punctuation', 'spelling', 'formatting'
  description: string;
  count?: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percent: number;
}

export interface PaginatedTranscriptions {
  items: Transcription[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}
'''

def main():
    print("\n🚀 Updating TypeScript Types...")
    print("=" * 50)
    
    try:
        # Create types directory if not exists
        TYPES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"📝 Writing to {TYPES_FILE}...")
        TYPES_FILE.write_text(NEW_TYPES, encoding='utf-8')
        print("✅ transcription.ts updated successfully!")
        print("\n📋 New types:")
        print("   • whisper_model: string")
        print("   • enhanced_text: string | null")
        print("   • summary: string | null")
        print("   • gemini_status: string | null")
        print("   • gemini_improvements: GeminiImprovement[]")
        print("   • gemini_metadata: Record<string, any>")
        print("=" * 50 + "\n")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    main()
