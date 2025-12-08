"""
Pulse Social Platform API
=========================
API endpoints for the Pulse social media platform.
Integrated with MixUp/Gistify - shared user authentication.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth.utils import get_current_active_user
from app.models.user import User
from app.models.pulse import (
    Pulse, Follow, Circle, Hashtag, Resonance, PulseComment,
    PulseNotification, PulseAIGeneration, VibeCheck,
    PulseVisibility, PulseStatus, ResonanceType, ContentType, AIGenerationType
)
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType

router = APIRouter(prefix="/pulse", tags=["pulse"])


# ============================================================================
# SCHEMAS
# ============================================================================

class PulseCreate(BaseModel):
    """Create a new pulse"""
    content: str = Field(..., min_length=1, max_length=10000)
    content_type: ContentType = ContentType.TEXT
    visibility: PulseVisibility = PulseVisibility.PUBLIC
    
    # Optional fields
    media_urls: List[str] = []
    hashtags: List[str] = []
    circle_id: Optional[int] = None
    parent_id: Optional[int] = None  # For threads
    
    # MixUp integration
    mixup_items: Optional[dict] = None
    mixup_source_id: Optional[int] = None
    
    # AI formatting
    use_ai_formatting: bool = False
    ai_model: Optional[str] = None
    ai_prompt: Optional[str] = None


class PulseUpdate(BaseModel):
    """Update an existing pulse"""
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    visibility: Optional[PulseVisibility] = None
    circle_id: Optional[int] = None


class PulseResponse(BaseModel):
    """Pulse response"""
    id: int
    user_id: int
    username: str
    content: str
    formatted_content: Optional[str]
    content_type: ContentType
    visibility: PulseVisibility
    status: PulseStatus
    media_urls: List[str]
    hashtags: List[str]
    
    # Stats
    resonance_count: int
    comment_count: int
    share_count: int
    view_count: int
    
    # User's resonance (if any)
    user_resonance: Optional[str] = None
    
    # Threading
    parent_id: Optional[int]
    thread_position: int
    
    # AI info
    ai_generated: bool
    
    # Timestamps
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResonanceCreate(BaseModel):
    """Add resonance to a pulse"""
    resonance_type: ResonanceType


class CommentCreate(BaseModel):
    """Create a comment"""
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[int] = None


class CommentResponse(BaseModel):
    """Comment response"""
    id: int
    user_id: int
    username: str
    content: str
    parent_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CircleCreate(BaseModel):
    """Create a circle"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    color: str = "#6366f1"
    icon: str = "👥"


class CircleResponse(BaseModel):
    """Circle response"""
    id: int
    name: str
    description: Optional[str]
    color: str
    icon: str
    member_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """User profile for Pulse"""
    id: int
    username: str
    full_name: Optional[str]
    
    pulse_count: int
    follower_count: int
    following_count: int
    
    is_following: bool = False
    
    class Config:
        from_attributes = True


class VibeCheckCreate(BaseModel):
    """Set your vibe"""
    vibe: str = Field(..., max_length=50)
    message: Optional[str] = Field(None, max_length=200)
    duration_hours: int = Field(24, ge=1, le=168)  # 1 hour to 1 week


class AIFormatRequest(BaseModel):
    """Request AI formatting for pulse content"""
    content: str = Field(..., min_length=1, max_length=10000)
    style: str = Field("social", description="social, professional, casual, creative")
    ai_model: Optional[str] = "gemini-2.0-flash"


