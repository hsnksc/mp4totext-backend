"""
Admin API endpoints for system configuration
Only accessible by admin users
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth.utils import get_current_user
from app.models.user import User
from app.settings import get_settings
from app.services.runpod_service import get_runpod_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
settings = get_settings()


class TranscriptionProviderSettings(BaseModel):
    """Transcription provider configuration"""
    provider: str  # "local", "runpod", or "modal"
    
    # RunPod settings (optional)
    runpod_api_key: str | None = None
    runpod_endpoint_id: str | None = None
    runpod_timeout: int = 300
    
    # Modal settings (optional)
    modal_api_token: str | None = None
    modal_function_name: str = "transcribe"


class ProviderStatus(BaseModel):
    """Status of a single provider"""
    name: str
    enabled: bool
    configured: bool
    healthy: bool | None = None
    description: str


class TranscriptionProviderResponse(BaseModel):
    """Current transcription provider settings"""
    current_provider: str  # "local", "runpod", or "modal"
    providers: list[ProviderStatus]


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to require admin role"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/transcription-provider", response_model=TranscriptionProviderResponse)
async def get_transcription_provider(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get current transcription provider settings and status
    
    Returns all available providers with their configuration and health status
    """
    providers = []
    
    # Local provider (always available)
    providers.append(ProviderStatus(
        name="local",
        enabled=not settings.USE_RUNPOD and not settings.USE_MODAL,
        configured=True,
        healthy=True,
        description="Local Faster-Whisper (CPU/GPU) - No external costs, runs on your machine"
    ))
    
    # RunPod provider
    runpod_configured = bool(settings.RUNPOD_API_KEY and settings.RUNPOD_ENDPOINT_ID)
    runpod_healthy = None
    if runpod_configured and settings.USE_RUNPOD:
        try:
            runpod_service = get_runpod_service()
            health = runpod_service.health_check()
            runpod_healthy = health.get("status") == "healthy"
        except Exception as e:
            logger.error(f"RunPod health check failed: {e}")
            runpod_healthy = False
    
    providers.append(ProviderStatus(
        name="runpod",
        enabled=settings.USE_RUNPOD,
        configured=runpod_configured,
        healthy=runpod_healthy,
        description="RunPod Serverless - Cloud GPU, pay per second (~$0.00045/sec)"
    ))
    
    # Modal provider
    modal_configured = bool(settings.MODAL_API_TOKEN)
    modal_healthy = None
    if modal_configured and settings.USE_MODAL:
        try:
            # Simple health check - Modal is healthy if credentials are set
            modal_healthy = True
        except Exception as e:
            logger.error(f"Modal check failed: {e}")
            modal_healthy = False
    
    providers.append(ProviderStatus(
        name="modal",
        enabled=settings.USE_MODAL,
        configured=modal_configured,
        healthy=modal_healthy,
        description="Modal Labs - Serverless GPU, $30 free credits/month, fast deployment"
    ))
    
    # Determine current provider
    if settings.USE_MODAL:
        current_provider = "modal"
    elif settings.USE_RUNPOD:
        current_provider = "runpod"
    else:
        current_provider = "local"
    
    return TranscriptionProviderResponse(
        current_provider=current_provider,
        providers=providers
    )


