"""
Add generated_videos table for video generation feature
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.settings import get_settings
from app.database import Base

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)


def add_generated_videos_table():
    """Add generated_videos table"""
    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='generated_videos'"
        ))
        
        if result.fetchone():
            print("✅ generated_videos table already exists")
            return
        
        print("📝 Creating generated_videos table...")
        
        conn.execute(text("""
            CREATE TABLE generated_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transcription_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                filename VARCHAR(500) NOT NULL,
                url VARCHAR(1000),
                duration FLOAT,
                style VARCHAR(100),
                status VARCHAR(50) DEFAULT 'processing',
                progress INTEGER DEFAULT 0,
                error_message TEXT,
                segments JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                task_id VARCHAR(255),
                FOREIGN KEY (transcription_id) REFERENCES transcriptions(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        
        # Create indexes
        conn.execute(text(
            "CREATE INDEX idx_generated_videos_transcription ON generated_videos(transcription_id)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_generated_videos_user ON generated_videos(user_id)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_generated_videos_status ON generated_videos(status)"
        ))
        
        conn.commit()
        print("✅ generated_videos table created successfully")


if __name__ == "__main__":
    print("🚀 Adding video generation feature...")
    add_generated_videos_table()
    print("✅ Migration completed!")
