"""
Migration: Add Vision API support columns to transcriptions table
Enables document analysis alongside audio transcription (NotebookLM-style)

New columns:
- has_audio: Boolean flag for audio/video presence
- has_document: Boolean flag for document presence
- document_file_id: MinIO file ID for document
- document_file_path: MinIO path for document
- document_filename: Original document filename
- document_content_type: MIME type of document
- document_file_size: Size in bytes
- document_text: Extracted text from document (OCR/Vision)
- document_analysis: AI analysis of document content (JSON)
- document_summary: Summary of document content
- document_key_points: Key points extracted (JSON array)
- combined_analysis: Combined analysis of audio + document (JSON)
- combined_summary: Unified summary of all sources
- processing_mode: 'audio_only', 'document_only', 'combined'
- vision_provider: 'gemini', 'openai' (which Vision API used)
- vision_model: Specific model used for vision
- vision_processing_time: Time spent on vision processing
"""

import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "mp4totext.db")

def add_vision_columns():
    """Add Vision API columns to transcriptions table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # New columns to add
    new_columns = [
        # Processing mode flags
        ("has_audio", "BOOLEAN DEFAULT 1"),  # Default true for backward compatibility
        ("has_document", "BOOLEAN DEFAULT 0"),
        ("processing_mode", "VARCHAR(50) DEFAULT 'audio_only'"),  # audio_only, document_only, combined
        
        # Document file info
        ("document_file_id", "VARCHAR(255)"),
        ("document_file_path", "VARCHAR(500)"),
        ("document_filename", "VARCHAR(255)"),
        ("document_content_type", "VARCHAR(100)"),
        ("document_file_size", "INTEGER"),
        
        # Document processing results
        ("document_text", "TEXT"),  # Extracted/OCR text
        ("document_analysis", "TEXT"),  # JSON: detailed analysis
        ("document_summary", "TEXT"),  # Summary of document
        ("document_key_points", "TEXT"),  # JSON: array of key points
        ("document_metadata", "TEXT"),  # JSON: page count, language, etc.
        
        # Combined results (audio + document)
        ("combined_analysis", "TEXT"),  # JSON: unified analysis
        ("combined_summary", "TEXT"),  # Unified summary
        ("combined_insights", "TEXT"),  # JSON: cross-referenced insights
        ("combined_key_topics", "TEXT"),  # JSON: merged topics
        ("enable_combined_analysis", "BOOLEAN DEFAULT 1"),  # Whether to combine transcription + document
        
        # Vision API settings
        ("vision_provider", "VARCHAR(50)"),  # gemini, openai
        ("vision_model", "VARCHAR(100)"),  # gemini-2.0-flash, gpt-4o, etc.
        ("vision_processing_time", "FLOAT"),  # Seconds spent on vision
        ("vision_status", "VARCHAR(50)"),  # pending, processing, completed, failed
        ("vision_error", "TEXT"),  # Error message if failed
        
        # Multi-document support (future)
        ("document_count", "INTEGER DEFAULT 0"),  # Number of documents
        ("documents_json", "TEXT"),  # JSON array of document info for multiple docs
    ]
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(transcriptions)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    added_count = 0
    skipped_count = 0
    
    for col_name, col_def in new_columns:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE transcriptions ADD COLUMN {col_name} {col_def}"
                cursor.execute(sql)
                print(f"✅ Added column: {col_name}")
                added_count += 1
            except Exception as e:
                print(f"❌ Error adding {col_name}: {e}")
        else:
            print(f"⏭️  Column already exists: {col_name}")
            skipped_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Migration complete!")
    print(f"   Added: {added_count} columns")
    print(f"   Skipped: {skipped_count} columns (already exist)")
    
    return added_count, skipped_count


def add_vision_pricing():
    """Add Vision API pricing to credit_pricing table"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if credit_pricing table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credit_pricing'")
    if not cursor.fetchone():
        print("⚠️  credit_pricing table not found, skipping pricing setup")
        conn.close()
        return
    
    # Vision pricing entries
    pricing_entries = [
        ("vision_analysis_per_page", "Document Vision Analysis (per page)", 0.5, "page", True),
        ("vision_analysis_per_image", "Image Vision Analysis (per image)", 0.3, "image", True),
        ("combined_analysis", "Combined Audio+Document Analysis", 2.0, "analysis", True),
        ("document_ocr_per_page", "Document OCR (per page)", 0.2, "page", True),
    ]
    
    for operation_key, operation_name, cost_per_unit, unit_description, is_active in pricing_entries:
        try:
            # Check if already exists
            cursor.execute("SELECT id FROM credit_pricing WHERE operation_key = ?", (operation_key,))
            if cursor.fetchone():
                print(f"⏭️  Pricing already exists: {operation_key}")
                continue
            
            cursor.execute("""
                INSERT INTO credit_pricing (operation_key, operation_name, cost_per_unit, unit_description, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (operation_key, operation_name, cost_per_unit, unit_description, is_active))
            print(f"✅ Added pricing: {operation_key} = {cost_per_unit} credits/{unit_description}")
        except Exception as e:
            print(f"❌ Error adding pricing {operation_key}: {e}")
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Vision API Support Migration")
    print("=" * 60)
    print(f"📅 Date: {datetime.now().isoformat()}")
    print(f"📁 Database: {DB_PATH}")
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        exit(1)
    
    print("📝 Adding Vision columns to transcriptions table...")
    add_vision_columns()
    
    print("\n💰 Adding Vision pricing...")
    add_vision_pricing()
    
    print("\n✅ Migration completed successfully!")
    print("🔄 Restart the backend to apply changes.")