@router.post("/transcription-provider")
async def update_transcription_provider(
    settings_data: TranscriptionProviderSettings,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update transcription provider settings
    
    This endpoint updates the .env file with new settings.
    Requires server restart to take effect.
    
    Args:
        settings_data: New transcription provider settings
        
    Returns:
        Success message with restart reminder
    """
    import os
    from pathlib import Path
    from dotenv import set_key
    
    try:
        # Get .env file path
        env_path = Path(__file__).parent.parent.parent / ".env"
        
        if not env_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=".env file not found"
            )
        
        # Validate provider
        if settings_data.provider not in ["local", "runpod", "modal"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {settings_data.provider}. Must be 'local', 'runpod', or 'modal'"
            )
        
        # Update provider flags
        use_runpod = settings_data.provider == "runpod"
        use_modal = settings_data.provider == "modal"
        
        set_key(env_path, "USE_RUNPOD", str(use_runpod).lower())
        set_key(env_path, "USE_MODAL", str(use_modal).lower())
        logger.info(f"✅ Updated provider to: {settings_data.provider}")
        
        # Update RunPod credentials if provided
        if settings_data.provider == "runpod":
            if settings_data.runpod_api_key:
                set_key(env_path, "RUNPOD_API_KEY", settings_data.runpod_api_key)
                logger.info("✅ Updated RUNPOD_API_KEY")
            
            if settings_data.runpod_endpoint_id:
                set_key(env_path, "RUNPOD_ENDPOINT_ID", settings_data.runpod_endpoint_id)
                logger.info("✅ Updated RUNPOD_ENDPOINT_ID")
            
            if settings_data.runpod_timeout:
                set_key(env_path, "RUNPOD_TIMEOUT", str(settings_data.runpod_timeout))
                logger.info(f"✅ Updated RUNPOD_TIMEOUT to: {settings_data.runpod_timeout}")
        
        # Update Modal credentials if provided
        if settings_data.provider == "modal":
            if settings_data.modal_api_token:
                set_key(env_path, "MODAL_API_TOKEN", settings_data.modal_api_token)
                logger.info("✅ Updated MODAL_API_TOKEN")
            
            if settings_data.modal_function_name:
                set_key(env_path, "MODAL_FUNCTION_NAME", settings_data.modal_function_name)
                logger.info(f"✅ Updated MODAL_FUNCTION_NAME to: {settings_data.modal_function_name}")
        
        # Test provider connection if not local
        if settings_data.provider == "runpod":
            try:
                # Temporarily update settings for testing
                settings.USE_RUNPOD = True
                if settings_data.runpod_api_key:
                    settings.RUNPOD_API_KEY = settings_data.runpod_api_key
                if settings_data.runpod_endpoint_id:
                    settings.RUNPOD_ENDPOINT_ID = settings_data.runpod_endpoint_id
                
                runpod_service = get_runpod_service()
                health = runpod_service.health_check()
                
                if health.get("status") != "healthy":
                    logger.warning(f"⚠️ RunPod health check warning: {health}")
                else:
                    logger.info("✅ RunPod endpoint is healthy")
                    
            except Exception as e:
                logger.error(f"❌ RunPod connection test failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"RunPod connection test failed: {str(e)}"
                )
        
        elif settings_data.provider == "modal":
            # Modal validation - check credentials are set
            if not settings_data.modal_api_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Modal API token is required"
                )
            logger.info("✅ Modal credentials validated")
        
        return {
            "success": True,
            "message": "Transcription provider settings updated successfully",
            "provider": settings_data.provider,
            "restart_required": True,
            "note": "Please restart the backend and Celery workers for changes to take effect"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update transcription provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.get("/runpod/health")
async def check_runpod_health(
    admin: User = Depends(require_admin)
):
    """
    Check RunPod endpoint health status
    
    Returns detailed health information from RunPod API
    """
    if not settings.USE_RUNPOD:
        return {
            "enabled": False,
            "message": "RunPod is not enabled"
        }
    
    if not settings.RUNPOD_API_KEY or not settings.RUNPOD_ENDPOINT_ID:
        return {
            "enabled": True,
            "configured": False,
            "message": "RunPod credentials not configured"
        }
    
    try:
        runpod_service = get_runpod_service()
        health = runpod_service.health_check()
        
        return {
            "enabled": True,
            "configured": True,
            "status": health.get("status"),
            "data": health.get("data"),
            "error": health.get("error")
        }
        
    except Exception as e:
        logger.error(f"RunPod health check failed: {e}")
        return {
            "enabled": True,
            "configured": True,
            "status": "error",
            "error": str(e)
        }
