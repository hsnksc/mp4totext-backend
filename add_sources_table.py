"""
Add Sources table for Mix Up feature
"""
from app.database import engine, SessionLocal
from app.models.source import Source
from sqlalchemy import inspect

def add_sources_table():
    """Create sources table if not exists"""
    print("🔧 Adding Sources table...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if "sources" in existing_tables:
        print("✅ Sources table already exists")
        return
    
    # Create the table
    Source.__table__.create(engine)
    print("✅ Sources table created successfully!")
    
    # Verify
    inspector = inspect(engine)
    if "sources" in inspector.get_table_names():
        print("✅ Verified: Sources table exists")
        columns = [col['name'] for col in inspector.get_columns('sources')]
        print(f"   Columns: {', '.join(columns)}")
    else:
        print("❌ Error: Sources table was not created")

if __name__ == "__main__":
    add_sources_table()
