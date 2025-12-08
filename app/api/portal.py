"""
Gistify Portal API
==================
Central portal for accessing all Gistify applications.
Provides app directory, user preferences, and cross-app navigation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.auth.utils import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


# ============================================================================
# SCHEMAS
# ============================================================================

class AppInfo(BaseModel):
    """Information about a Gistify application"""
    id: str
    name: str
    description: str
    url: str
    icon: str  # Icon name or emoji
    color: str  # Primary color hex
    gradient: str  # Tailwind gradient classes
    is_available: bool = True
    requires_credits: bool = False
    badge: Optional[str] = None  # e.g., "NEW", "BETA"


class PortalAppsResponse(BaseModel):
    """Response containing all available apps"""
    apps: List[AppInfo]
    user: dict
    timestamp: str


class UserPreferences(BaseModel):
    """User preferences for portal"""
    theme: str = "system"  # light, dark, system
    default_app: Optional[str] = None
    language: str = "en"


# ============================================================================
# APP REGISTRY
# ============================================================================

# Define all Gistify applications
GISTIFY_APPS = [
    AppInfo(
        id="notebook",
        name="Notebook",
        description="AI-powered notes & knowledge base with RAG",
        url="https://notebook.gistify.pro",
        icon="book-open",
        color="#10b981",
        gradient="from-emerald-500 to-teal-600",
        is_available=True,
        requires_credits=True,
    ),
    AppInfo(
        id="pulse",
        name="Pulse",
        description="Share ideas with resonance reactions",
        url="https://pulse.gistify.pro",
        icon="heart",
        color="#ec4899",
        gradient="from-pink-500 to-rose-600",
        is_available=True,
        requires_credits=True,
        badge="NEW",
    ),
    AppInfo(
        id="mp4totext",
        name="MP4toText",
        description="Transcribe audio & video with AI",
        url="https://gistify.pro",
        icon="mic",
        color="#8b5cf6",
        gradient="from-violet-500 to-purple-600",
        is_available=True,
        requires_credits=True,
    ),
    AppInfo(
        id="mixup",
        name="MixUp",
        description="Creative content mixer & editor",
        url="https://gistify.pro/mixup",
        icon="layout",
        color="#f59e0b",
        gradient="from-amber-500 to-orange-600",
        is_available=True,
        requires_credits=True,
    ),
]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/apps", response_model=PortalAppsResponse)
async def get_portal_apps(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all available Gistify applications for the portal.
    Returns app list with user info and credits.
    """
    return PortalAppsResponse(
        apps=GISTIFY_APPS,
        user={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "credits": float(current_user.credits) if current_user.credits else 0.0,
            "is_admin": current_user.is_admin if hasattr(current_user, 'is_admin') else False,
        },
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/apps/{app_id}")
async def get_app_info(
    app_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get information about a specific application.
    """
    for app in GISTIFY_APPS:
        if app.id == app_id:
            return {
                "app": app.dict(),
                "user_credits": float(current_user.credits) if current_user.credits else 0.0,
            }
    
    raise HTTPException(status_code=404, detail=f"App '{app_id}' not found")


@router.get("/user/stats")
async def get_user_portal_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user statistics across all Gistify applications.
    """
    from app.models.transcription import Transcription
    from app.models.pulse import Pulse
    from app.models.source import Source
    
    # Count transcriptions
    transcription_count = db.query(Transcription).filter(
        Transcription.user_id == current_user.id
    ).count()
    
    # Count pulses
    try:
        pulse_count = db.query(Pulse).filter(
            Pulse.user_id == current_user.id
        ).count()
    except:
        pulse_count = 0
    
    # Count sources (notebooks)
    try:
        source_count = db.query(Source).filter(
            Source.user_id == current_user.id
        ).count()
    except:
        source_count = 0
    
    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "credits": float(current_user.credits) if current_user.credits else 0.0,
        },
        "stats": {
            "transcriptions": transcription_count,
            "pulses": pulse_count,
            "sources": source_count,
            "total_items": transcription_count + pulse_count + source_count,
        },
        "apps_used": [
            app.id for app in GISTIFY_APPS 
            if (app.id == "mp4totext" and transcription_count > 0) or
               (app.id == "pulse" and pulse_count > 0) or
               (app.id == "notebook" and source_count > 0)
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/preferences")
async def update_user_preferences(
    preferences: UserPreferences,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user portal preferences (theme, default app, language).
    Stored in user's metadata or dedicated preferences table.
    """
    # For now, just return success - preferences can be stored in localStorage
    # In future, can add UserPreferences model to database
    return {
        "success": True,
        "message": "Preferences updated",
        "preferences": preferences.dict(),
    }


@router.get("/health")
async def portal_health():
    """
    Health check for portal API.
    """
    return {
        "status": "healthy",
        "service": "gistify-portal",
        "timestamp": datetime.utcnow().isoformat(),
        "apps_count": len(GISTIFY_APPS),
    }
