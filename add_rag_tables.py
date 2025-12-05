"""
RAG Database Migration Script
==============================
Creates tables for RAG (Retrieval Augmented Generation) system.

Run this script to add RAG-related tables to your database:
    python add_rag_tables.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.database import Base, engine
from app.models.rag import (
    RAGSource, RAGSourceItem, RAGSourceChunk,
    RAGChatSession, RAGChatMessage, RAGGeneratedDocument
)

def add_rag_tables():
    """Create all RAG-related tables"""
    
    print("🚀 Starting RAG database migration...")
    
    # Create all RAG tables
    tables = [
        RAGSource.__table__,
        RAGSourceItem.__table__,
        RAGSourceChunk.__table__,
        RAGChatSession.__table__,
        RAGChatMessage.__table__,
        RAGGeneratedDocument.__table__
    ]
    
    for table in tables:
        try:
            table.create(engine, checkfirst=True)
            print(f"  ✅ Created table: {table.name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  ℹ️  Table already exists: {table.name}")
            else:
                print(f"  ❌ Error creating table {table.name}: {e}")
    
    print("\n✅ RAG database migration completed!")
    
    # Verify tables
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'rag_%'
            ORDER BY name
        """))
        rag_tables = [row[0] for row in result]
        
        print(f"\n📋 RAG Tables in database: {len(rag_tables)}")
        for table_name in rag_tables:
            print(f"   - {table_name}")


def verify_rag_tables():
    """Verify RAG tables exist and show their structure"""
    
    print("\n🔍 Verifying RAG tables...")
    
    expected_tables = [
        'rag_sources',
        'rag_source_items', 
        'rag_source_chunks',
        'rag_chat_sessions',
        'rag_chat_messages',
        'rag_generated_documents'
    ]
    
    with engine.connect() as conn:
        for table_name in expected_tables:
            try:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = result.fetchall()
                
                if columns:
                    print(f"\n  ✅ {table_name}: {len(columns)} columns")
                    for col in columns[:5]:  # Show first 5 columns
                        print(f"     - {col[1]} ({col[2]})")
                    if len(columns) > 5:
                        print(f"     ... and {len(columns) - 5} more columns")
                else:
                    print(f"\n  ❌ {table_name}: NOT FOUND")
                    
            except Exception as e:
                print(f"\n  ❌ Error checking {table_name}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("  RAG DATABASE MIGRATION")
    print("=" * 60)
    
    add_rag_tables()
    verify_rag_tables()
    
    print("\n" + "=" * 60)
    print("  Migration Complete!")
    print("=" * 60)
