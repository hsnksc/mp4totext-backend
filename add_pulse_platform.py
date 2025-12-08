"""
Add Pulse Platform Tables Migration
====================================
Creates all tables needed for the Pulse social platform.
Run: python add_pulse_platform.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine, Base

# Import Pulse models to register them
from app.models.pulse import (
    Pulse, Follow, Circle, Hashtag, Resonance,
    PulseComment, PulseNotification, PulseAIGeneration,
    VibeCheck, PulseMessage,
    pulse_hashtags, circle_members
)


def run_migration():
    """Create Pulse platform tables."""
    print("🚀 Starting Pulse platform migration...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Pulse platform tables created successfully!")
    print("")
    print("📋 Created tables:")
    print("   - pulses (main content)")
    print("   - follows (user following)")
    print("   - circles (private groups)")
    print("   - hashtags (content discovery)")
    print("   - resonances (reactions)")
    print("   - pulse_comments (comments)")
    print("   - pulse_notifications (notifications)")
    print("   - pulse_ai_generations (AI tracking)")
    print("   - vibe_checks (community mood)")
    print("   - pulse_messages (DMs)")
    print("   - pulse_hashtags (junction table)")
    print("   - circle_members (junction table)")
    print("")
    print("🎉 Pulse platform is ready!")


if __name__ == "__main__":
    run_migration()
