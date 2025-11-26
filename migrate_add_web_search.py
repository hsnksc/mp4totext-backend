"""
Database migration script - Add enable_web_search column
"""
from app.database import engine
from sqlalchemy import text
import sys

try:
    with engine.begin() as conn:
        # Try to add the column
        conn.execute(text('ALTER TABLE transcriptions ADD COLUMN enable_web_search BOOLEAN DEFAULT FALSE'))
        print('✅ enable_web_search sütunu başarıyla eklendi')
except Exception as e:
    if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
        print('ℹ️ enable_web_search sütunu zaten mevcut')
    else:
        print(f'❌ Hata: {e}')
        sys.exit(1)
