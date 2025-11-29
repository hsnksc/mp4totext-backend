"""
Credit API endpoints - User credit management
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.api.auth import get_current_active_user, require_superuser
from app.models.user import User
from app.models.credit_transaction import CreditTransaction, OperationType
from app.services.credit_service import get_credit_service, InsufficientCreditsError, CreditPricing
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/credits", tags=["credits"])


# Pydantic schemas
class CreditBalance(BaseModel):
    credits: float
    user_id: int
    username: str

    class Config:
        from_attributes = True


class CreditTransactionResponse(BaseModel):
    id: int
    amount: float
    operation_type: str
    description: str | None
    transcription_id: int | None
    balance_after: float
    created_at: datetime
    extra_info: str | None  # JSON string with character_count, duration_seconds, model_key, etc.

    class Config:
        from_attributes = True


class CreditHistoryResponse(BaseModel):
    transactions: List[CreditTransactionResponse]
    total_earned: float
    total_spent: float
    current_balance: float


class CreditPurchaseRequest(BaseModel):
    package: str  # "basic" | "pro" | "enterprise" | "custom"
    amount: float | None = None  # For custom amount


class CreditPricingResponse(BaseModel):
    transcription_per_minute: float
    speaker_recognition_per_minute: float
    youtube_download: float
    ai_enhancement: float
    lecture_notes: float
    custom_prompt: float
    exam_questions: float
    translation: float
    tavily_web_search: float
    assemblyai_speech_understanding_per_minute: float
    assemblyai_llm_gateway: float


class AIModelPricingResponse(BaseModel):
    """AI Model Pricing Response Schema"""
    id: int
    model_key: str
    model_name: str
    provider: str
    credit_multiplier: float
    description: str | None
    api_cost_per_1m_input: float | None
    api_cost_per_1m_output: float | None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class AIModelPricingUpdate(BaseModel):
    """AI Model Pricing Update Schema (admin only)"""
    credit_multiplier: float | None = None
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None


@router.get("/balance", response_model=CreditBalance)
async def get_credit_balance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's credit balance
    """
    credit_service = get_credit_service(db)
    balance = credit_service.get_balance(current_user.id)
    
    return CreditBalance(
        credits=balance,
        user_id=current_user.id,
        username=current_user.username
    )


@router.get("/history", response_model=CreditHistoryResponse)
async def get_credit_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's credit transaction history
    """
    credit_service = get_credit_service(db)
    transactions = credit_service.get_transaction_history(
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    # Calculate totals
    total_earned = sum(t.amount for t in transactions if t.amount > 0)
    total_spent = abs(sum(t.amount for t in transactions if t.amount < 0))
    current_balance = credit_service.get_balance(current_user.id)
    
    return CreditHistoryResponse(
        transactions=[
            CreditTransactionResponse(
                id=t.id,
                amount=t.amount,
                operation_type=t.operation_type.value,
                description=t.description,
                transcription_id=t.transcription_id,
                balance_after=t.balance_after,
                created_at=t.created_at,
                extra_info=t.extra_info  # Include metadata with character counts, model keys, etc.
            )
            for t in transactions
        ],
        total_earned=total_earned,
        total_spent=total_spent,
        current_balance=current_balance
    )


@router.get("/transactions/transcription/{transcription_id}", response_model=List[CreditTransactionResponse])
async def get_transcription_transactions(
    transcription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all credit transactions for a specific transcription
    
    Returns transactions for:
    - Initial transcription
    - AI enhancements
    - Video generation
    - Image generation
    - Custom prompts
    - Translations
    - etc.
    """
    credit_service = get_credit_service(db)
    
    # Get all transactions for this transcription
    transactions = db.query(CreditTransaction).filter(
        CreditTransaction.user_id == current_user.id,
        CreditTransaction.transcription_id == transcription_id
    ).order_by(CreditTransaction.created_at.desc()).all()
    
    logger.info(f"📊 Found {len(transactions)} credit transactions for transcription {transcription_id}")
    
    return [
        CreditTransactionResponse(
            id=t.id,
            amount=t.amount,
            operation_type=t.operation_type.value,
            description=t.description,
            transcription_id=t.transcription_id,
            balance_after=t.balance_after,
            created_at=t.created_at,
            extra_info=t.extra_info
        )
        for t in transactions
    ]


