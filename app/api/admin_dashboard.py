"""
Admin Dashboard API
Comprehensive admin endpoints for system management
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from pydantic import BaseModel, Field

from app.database import get_db
from app.auth.utils import get_current_user
from app.models.user import User
from app.models.transcription import Transcription
from app.models.credit_transaction import CreditTransaction
from app.models.credit_pricing import CreditPricingConfig
from app.models.ai_model_pricing import AIModelPricing
from app.models.generated_image import GeneratedImage
from app.models.generated_video import GeneratedVideo
from app.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin-dashboard"])
settings = get_settings()


# ============================================================================
# AUTH HELPER
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================================
# SCHEMAS
# ============================================================================

class DashboardStats(BaseModel):
    total_users: int
    active_users_30d: int
    total_transcriptions: int
    transcriptions_today: int
    total_credits_used: float
    total_images_generated: int
    total_videos_generated: int
    storage_used_mb: float


class UserSummary(BaseModel):
    id: int
    username: str
    email: str
    credits: float
    is_active: bool
    is_superuser: bool
    transcription_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    credits: Optional[float] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class CreditAdjustment(BaseModel):
    user_id: int
    amount: float = Field(..., description="Positive to add, negative to deduct")
    reason: str = Field(..., min_length=3, max_length=200)


class AIModelUpdate(BaseModel):
    is_active: Optional[bool] = None
    credit_multiplier: Optional[float] = None
    cost_per_1k_chars: Optional[float] = None
    is_default: Optional[bool] = None


class PricingUpdate(BaseModel):
    cost_per_unit: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class SystemConfig(BaseModel):
    # Transcription providers
    use_assemblyai: bool
    use_faster_whisper: bool
    use_modal: bool
    
    # AI Enhancement
    gemini_enabled: bool
    openai_enabled: bool
    groq_enabled: bool
    together_enabled: bool
    
    # Image Generation
    modal_flux_enabled: bool
    replicate_enabled: bool
    
    # General
    max_file_size_mb: int
    default_credits_new_user: float


# ============================================================================
# DASHBOARD STATS
# ============================================================================

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get overall system statistics"""
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = now - timedelta(days=30)
    
    # User stats
    total_users = db.query(func.count(User.id)).scalar()
    active_users_30d = db.query(func.count(User.id)).filter(
        User.created_at >= thirty_days_ago
    ).scalar()
    
    # Transcription stats
    total_transcriptions = db.query(func.count(Transcription.id)).scalar()
    transcriptions_today = db.query(func.count(Transcription.id)).filter(
        Transcription.created_at >= today_start
    ).scalar()
    
    # Credit stats
    total_credits_used = db.query(
        func.sum(func.abs(CreditTransaction.amount))
    ).filter(
        CreditTransaction.amount < 0
    ).scalar() or 0
    
    # Generated content stats
    total_images = db.query(func.count(GeneratedImage.id)).scalar()
    total_videos = db.query(func.count(GeneratedVideo.id)).scalar()
    
    # Storage (approximate from file sizes)
    image_storage = db.query(func.sum(GeneratedImage.file_size)).scalar() or 0
    storage_used_mb = image_storage / (1024 * 1024)
    
    return DashboardStats(
        total_users=total_users,
        active_users_30d=active_users_30d,
        total_transcriptions=total_transcriptions,
        transcriptions_today=transcriptions_today,
        total_credits_used=round(total_credits_used, 2),
        total_images_generated=total_images,
        total_videos_generated=total_videos,
        storage_used_mb=round(storage_used_mb, 2)
    )


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.get("/users", response_model=List[UserSummary])
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users with their stats"""
    
    query = db.query(User)
    
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    
    users = query.order_by(desc(User.created_at)).offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        transcription_count = db.query(func.count(Transcription.id)).filter(
            Transcription.user_id == user.id
        ).scalar()
        
        result.append(UserSummary(
            id=user.id,
            username=user.username,
            email=user.email,
            credits=user.credits,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            transcription_count=transcription_count,
            created_at=user.created_at
        ))
    
    return result


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get stats
    transcription_count = db.query(func.count(Transcription.id)).filter(
        Transcription.user_id == user_id
    ).scalar()
    
    image_count = db.query(func.count(GeneratedImage.id)).filter(
        GeneratedImage.user_id == user_id
    ).scalar()
    
    # Recent transactions
    recent_transactions = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id
    ).order_by(desc(CreditTransaction.created_at)).limit(10).all()
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "credits": user.credits,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at,
        "stats": {
            "transcription_count": transcription_count,
            "image_count": image_count
        },
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "operation_type": t.operation_type,
                "description": t.description,
                "created_at": t.created_at
            }
            for t in recent_transactions
        ]
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    update: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user properties"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if update.credits is not None:
        user.credits = update.credits
    if update.is_active is not None:
        user.is_active = update.is_active
    if update.is_superuser is not None:
        user.is_superuser = update.is_superuser
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"✅ Admin {admin.username} updated user {user.username}")
    
    return {"success": True, "user": {
        "id": user.id,
        "username": user.username,
        "credits": user.credits,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser
    }}


@router.post("/users/{user_id}/credits")
async def adjust_user_credits(
    user_id: int,
    adjustment: CreditAdjustment,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Add or remove credits from a user"""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_credits = user.credits
    user.credits += adjustment.amount
    
    # Log transaction
    transaction = CreditTransaction(
        user_id=user_id,
        amount=adjustment.amount,
        operation_type="admin_adjustment",
        description=f"Admin adjustment: {adjustment.reason}",
        balance_after=user.credits
    )
    db.add(transaction)
    db.commit()
    
    logger.info(f"💰 Admin {admin.username} adjusted credits for {user.username}: {old_credits} -> {user.credits} ({adjustment.reason})")
    
    return {
        "success": True,
        "old_credits": old_credits,
        "new_credits": user.credits,
        "adjustment": adjustment.amount,
        "reason": adjustment.reason
    }


