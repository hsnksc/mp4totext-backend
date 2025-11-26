"""
Add web_context_enrichment column to transcriptions table

This field stores AI-synthesized web search context that:
1. Uses AI-generated optimized search queries (not just keywords)
2. Synthesizes Tavily results with transcript context
3. Includes proper references and citations
4. Explains how web info relates to transcript

Run: python add_web_context_enrichment_column.py
"""

from sqlalchemy import create_engine, Column, Text, MetaData, Table
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mp4totext.db")

print(f"🔧 Connecting to database: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Reflect existing table
transcriptions = Table('transcriptions', metadata, autoload_with=engine)

print("📊 Current columns:")
for col in transcriptions.columns:
    print(f"  - {col.name}: {col.type}")

# Check if column already exists
if 'web_context_enrichment' in [col.name for col in transcriptions.columns]:
    print("✅ Column 'web_context_enrichment' already exists - no migration needed")
else:
    print("\n🔨 Adding 'web_context_enrichment' column...")
    
    # SQLite doesn't support ADD COLUMN with complex types, use raw SQL
    from sqlalchemy import text
    with engine.connect() as conn:
        if 'sqlite' in DATABASE_URL:
            conn.execute(text("ALTER TABLE transcriptions ADD COLUMN web_context_enrichment TEXT"))
        else:
            conn.execute(text("ALTER TABLE transcriptions ADD COLUMN web_context_enrichment TEXT NULL"))
        conn.commit()
    
    print("✅ Column 'web_context_enrichment' added successfully!")
    print("\n📝 This field will store:")
    print("  - AI-synthesized web search context")
    print("  - Connections between web info and transcript")
    print("  - Proper citations and references")
    print("  - Background information from reliable sources")

print("\n✨ Migration complete!")