@router.get("/pricing", response_model=CreditPricingResponse)
async def get_credit_pricing(db: Session = Depends(get_db)):
    """
    Get current credit pricing information (from database)
    """
    credit_service = get_credit_service(db)
    pricing = credit_service.pricing
    
    return CreditPricingResponse(
        transcription_per_minute=pricing.TRANSCRIPTION_BASE,
        speaker_recognition_per_minute=pricing.SPEAKER_RECOGNITION,
        youtube_download=pricing.YOUTUBE_DOWNLOAD,
        ai_enhancement=pricing.AI_ENHANCEMENT,
        lecture_notes=pricing.LECTURE_NOTES,
        custom_prompt=pricing.CUSTOM_PROMPT,
        exam_questions=pricing.EXAM_QUESTIONS,
        translation=pricing.TRANSLATION,
        tavily_web_search=pricing.TAVILY_WEB_SEARCH,
        assemblyai_speech_understanding_per_minute=pricing.ASSEMBLYAI_SPEECH_UNDERSTANDING_PER_MINUTE,
        assemblyai_llm_gateway=pricing.ASSEMBLYAI_LLM_GATEWAY
    )


@router.post("/purchase")
async def purchase_credits(
    request: CreditPurchaseRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Purchase credit package (placeholder - integrate with payment gateway later)
    
    Packages:
    - basic: 500 credits / $10
    - pro: 2000 credits / $30
    - enterprise: 10000 credits / $100
    - custom: specify amount
    """
    credit_service = get_credit_service(db)
    
    # Package definitions
    packages = {
        "basic": {"credits": 500, "price": 10},
        "pro": {"credits": 2000, "price": 30},
        "enterprise": {"credits": 10000, "price": 100}
    }
    
    if request.package == "custom":
        if not request.amount or request.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom amount must be positive"
            )
        credits_to_add = request.amount
        price = credits_to_add / 50  # 50 credits per $1
    elif request.package in packages:
        package = packages[request.package]
        credits_to_add = package["credits"]
        price = package["price"]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid package: {request.package}"
        )
    
    # TODO: Integrate with payment gateway (Stripe, PayPal, etc.)
    # For now, this is a placeholder that simulates successful payment
    logger.warning(f"⚠️ DEMO MODE: Simulating credit purchase for user {current_user.id}")
    
    transaction = credit_service.add_credits(
        user_id=current_user.id,
        amount=credits_to_add,
        operation_type=OperationType.PURCHASE,
        description=f"Purchased {request.package} package ({credits_to_add} credits for ${price})",
        metadata={
            "package": request.package,
            "price_usd": price,
            "payment_method": "demo"  # TODO: Replace with actual payment method
        }
    )
    
    return {
        "success": True,
        "credits_added": credits_to_add,
        "new_balance": transaction.balance_after,
        "transaction_id": transaction.id,
        "message": f"Successfully purchased {credits_to_add} credits!",
        "note": "⚠️ DEMO MODE: No actual payment processed"
    }


@router.post("/admin/add")
async def admin_add_credits(
    user_id: int,
    amount: float,
    reason: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to add credits to any user
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can add credits"
        )
    
    credit_service = get_credit_service(db)
    
    transaction = credit_service.add_credits(
        user_id=user_id,
        amount=amount,
        operation_type=OperationType.ADMIN_ADJUSTMENT,
        description=f"Admin adjustment: {reason}",
        metadata={"admin_user_id": current_user.id}
    )
    
    logger.info(f"👮 Admin {current_user.username} added {amount} credits to user {user_id}")
    
    return {
        "success": True,
        "credits_added": amount,
        "new_balance": transaction.balance_after,
        "transaction_id": transaction.id
    }


# =============================================================================
# ADMIN PRICING MANAGEMENT
# =============================================================================

class PricingConfigResponse(BaseModel):
    """Pricing configuration response schema"""
    id: int
    operation_key: str
    operation_name: str
    cost_per_unit: float
    unit_description: str
    description: str | None
    is_active: bool

    class Config:
        from_attributes = True


class PricingConfigUpdate(BaseModel):
    """Schema for bulk pricing update"""
    configs: dict[str, float]  # {operation_key: new_cost}


@router.get("/admin/pricing", response_model=List[PricingConfigResponse])
async def get_pricing_configs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Get all pricing configurations
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view pricing configurations"
        )
    
    from app.models.credit_pricing import CreditPricingConfig
    
    configs = db.query(CreditPricingConfig).order_by(CreditPricingConfig.id).all()
    
    logger.info(f"👮 Admin {current_user.username} fetched pricing configs")
    
    return configs


@router.put("/admin/pricing")
async def update_pricing_configs(
    pricing_update: PricingConfigUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint: Bulk update pricing configurations
    Request body: {"configs": {"transcription_base": 15, "ai_enhancement": 25}}
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update pricing"
        )
    
    from app.models.credit_pricing import CreditPricingConfig
    
    updated_configs = []
    errors = []
    
    for operation_key, new_cost in pricing_update.configs.items():
        # Validate cost
        if new_cost < 0:
            errors.append(f"{operation_key}: Cost cannot be negative")
            continue
        
        # Find and update config
        config = db.query(CreditPricingConfig).filter_by(operation_key=operation_key).first()
        
        if not config:
            errors.append(f"{operation_key}: Configuration not found")
            continue
        
        old_cost = config.cost_per_unit
        config.cost_per_unit = new_cost
        updated_configs.append({
            "operation_key": operation_key,
            "operation_name": config.operation_name,
            "old_cost": old_cost,
            "new_cost": new_cost
        })
        
        logger.info(f"👮 Admin {current_user.username} updated {operation_key}: {old_cost} → {new_cost} credits")
    
    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Some updates failed", "errors": errors}
        )
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update pricing configurations"
        )
    
    return {
        "success": True,
        "updated_count": len(updated_configs),
        "updates": updated_configs,
        "message": f"Successfully updated {len(updated_configs)} pricing configuration(s)"
    }


# ============================================================================
# AI MODEL PRICING ENDPOINTS
# ============================================================================

@router.get("/models/active", response_model=List[AIModelPricingResponse])
async def get_active_models(
    db: Session = Depends(get_db)
):
    """
    Get all active AI models with pricing information (PUBLIC)
    
    Returns list of available models sorted by credit multiplier (cheapest first)
    """
    from app.models.ai_model_pricing import AIModelPricing
    
    try:
        models = db.query(AIModelPricing).filter(
            AIModelPricing.is_active == True
        ).order_by(AIModelPricing.credit_multiplier).all()
        
        logger.info(f"📋 Returning {len(models)} active AI models")
        return models
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch active models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch active models"
        )


@router.get("/admin/models", response_model=List[AIModelPricingResponse])
async def get_all_models_admin(
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """
    Get all AI models (including inactive) - ADMIN ONLY
    
    Returns complete list of models sorted by provider and multiplier
    """
    from app.models.ai_model_pricing import AIModelPricing
    
    try:
        models = db.query(AIModelPricing).order_by(
            AIModelPricing.provider,
            AIModelPricing.credit_multiplier
        ).all()
        
        logger.info(f"👮 Admin {current_user.username} fetched all {len(models)} AI models")
        return models
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch models"
        )


@router.put("/admin/models/{model_id}", response_model=AIModelPricingResponse)
async def update_model_pricing_admin(
    model_id: int,
    update_data: AIModelPricingUpdate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """
    Update AI model pricing configuration - ADMIN ONLY
    
    Allows updating:
    - credit_multiplier: Cost multiplier (e.g., 1.0, 2.5, 0.5)
    - description: User-facing model description
    - is_active: Enable/disable model
    - is_default: Set as default model (will unset other defaults)
    """
    from app.models.ai_model_pricing import AIModelPricing
    
    try:
        # Find model
        model = db.query(AIModelPricing).filter(AIModelPricing.id == model_id).first()
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI model with id {model_id} not found"
            )
        
        # Store old values for logging
        old_values = {
            "multiplier": model.credit_multiplier,
            "is_active": model.is_active,
            "is_default": model.is_default
        }
        
        # Update fields
        if update_data.credit_multiplier is not None:
            model.credit_multiplier = update_data.credit_multiplier
        
        if update_data.description is not None:
            model.description = update_data.description
        
        if update_data.is_active is not None:
            model.is_active = update_data.is_active
        
        if update_data.is_default is not None and update_data.is_default:
            # Unset all other defaults first
            db.query(AIModelPricing).update({"is_default": False})
            model.is_default = True
        
        model.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(model)
        
        logger.info(
            f"👮 Admin {current_user.username} updated model {model.model_name}: "
            f"multiplier {old_values['multiplier']} → {model.credit_multiplier}, "
            f"active {old_values['is_active']} → {model.is_active}, "
            f"default {old_values['is_default']} → {model.is_default}"
        )
        
        return model
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to update model {model_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update model: {str(e)}"
        )


# Schema for creating new AI model
class AIModelCreate(BaseModel):
    model_key: str
    model_name: str
    provider: str  # gemini, together, groq, openai
    credit_multiplier: float = 1.0
    api_cost_per_1m_input: Optional[float] = None
    api_cost_per_1m_output: Optional[float] = None
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False


@router.post("/admin/models", response_model=AIModelPricingResponse)
async def create_model_admin(
    model_data: AIModelCreate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """
    Create a new AI model - ADMIN ONLY
    """
    from app.models.ai_model_pricing import AIModelPricing
    
    try:
        # Check if model_key already exists
        existing = db.query(AIModelPricing).filter(
            AIModelPricing.model_key == model_data.model_key
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model with key '{model_data.model_key}' already exists"
            )
        
        # If setting as default, unset others
        if model_data.is_default:
            db.query(AIModelPricing).update({"is_default": False})
        
        new_model = AIModelPricing(
            model_key=model_data.model_key,
            model_name=model_data.model_name,
            provider=model_data.provider,
            credit_multiplier=model_data.credit_multiplier,
            api_cost_per_1m_input=model_data.api_cost_per_1m_input,
            api_cost_per_1m_output=model_data.api_cost_per_1m_output,
            description=model_data.description,
            is_active=model_data.is_active,
            is_default=model_data.is_default
        )
        
        db.add(new_model)
        db.commit()
        db.refresh(new_model)
        
        logger.info(f"👮 Admin {current_user.username} created model: {new_model.model_name}")
        return new_model
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to create model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create model: {str(e)}"
        )


class BulkModelCreate(BaseModel):
    models: List[AIModelCreate]


@router.post("/admin/models/bulk")
async def bulk_create_models_admin(
    data: BulkModelCreate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """
    Bulk create AI models - ADMIN ONLY
    Skips existing models (by model_key)
    """
    from app.models.ai_model_pricing import AIModelPricing
    
    try:
        created = 0
        skipped = 0
        errors = []
        
        for model_data in data.models:
            # Check if exists
            existing = db.query(AIModelPricing).filter(
                AIModelPricing.model_key == model_data.model_key
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            try:
                new_model = AIModelPricing(
                    model_key=model_data.model_key,
                    model_name=model_data.model_name,
                    provider=model_data.provider,
                    credit_multiplier=model_data.credit_multiplier,
                    api_cost_per_1m_input=model_data.api_cost_per_1m_input,
                    api_cost_per_1m_output=model_data.api_cost_per_1m_output,
                    description=model_data.description,
                    is_active=model_data.is_active,
                    is_default=False  # Don't set default in bulk
                )
                db.add(new_model)
                created += 1
            except Exception as e:
                errors.append(f"{model_data.model_key}: {str(e)}")
        
        db.commit()
        
        logger.info(f"👮 Admin {current_user.username} bulk created {created} models, skipped {skipped}")
        
        return {
            "success": True,
            "created": created,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Bulk create failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk create failed: {str(e)}"
        )