class FeedResponse(BaseModel):
    """Feed pagination response"""
    pulses: List[PulseResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ============================================================================
# FEED ENDPOINTS
# ============================================================================

@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get personalized feed for the current user.
    Shows pulses from followed users + public trending.
    """
    offset = (page - 1) * page_size
    
    # Get users that current user follows
    following_ids = db.query(Follow.following_id).filter(
        Follow.follower_id == current_user.id
    ).subquery()
    
    # Query pulses: from followed users OR public
    query = db.query(Pulse).filter(
        Pulse.status == PulseStatus.PUBLISHED,
        or_(
            Pulse.user_id.in_(following_ids),
            Pulse.visibility == PulseVisibility.PUBLIC
        )
    ).order_by(desc(Pulse.created_at))
    
    total = query.count()
    pulses = query.offset(offset).limit(page_size).all()
    
    # Build response with user info and resonance status
    pulse_responses = []
    for pulse in pulses:
        # Check user's resonance on this pulse
        user_resonance = db.query(Resonance).filter(
            Resonance.pulse_id == pulse.id,
            Resonance.user_id == current_user.id
        ).first()
        
        pulse_responses.append(PulseResponse(
            id=pulse.id,
            user_id=pulse.user_id,
            username=pulse.user.username,
            content=pulse.content,
            formatted_content=pulse.formatted_content,
            content_type=pulse.content_type,
            visibility=pulse.visibility,
            status=pulse.status,
            media_urls=pulse.media_urls or [],
            hashtags=[h.name for h in pulse.hashtags],
            resonance_count=pulse.resonance_count,
            comment_count=pulse.comment_count,
            share_count=pulse.share_count,
            view_count=pulse.view_count,
            user_resonance=user_resonance.resonance_type.value if user_resonance else None,
            parent_id=pulse.parent_id,
            thread_position=pulse.thread_position,
            ai_generated=pulse.ai_generated,
            created_at=pulse.created_at
        ))
    
    return FeedResponse(
        pulses=pulse_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )


@router.get("/explore")
async def explore_pulses(
    hashtag: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Explore public pulses, optionally filtered by hashtag.
    """
    offset = (page - 1) * page_size
    
    query = db.query(Pulse).filter(
        Pulse.status == PulseStatus.PUBLISHED,
        Pulse.visibility == PulseVisibility.PUBLIC
    )
    
    if hashtag:
        query = query.join(Pulse.hashtags).filter(
            Hashtag.name == hashtag.lower().strip('#')
        )
    
    query = query.order_by(desc(Pulse.resonance_count), desc(Pulse.created_at))
    
    total = query.count()
    pulses = query.offset(offset).limit(page_size).all()
    
    return {
        "pulses": pulses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": (offset + page_size) < total
    }


# ============================================================================
# PULSE CRUD
# ============================================================================

@router.post("/pulses", response_model=PulseResponse)
async def create_pulse(
    request: PulseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new pulse.
    Optionally use AI formatting (costs credits).
    """
    formatted_content = None
    ai_generated = False
    credits_used = 0.0
    
    # AI Formatting (if requested)
    if request.use_ai_formatting and request.ai_model:
        # Check credits
        required_credits = 2.0  # Base cost for AI formatting
        if current_user.credits < required_credits:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. Required: {required_credits}, Available: {current_user.credits}"
            )
        
        # TODO: Call AI service for formatting
        # For now, just mark as AI formatted
        formatted_content = request.content  # Will be replaced with AI result
        ai_generated = True
        credits_used = required_credits
    
    # Create pulse
    pulse = Pulse(
        user_id=current_user.id,
        content=request.content,
        formatted_content=formatted_content,
        content_type=request.content_type,
        visibility=request.visibility,
        status=PulseStatus.PUBLISHED,
        media_urls=request.media_urls,
        mixup_items=request.mixup_items,
        mixup_source_id=request.mixup_source_id,
        parent_id=request.parent_id,
        circle_id=request.circle_id,
        ai_generated=ai_generated,
        ai_model=request.ai_model if ai_generated else None,
        ai_prompt=request.ai_prompt if ai_generated else None,
        published_at=datetime.utcnow()
    )
    
    # Handle hashtags
    for tag_name in request.hashtags:
        tag_name = tag_name.lower().strip('#')
        if not tag_name:
            continue
            
        hashtag = db.query(Hashtag).filter(Hashtag.name == tag_name).first()
        if not hashtag:
            hashtag = Hashtag(name=tag_name)
            db.add(hashtag)
        
        hashtag.use_count += 1
        pulse.hashtags.append(hashtag)
    
    db.add(pulse)
    db.commit()
    db.refresh(pulse)
    
    # Deduct credits if AI was used
    if credits_used > 0:
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=current_user.id,
            amount=credits_used,
            operation_type=OperationType.ENHANCEMENT,
            description=f"Pulse AI formatting",
            metadata={"pulse_id": pulse.id, "ai_model": request.ai_model}
        )
    
    return PulseResponse(
        id=pulse.id,
        user_id=pulse.user_id,
        username=current_user.username,
        content=pulse.content,
        formatted_content=pulse.formatted_content,
        content_type=pulse.content_type,
        visibility=pulse.visibility,
        status=pulse.status,
        media_urls=pulse.media_urls or [],
        hashtags=[h.name for h in pulse.hashtags],
        resonance_count=0,
        comment_count=0,
        share_count=0,
        view_count=0,
        user_resonance=None,
        parent_id=pulse.parent_id,
        thread_position=pulse.thread_position,
        ai_generated=pulse.ai_generated,
        created_at=pulse.created_at
    )


@router.get("/pulses/{pulse_id}", response_model=PulseResponse)
async def get_pulse(
    pulse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific pulse by ID."""
    pulse = db.query(Pulse).filter(Pulse.id == pulse_id).first()
    
    if not pulse:
        raise HTTPException(status_code=404, detail="Pulse not found")
    
    # Check visibility
    if pulse.visibility == PulseVisibility.PRIVATE and pulse.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this pulse")
    
    if pulse.visibility == PulseVisibility.FOLLOWERS:
        is_following = db.query(Follow).filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == pulse.user_id
        ).first()
        if not is_following and pulse.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only followers can view this pulse")
    
    # Increment view count
    pulse.view_count += 1
    db.commit()
    
    # Get user's resonance
    user_resonance = db.query(Resonance).filter(
        Resonance.pulse_id == pulse.id,
        Resonance.user_id == current_user.id
    ).first()
    
    return PulseResponse(
        id=pulse.id,
        user_id=pulse.user_id,
        username=pulse.user.username,
        content=pulse.content,
        formatted_content=pulse.formatted_content,
        content_type=pulse.content_type,
        visibility=pulse.visibility,
        status=pulse.status,
        media_urls=pulse.media_urls or [],
        hashtags=[h.name for h in pulse.hashtags],
        resonance_count=pulse.resonance_count,
        comment_count=pulse.comment_count,
        share_count=pulse.share_count,
        view_count=pulse.view_count,
        user_resonance=user_resonance.resonance_type.value if user_resonance else None,
        parent_id=pulse.parent_id,
        thread_position=pulse.thread_position,
        ai_generated=pulse.ai_generated,
        created_at=pulse.created_at
    )


@router.put("/pulses/{pulse_id}")
async def update_pulse(
    pulse_id: int,
    request: PulseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a pulse (only owner can update)."""
    pulse = db.query(Pulse).filter(
        Pulse.id == pulse_id,
        Pulse.user_id == current_user.id
    ).first()
    
    if not pulse:
        raise HTTPException(status_code=404, detail="Pulse not found or not authorized")
    
    if request.content:
        pulse.content = request.content
    if request.visibility:
        pulse.visibility = request.visibility
    if request.circle_id is not None:
        pulse.circle_id = request.circle_id
    
    db.commit()
    
    return {"success": True, "message": "Pulse updated"}


@router.delete("/pulses/{pulse_id}")
async def delete_pulse(
    pulse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Soft delete a pulse."""
    pulse = db.query(Pulse).filter(
        Pulse.id == pulse_id,
        Pulse.user_id == current_user.id
    ).first()
    
    if not pulse:
        raise HTTPException(status_code=404, detail="Pulse not found or not authorized")
    
    pulse.status = PulseStatus.DELETED
    db.commit()
    
    return {"success": True, "message": "Pulse deleted"}


# ============================================================================
# RESONANCE (REACTIONS)
# ============================================================================

@router.post("/pulses/{pulse_id}/resonance")
async def add_resonance(
    pulse_id: int,
    request: ResonanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add or change resonance on a pulse."""
    pulse = db.query(Pulse).filter(Pulse.id == pulse_id).first()
    
    if not pulse:
        raise HTTPException(status_code=404, detail="Pulse not found")
    
    # Check if user already has a resonance
    existing = db.query(Resonance).filter(
        Resonance.pulse_id == pulse_id,
        Resonance.user_id == current_user.id
    ).first()
    
    if existing:
        # Update existing resonance
        existing.resonance_type = request.resonance_type
    else:
        # Create new resonance
        resonance = Resonance(
            pulse_id=pulse_id,
            user_id=current_user.id,
            resonance_type=request.resonance_type
        )
        db.add(resonance)
        pulse.resonance_count += 1
    
    db.commit()
    
    # Create notification for pulse author
    if pulse.user_id != current_user.id:
        notification = PulseNotification(
            user_id=pulse.user_id,
            actor_id=current_user.id,
            pulse_id=pulse_id,
            notification_type="resonance",
            title=f"{current_user.username} resonated with your pulse",
            body=f"{request.resonance_type.value}: {pulse.content[:50]}..."
        )
        db.add(notification)
        db.commit()
    
    return {"success": True, "resonance_type": request.resonance_type.value}


@router.delete("/pulses/{pulse_id}/resonance")
async def remove_resonance(
    pulse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove resonance from a pulse."""
    resonance = db.query(Resonance).filter(
        Resonance.pulse_id == pulse_id,
        Resonance.user_id == current_user.id
    ).first()
    
    if not resonance:
        raise HTTPException(status_code=404, detail="Resonance not found")
    
    # Update pulse count
    pulse = db.query(Pulse).filter(Pulse.id == pulse_id).first()
    if pulse and pulse.resonance_count > 0:
        pulse.resonance_count -= 1
    
    db.delete(resonance)
    db.commit()
    
    return {"success": True, "message": "Resonance removed"}


@router.get("/pulses/{pulse_id}/resonances")
async def get_resonances(
    pulse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get resonance breakdown for a pulse."""
    resonances = db.query(
        Resonance.resonance_type,
        func.count(Resonance.id).label('count')
    ).filter(
        Resonance.pulse_id == pulse_id
    ).group_by(Resonance.resonance_type).all()
    
    breakdown = {rt.value: 0 for rt in ResonanceType}
    for r_type, count in resonances:
        breakdown[r_type.value] = count
    
    return {
        "pulse_id": pulse_id,
        "total": sum(breakdown.values()),
        "breakdown": breakdown
    }


# ============================================================================
# COMMENTS
# ============================================================================

@router.get("/pulses/{pulse_id}/comments")
async def get_comments(
    pulse_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comments for a pulse."""
    offset = (page - 1) * page_size
    
    query = db.query(PulseComment).filter(
        PulseComment.pulse_id == pulse_id,
        PulseComment.parent_id == None  # Top-level comments only
    ).order_by(desc(PulseComment.created_at))
    
    total = query.count()
    comments = query.offset(offset).limit(page_size).all()
    
    comment_responses = []
    for comment in comments:
        comment_responses.append(CommentResponse(
            id=comment.id,
            user_id=comment.user_id,
            username=comment.user.username,
            content=comment.content,
            parent_id=comment.parent_id,
            created_at=comment.created_at
        ))
    
    return {
        "comments": comment_responses,
        "total": total,
        "page": page,
        "has_more": (offset + page_size) < total
    }


@router.post("/pulses/{pulse_id}/comments")
async def create_comment(
    pulse_id: int,
    request: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a comment to a pulse."""
    pulse = db.query(Pulse).filter(Pulse.id == pulse_id).first()
    
    if not pulse:
        raise HTTPException(status_code=404, detail="Pulse not found")
    
    comment = PulseComment(
        pulse_id=pulse_id,
        user_id=current_user.id,
        content=request.content,
        parent_id=request.parent_id
    )
    
    db.add(comment)
    pulse.comment_count += 1
    db.commit()
    db.refresh(comment)
    
    # Create notification
    if pulse.user_id != current_user.id:
        notification = PulseNotification(
            user_id=pulse.user_id,
            actor_id=current_user.id,
            pulse_id=pulse_id,
            comment_id=comment.id,
            notification_type="comment",
            title=f"{current_user.username} commented on your pulse",
            body=request.content[:100]
        )
        db.add(notification)
        db.commit()
    
    return CommentResponse(
        id=comment.id,
        user_id=comment.user_id,
        username=current_user.username,
        content=comment.content,
        parent_id=comment.parent_id,
        created_at=comment.created_at
    )


# ============================================================================
# FOLLOW SYSTEM
# ============================================================================

@router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Follow a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already following this user")
    
    follow = Follow(
        follower_id=current_user.id,
        following_id=user_id
    )
    db.add(follow)
    
    # Create notification
    notification = PulseNotification(
        user_id=user_id,
        actor_id=current_user.id,
        notification_type="follow",
        title=f"{current_user.username} started following you"
    )
    db.add(notification)
    
    db.commit()
    
    return {"success": True, "message": f"Now following {target_user.username}"}


@router.delete("/users/{user_id}/follow")
async def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Unfollow a user."""
    follow = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()
    
    if not follow:
        raise HTTPException(status_code=404, detail="Not following this user")
    
    db.delete(follow)
    db.commit()
    
    return {"success": True, "message": "Unfollowed successfully"}


@router.get("/users/{user_id}/followers")
async def get_followers(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get followers of a user."""
    offset = (page - 1) * page_size
    
    query = db.query(Follow).filter(Follow.following_id == user_id)
    
    total = query.count()
    follows = query.offset(offset).limit(page_size).all()
    
    followers = []
    for follow in follows:
        is_following = db.query(Follow).filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == follow.follower_id
        ).first() is not None
        
        followers.append({
            "id": follow.follower.id,
            "username": follow.follower.username,
            "full_name": follow.follower.full_name,
            "is_following": is_following
        })
    
    return {
        "followers": followers,
        "total": total,
        "page": page,
        "has_more": (offset + page_size) < total
    }


@router.get("/users/{user_id}/following")
async def get_following(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get users that a user is following."""
    offset = (page - 1) * page_size
    
    query = db.query(Follow).filter(Follow.follower_id == user_id)
    
    total = query.count()
    follows = query.offset(offset).limit(page_size).all()
    
    following = []
    for follow in follows:
        is_following = db.query(Follow).filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == follow.following_id
        ).first() is not None
        
        following.append({
            "id": follow.following.id,
            "username": follow.following.username,
            "full_name": follow.following.full_name,
            "is_following": is_following
        })
    
    return {
        "following": following,
        "total": total,
        "page": page,
        "has_more": (offset + page_size) < total
    }


# ============================================================================
# USER PROFILE
# ============================================================================

@router.get("/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user profile for Pulse."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    pulse_count = db.query(Pulse).filter(
        Pulse.user_id == user_id,
        Pulse.status == PulseStatus.PUBLISHED
    ).count()
    
    follower_count = db.query(Follow).filter(Follow.following_id == user_id).count()
    following_count = db.query(Follow).filter(Follow.follower_id == user_id).count()
    
    is_following = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first() is not None
    
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        pulse_count=pulse_count,
        follower_count=follower_count,
        following_count=following_count,
        is_following=is_following
    )


@router.get("/users/{user_id}/pulses")
async def get_user_pulses(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get pulses by a specific user."""
    offset = (page - 1) * page_size
    
    # Build visibility filter
    visibility_filter = [PulseVisibility.PUBLIC]
    
    # If viewing own profile, show all
    if user_id == current_user.id:
        visibility_filter = [PulseVisibility.PUBLIC, PulseVisibility.FOLLOWERS, PulseVisibility.CIRCLE, PulseVisibility.PRIVATE]
    else:
        # Check if following
        is_following = db.query(Follow).filter(
            Follow.follower_id == current_user.id,
            Follow.following_id == user_id
        ).first()
        if is_following:
            visibility_filter.append(PulseVisibility.FOLLOWERS)
    
    query = db.query(Pulse).filter(
        Pulse.user_id == user_id,
        Pulse.status == PulseStatus.PUBLISHED,
        Pulse.visibility.in_(visibility_filter)
    ).order_by(desc(Pulse.created_at))
    
    total = query.count()
    pulses = query.offset(offset).limit(page_size).all()
    
    return {
        "pulses": pulses,
        "total": total,
        "page": page,
        "has_more": (offset + page_size) < total
    }


# ============================================================================
# CIRCLES
# ============================================================================

@router.get("/circles")
async def get_my_circles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get circles created by current user."""
    circles = db.query(Circle).filter(
        Circle.user_id == current_user.id,
        Circle.is_active == True
    ).all()
    
    circle_responses = []
    for circle in circles:
        member_count = len(circle.members)
        circle_responses.append(CircleResponse(
            id=circle.id,
            name=circle.name,
            description=circle.description,
            color=circle.color,
            icon=circle.icon,
            member_count=member_count,
            created_at=circle.created_at
        ))
    
    return {"circles": circle_responses}


@router.post("/circles", response_model=CircleResponse)
async def create_circle(
    request: CircleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new circle."""
    circle = Circle(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon
    )
    
    db.add(circle)
    db.commit()
    db.refresh(circle)
    
    return CircleResponse(
        id=circle.id,
        name=circle.name,
        description=circle.description,
        color=circle.color,
        icon=circle.icon,
        member_count=0,
        created_at=circle.created_at
    )


@router.post("/circles/{circle_id}/members/{user_id}")
async def add_circle_member(
    circle_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a member to a circle."""
    circle = db.query(Circle).filter(
        Circle.id == circle_id,
        Circle.user_id == current_user.id
    ).first()
    
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found or not authorized")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user in circle.members:
        raise HTTPException(status_code=400, detail="User already in circle")
    
    circle.members.append(user)
    db.commit()
    
    return {"success": True, "message": f"{user.username} added to circle"}


@router.delete("/circles/{circle_id}/members/{user_id}")
async def remove_circle_member(
    circle_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a member from a circle."""
    circle = db.query(Circle).filter(
        Circle.id == circle_id,
        Circle.user_id == current_user.id
    ).first()
    
    if not circle:
        raise HTTPException(status_code=404, detail="Circle not found or not authorized")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user not in circle.members:
        raise HTTPException(status_code=400, detail="User not in circle")
    
    circle.members.remove(user)
    db.commit()
    
    return {"success": True, "message": f"{user.username} removed from circle"}


# ============================================================================
# VIBE CHECK
# ============================================================================

@router.post("/vibe")
async def set_vibe(
    request: VibeCheckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set your current vibe."""
    vibe = VibeCheck(
        user_id=current_user.id,
        vibe=request.vibe,
        message=request.message,
        expires_at=datetime.utcnow() + timedelta(hours=request.duration_hours)
    )
    
    db.add(vibe)
    db.commit()
    db.refresh(vibe)
    
    return {
        "success": True,
        "vibe": vibe.vibe,
        "expires_at": vibe.expires_at
    }


@router.get("/vibe/community")
async def get_community_vibe(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get community vibe aggregation."""
    # Get active vibes (not expired)
    now = datetime.utcnow()
    
    vibes = db.query(
        VibeCheck.vibe,
        func.count(VibeCheck.id).label('count')
    ).filter(
        or_(
            VibeCheck.expires_at == None,
            VibeCheck.expires_at > now
        )
    ).group_by(VibeCheck.vibe).order_by(desc('count')).limit(10).all()
    
    total = sum(v.count for v in vibes)
    
    return {
        "total_participants": total,
        "vibes": [
            {
                "vibe": v.vibe,
                "count": v.count,
                "percentage": round(v.count / total * 100, 1) if total > 0 else 0
            }
            for v in vibes
        ]
    }


# ============================================================================
# NOTIFICATIONS
# ============================================================================

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get notifications for current user."""
    offset = (page - 1) * page_size
    
    query = db.query(PulseNotification).filter(
        PulseNotification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(PulseNotification.is_read == False)
    
    query = query.order_by(desc(PulseNotification.created_at))
    
    total = query.count()
    notifications = query.offset(offset).limit(page_size).all()
    
    unread_count = db.query(PulseNotification).filter(
        PulseNotification.user_id == current_user.id,
        PulseNotification.is_read == False
    ).count()
    
    return {
        "notifications": notifications,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "has_more": (offset + page_size) < total
    }


@router.post("/notifications/read")
async def mark_notifications_read(
    notification_ids: List[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark notifications as read."""
    query = db.query(PulseNotification).filter(
        PulseNotification.user_id == current_user.id
    )
    
    if notification_ids:
        query = query.filter(PulseNotification.id.in_(notification_ids))
    
    query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    
    return {"success": True, "message": "Notifications marked as read"}


# ============================================================================
# HASHTAGS / TRENDING
# ============================================================================

@router.get("/trending/hashtags")
async def get_trending_hashtags(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get trending hashtags."""
    hashtags = db.query(Hashtag).order_by(
        desc(Hashtag.use_count)
    ).limit(limit).all()
    
    return {
        "hashtags": [
            {"name": h.name, "count": h.use_count}
            for h in hashtags
        ]
    }


# ============================================================================
# AI FORMATTING
# ============================================================================

@router.post("/ai/format")
async def format_with_ai(
    request: AIFormatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Format content for social sharing using AI."""
    # Check credits
    required_credits = 2.0
    if current_user.credits < required_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Required: {required_credits}, Available: {current_user.credits}"
        )
    
    # TODO: Integrate with Gemini/AI service
    # For now, return the content as-is with a placeholder
    formatted = f"✨ {request.content}"
    
    # Deduct credits
    credit_service = get_credit_service(db)
    credit_service.deduct_credits(
        user_id=current_user.id,
        amount=required_credits,
        operation_type=OperationType.ENHANCEMENT,
        description=f"Pulse AI formatting ({request.style})",
        metadata={"style": request.style, "ai_model": request.ai_model}
    )
    
    return {
        "original": request.content,
        "formatted": formatted,
        "credits_used": required_credits
    }