# ============================================================================
# AI MODEL MANAGEMENT
# ============================================================================

@router.get("/ai-models")
async def get_ai_models(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all AI models with pricing"""
    
    models = db.query(AIModelPricing).order_by(AIModelPricing.provider, AIModelPricing.model_key).all()
    
    return {
        "models": [
            {
                "id": m.id,
                "model_key": m.model_key,
                "model_name": m.model_name,
                "provider": m.provider,
                "credit_multiplier": m.credit_multiplier,
                "cost_per_1k_chars": m.cost_per_1k_chars,
                "description": m.description,
                "is_active": m.is_active,
                "is_default": m.is_default
            }
            for m in models
        ]
    }


@router.patch("/ai-models/{model_id}")
async def update_ai_model(
    model_id: int,
    update: AIModelUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update AI model settings"""
    
    model = db.query(AIModelPricing).filter(AIModelPricing.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="AI model not found")
    
    if update.is_active is not None:
        model.is_active = update.is_active
    if update.credit_multiplier is not None:
        model.credit_multiplier = update.credit_multiplier
    if update.cost_per_1k_chars is not None:
        model.cost_per_1k_chars = update.cost_per_1k_chars
    if update.is_default is not None:
        if update.is_default:
            # Clear other defaults for same provider
            db.query(AIModelPricing).filter(
                AIModelPricing.provider == model.provider,
                AIModelPricing.id != model_id
            ).update({"is_default": False})
        model.is_default = update.is_default
    
    db.commit()
    db.refresh(model)
    
    logger.info(f"✅ Admin {admin.username} updated AI model {model.model_key}")
    
    return {"success": True, "model": {
        "id": model.id,
        "model_key": model.model_key,
        "is_active": model.is_active,
        "credit_multiplier": model.credit_multiplier,
        "cost_per_1k_chars": model.cost_per_1k_chars,
        "is_default": model.is_default
    }}


# ============================================================================
# CREDIT PRICING MANAGEMENT
# ============================================================================

@router.get("/pricing")
async def get_pricing_configs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all pricing configurations"""
    
    configs = db.query(CreditPricingConfig).order_by(CreditPricingConfig.operation_key).all()
    
    return {
        "pricing": [
            {
                "id": c.id,
                "operation_key": c.operation_key,
                "operation_name": c.operation_name,
                "cost_per_unit": c.cost_per_unit,
                "unit_description": c.unit_description,
                "description": c.description,
                "is_active": c.is_active
            }
            for c in configs
        ]
    }


@router.patch("/pricing/{pricing_id}")
async def update_pricing(
    pricing_id: int,
    update: PricingUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update pricing configuration"""
    
    config = db.query(CreditPricingConfig).filter(CreditPricingConfig.id == pricing_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Pricing config not found")
    
    if update.cost_per_unit is not None:
        config.cost_per_unit = update.cost_per_unit
    if update.is_active is not None:
        config.is_active = update.is_active
    if update.description is not None:
        config.description = update.description
    
    db.commit()
    db.refresh(config)
    
    logger.info(f"✅ Admin {admin.username} updated pricing {config.operation_key}")
    
    return {"success": True, "pricing": {
        "id": config.id,
        "operation_key": config.operation_key,
        "cost_per_unit": config.cost_per_unit,
        "is_active": config.is_active
    }}


# ============================================================================
# SYSTEM CONFIGURATION
# ============================================================================

@router.get("/system/config")
async def get_system_config(
    admin: User = Depends(require_admin)
):
    """Get current system configuration"""
    
    return {
        "transcription": {
            "use_assemblyai": settings.USE_ASSEMBLYAI,
            "use_faster_whisper": settings.USE_FASTER_WHISPER,
            "use_modal": settings.USE_MODAL,
            "use_runpod": settings.USE_RUNPOD,
            "assemblyai_configured": bool(settings.ASSEMBLYAI_API_KEY),
            "modal_configured": bool(settings.MODAL_API_TOKEN)
        },
        "ai_enhancement": {
            "gemini_configured": bool(settings.GEMINI_API_KEY),
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "groq_configured": bool(settings.GROQ_API_KEY) if hasattr(settings, 'GROQ_API_KEY') else False,
            "together_configured": bool(settings.TOGETHER_API_KEY) if hasattr(settings, 'TOGETHER_API_KEY') else False
        },
        "image_generation": {
            "modal_configured": bool(settings.MODAL_API_TOKEN),
            "replicate_configured": bool(settings.REPLICATE_API_TOKEN)
        },
        "storage": {
            "r2_configured": bool(settings.STORAGE_ACCESS_KEY),
            "bucket": settings.STORAGE_BUCKET
        }
    }


@router.get("/system/health")
async def get_system_health(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Check system health status"""
    
    health = {
        "database": False,
        "redis": False,
        "storage": False
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health["database"] = True
    except:
        pass
    
    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health["redis"] = True
    except:
        pass
    
    # Check R2/Storage
    try:
        from app.services.storage import get_storage_service
        storage = get_storage_service()
        health["storage"] = storage.r2_enabled
    except:
        pass
    
    return {
        "status": "healthy" if all(health.values()) else "degraded",
        "components": health,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# RECENT ACTIVITY
# ============================================================================

@router.get("/activity/recent")
async def get_recent_activity(
    limit: int = 20,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get recent system activity"""
    
    # Recent transcriptions
    recent_transcriptions = db.query(Transcription).order_by(
        desc(Transcription.created_at)
    ).limit(limit).all()
    
    # Recent credit transactions
    recent_transactions = db.query(CreditTransaction).order_by(
        desc(CreditTransaction.created_at)
    ).limit(limit).all()
    
    return {
        "transcriptions": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "filename": t.filename,
                "status": t.status,
                "created_at": t.created_at
            }
            for t in recent_transcriptions
        ],
        "transactions": [
            {
                "id": t.id,
                "user_id": t.user_id,
                "amount": t.amount,
                "operation_type": t.operation_type,
                "created_at": t.created_at
            }
            for t in recent_transactions
        ]
    }
