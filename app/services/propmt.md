PHASE 1: CRITICAL ROUTING FIX (Priority: 🔴 URGENT)
Task 1.1: Worker Provider Selection Fix
File: mp4totext-backend/app/workers/transcription_worker.py
Location: Satır ~450 civarı, AI enhancement bölümünde
Current Code:
pythonif transcription_options.get("ai_enhancement"):
    try:
        gemini_service = get_gemini_service()  # ❌ PROBLEM: Kullanıcı seçimini ignore ediyor
        
        result = await gemini_service.enhance_text(
            cleaned_text,
            language=language,
            include_summary=True,
            enable_web_search=transcription_options.get("enable_web_search", False)
        )
New Code:
pythonif transcription_options.get("ai_enhancement"):
    # 🔧 FIX 1: Extract user-selected provider and model
    ai_provider = transcription_options.get("ai_provider", "gemini")
    ai_model = transcription_options.get("ai_model", None)
    
    logger.info(f"🤖 User selected provider: {ai_provider}, model: {ai_model}")
    
    # 🔧 FIX 2: Create service instance with user selection
    from app.services.gemini_service import GeminiService
    gemini_service = GeminiService(
        preferred_provider=ai_provider,
        preferred_model=ai_model
    )
    
    # 🔧 FIX 3: Validate service is configured
    if not gemini_service.is_enabled():
        error_msg = f"Provider '{ai_provider}' is not configured. Check API key in settings."
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg)
    
    logger.info(f"✅ Service initialized: {gemini_service.provider} with {gemini_service.model_name}")
    
    try:
        result = await gemini_service.enhance_text(
            cleaned_text,
            language=language,
            include_summary=True,
            enable_web_search=transcription_options.get("enable_web_search", False)
        )
Expected Behavior After Fix:

✅ Log shows: "User selected provider: together, model: meta-llama/Llama-3.3-70B-Instruct-Turbo"
✅ Service uses correct provider (not default Gemini)
✅ If provider unconfigured, throws clear error message


Task 1.2: Model Validation Check
File: mp4totext-backend/app/workers/transcription_worker.py
Location: Right after Task 1.1 code, before gemini_service.enhance_text()
Add This Code:
python    # 🔧 FIX 4: Validate model exists and is active in database
    if ai_model:
        from app.models.ai_model_pricing import AIModelPricing
        db_model = db.query(AIModelPricing).filter_by(
            model_key=ai_model,
            is_active=True
        ).first()
        
        if not db_model:
            error_msg = f"Model '{ai_model}' is not active or not found in database"
            logger.error(f"❌ {error_msg}")
            logger.error(f"   Available models for {ai_provider}: Query database for active models")
            raise Exception(error_msg)
        
        logger.info(f"✅ Model validated: {ai_model}")
        logger.info(f"   Provider: {db_model.provider}")
        logger.info(f"   Credit multiplier: {db_model.credit_multiplier}")
    
    try:
        result = await gemini_service.enhance_text(...)
Expected Behavior:

✅ Checks if model exists in ai_model_pricing table
✅ Checks if is_active=True
✅ Blocks request if model unavailable
✅ Logs detailed validation info


Task 1.3: Comprehensive Error Handling & Logging
File: mp4totext-backend/app/workers/transcription_worker.py
Location: Exception handler for AI enhancement (satır ~500 civarı)
Current Code:
python    except Exception as e:
        logger.error(f"❌ Gemini enhancement failed: {e}")
        # Fallback to cleaned text
        enhanced_text = cleaned_text
        summary = ""
        additional_info = ""
New Code:
python    except Exception as e:
        logger.error(f"❌ AI enhancement failed: {e}")
        logger.error(f"   Provider: {ai_provider}")
        logger.error(f"   Model: {ai_model}")
        logger.error(f"   Error type: {type(e).__name__}")
        
        # 🔧 FIX 5: Extract error code if available
        error_code = "unknown"
        if hasattr(e, "status_code"):
            error_code = str(e.status_code)
        elif "404" in str(e):
            error_code = "404"
        elif "422" in str(e):
            error_code = "422"
        elif "401" in str(e) or "authentication" in str(e).lower():
            error_code = "401"
        elif "rate_limit" in str(e).lower():
            error_code = "429"
        
        logger.error(f"   Error code: {error_code}")
        
        # 🔧 FIX 6: Log to database for monitoring
        from app.models.ai_error_log import AIErrorLog
        try:
            error_log = AIErrorLog(
                transcription_id=transcription_id,
                provider=ai_provider,
                model_key=ai_model,
                operation="enhancement",
                error_code=error_code,
                error_message=str(e)[:1000],  # Limit length
                request_payload={
                    "text_length": len(cleaned_text),
                    "language": language,
                    "web_search_enabled": transcription_options.get("enable_web_search", False)
                }
            )
            db.add(error_log)
            db.commit()
            logger.info(f"✅ Error logged to database (ID: {error_log.id})")
        except Exception as log_error:
            logger.error(f"⚠️ Failed to log error to database: {log_error}")
        
        # 🔧 FIX 7: Update transcription with error flag
        transcription.ai_enhancement_error = True
        transcription.ai_error_message = str(e)[:500]  # Truncate for display
        transcription.ai_error_code = error_code
        db.commit()
        
        # 🔧 FIX 8: User-friendly error message in summary
        enhanced_text = cleaned_text
        summary = f"⚠️ AI Enhancement Failed: {str(e)[:200]}"
        additional_info = f"Error code: {error_code}. Please try a different model or contact support."
        
        logger.warning(f"⚠️ Falling back to cleaned text (no enhancement applied)")
Expected Behavior:

✅ Detailed error logging (provider, model, error type, error code)
✅ Error saved to ai_error_logs table for monitoring
✅ Transcription marked with ai_enhancement_error=True
✅ User sees error message in summary field
✅ Error code extracted for categorization (404, 422, 401, 429, unknown)


🗄️ PHASE 2: DATABASE SCHEMA UPDATE (Priority: 🔴 URGENT)
Task 2.1: Add Error Tracking Fields to Transcription Model
File: mp4totext-backend/app/models/transcription.py
Location: Inside Transcription class, after existing fields
Add These Fields:
pythonclass Transcription(Base):
    __tablename__ = "transcriptions"
    
    # ... existing fields (id, user_id, filename, etc.)
    
    # 🔧 NEW: AI Enhancement Error Tracking
    ai_enhancement_error = Column(Boolean, default=False, nullable=False, 
                                   comment="True if AI enhancement failed")
    ai_error_message = Column(Text, nullable=True, 
                              comment="User-friendly error message")
    ai_error_code = Column(String(50), nullable=True, 
                           comment="HTTP error code or error type (404, 422, etc.)")
    ai_error_timestamp = Column(DateTime, nullable=True, 
                                comment="When error occurred")
    
    # Relationship to error logs
    error_logs = relationship("AIErrorLog", back_populates="transcription")
Create Migration:
bash# Run in terminal
cd mp4totext-backend
alembic revision --autogenerate -m "add_ai_error_tracking_to_transcriptions"
alembic upgrade head
Expected Migration File Content:
python"""add_ai_error_tracking_to_transcriptions

Revision ID: xxxxx
Revises: yyyyy
Create Date: 2025-11-03 ...
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('transcriptions', sa.Column('ai_enhancement_error', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('transcriptions', sa.Column('ai_error_message', sa.Text(), nullable=True))
    op.add_column('transcriptions', sa.Column('ai_error_code', sa.String(length=50), nullable=True))
    op.add_column('transcriptions', sa.Column('ai_error_timestamp', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('transcriptions', 'ai_error_timestamp')
    op.drop_column('transcriptions', 'ai_error_code')
    op.drop_column('transcriptions', 'ai_error_message')
    op.drop_column('transcriptions', 'ai_enhancement_error')

Task 2.2: Create AIErrorLog Model
File: mp4totext-backend/app/models/ai_error_log.py (CREATE NEW FILE)
Full File Content:
python"""
AI Error Log Model
Tracks all AI provider errors for monitoring and debugging
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class AIErrorLog(Base):
    """
    Log table for AI provider errors
    
    Tracks every error that occurs during AI operations:
    - Text enhancement
    - Lecture notes generation
    - Custom prompts
    - Translations
    - Exam questions
    
    Used for:
    - Debugging
    - Model health monitoring
    - Auto-disable failing models
    - User support
    """
    __tablename__ = "ai_error_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Error details
    provider = Column(String(50), nullable=False, index=True, comment="openai, gemini, groq, together")
    model_key = Column(String(200), nullable=False, index=True, comment="Exact model identifier")
    operation = Column(String(100), nullable=False, index=True, comment="enhancement, lecture_notes, translation, etc.")
    error_code = Column(String(50), nullable=True, index=True, comment="HTTP code or error type")
    error_message = Column(Text, nullable=False, comment="Full error message")
    
    # Request context
    request_payload = Column(JSON, nullable=True, comment="Request parameters for debugging")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolved = Column(Boolean, default=False, comment="Admin marked as resolved")
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    transcription = relationship("Transcription", back_populates="error_logs")
    user = relationship("User", back_populates="ai_error_logs")
    
    def __repr__(self):
        return f"<AIErrorLog(id={self.id}, provider={self.provider}, model={self.model_key}, error={self.error_code})>"
Update User Model:
File: mp4totext-backend/app/models/user.py
Add Relationship:
pythonclass User(Base):
    # ... existing fields
    
    # Relationships
    transcriptions = relationship("Transcription", back_populates="user")
    ai_error_logs = relationship("AIErrorLog", back_populates="user")  # 🔧 ADD THIS
Create Migration:
bashalembic revision --autogenerate -m "create_ai_error_logs_table"
alembic upgrade head

Task 2.3: Update Transcription Schema (API Response)
File: mp4totext-backend/app/schemas/transcription.py
Location: Inside TranscriptionResponse class
Add Fields:
pythonclass TranscriptionResponse(BaseModel):
    id: int
    filename: str
    # ... existing fields
    
    # 🔧 NEW: Error tracking fields
    ai_enhancement_error: bool = False
    ai_error_message: Optional[str] = None
    ai_error_code: Optional[str] = None
    ai_error_timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True
Expected API Response:
json{
  "id": 123,
  "filename": "test.mp3",
  "status": "completed",
  "cleaned_text": "Original text...",
  "enhanced_text": "Original text...",
  "ai_enhancement_error": true,
  "ai_error_message": "Error code: 404 - Model not available",
  "ai_error_code": "404",
  "ai_error_timestamp": "2025-11-03T15:30:45Z"
}

🎨 PHASE 3: FRONTEND ERROR DISPLAY (Priority: 🟡 HIGH)
Task 3.1: Update TypeScript Interface
File: mp4totext-web/src/types/transcription.ts
Location: Inside Transcription interface
Add Fields:
typescriptexport interface Transcription {
  id: number;
  filename: string;
  // ... existing fields
  
  // 🔧 NEW: Error tracking
  ai_enhancement_error?: boolean;
  ai_error_message?: string;
  ai_error_code?: string;
  ai_error_timestamp?: string;
}

Task 3.2: Error Alert Component
File: mp4totext-web/src/pages/TranscriptionDetailPage.tsx
Location: Inside component, after header, before transcript content
Add Component:
tsx{/* 🔧 NEW: AI Enhancement Error Alert */}
{transcription.ai_enhancement_error && (
  <Alert 
    severity="error" 
    sx={{ mb: 3 }}
    action={
      <Button 
        color="inherit" 
        size="small"
        onClick={() => handleRetryEnhancement()}
      >
        🔄 Retry
      </Button>
    }
  >
    <AlertTitle>
      <Box display="flex" alignItems="center" gap={1}>
        <ErrorIcon />
        <Typography variant="h6">AI Enhancement Failed</Typography>
      </Box>
    </AlertTitle>
    
    <Box mt={2}>
      <Typography variant="body2" fontWeight="bold">
        Error Details:
      </Typography>
      <Typography variant="body2" sx={{ mt: 1 }}>
        {transcription.ai_error_message || 'Unknown error occurred'}
      </Typography>
      
      {transcription.ai_error_code && (
        <Chip 
          label={`Error Code: ${transcription.ai_error_code}`}
          size="small"
          color="error"
          sx={{ mt: 1 }}
        />
      )}
      
      <Box mt={2}>
        <Typography variant="body2" fontWeight="bold">
          Selected Configuration:
        </Typography>
        <Typography variant="body2">
          • Provider: {transcription.ai_provider || 'Unknown'}
        </Typography>
        <Typography variant="body2">
          • Model: {transcription.ai_model || 'Unknown'}
        </Typography>
      </Box>
      
      <Box mt={2}>
        <Typography variant="body2" color="text.secondary">
          💡 <strong>What to do:</strong>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          • Try a different AI model using the Retry button
        </Typography>
        <Typography variant="body2" color="text.secondary">
          • Check if your API key is configured correctly
        </Typography>
        <Typography variant="body2" color="text.secondary">
          • Contact support if the issue persists
        </Typography>
      </Box>
    </Box>
  </Alert>
)}

{/* 🔧 NEW: Silent Failure Detection Alert */}
{!transcription.ai_enhancement_error && 
 transcription.ai_enhancement && 
 transcription.enhanced_text === transcription.cleaned_text && (
  <Alert severity="warning" sx={{ mb: 3 }}>
    <AlertTitle>⚠️ No Changes Detected</AlertTitle>
    <Typography variant="body2">
      AI enhancement was requested, but the enhanced text is identical to the cleaned text.
      This may indicate:
    </Typography>
    <Box component="ul" sx={{ mt: 1, pl: 2 }}>
      <li>The text was already in perfect condition</li>
      <li>An error occurred but wasn't caught (please report this)</li>
      <li>The AI model made no improvements</li>
    </Box>
  </Alert>
)}
Add Retry Handler:
tsxconst handleRetryEnhancement = async () => {
  try {
    setRetrying(true);
    
    // Show model selection dialog
    const newModel = await showModelSelectionDialog();
    
    if (!newModel) return;
    
    // Call retry endpoint
    const response = await api.post(`/transcriptions/${transcription.id}/retry-enhancement`, {
      ai_provider: newModel.provider,
      ai_model: newModel.model_key
    });
    
    toast.success('✅ Enhancement retry started!');
    
    // Refresh transcription data
    setTimeout(() => {
      window.location.reload();
    }, 2000);
    
  } catch (error) {
    toast.error('Failed to retry enhancement');
    console.error(error);
  } finally {
    setRetrying(false);
  }
};

Task 3.3: Error Badge in Transcription List
File: mp4totext-web/src/pages/TranscriptionListPage.tsx
Location: Inside TranscriptionCard or list item component
Add Badge:
tsx<Card>
  <CardContent>
    <Box display="flex" justifyContent="space-between" alignItems="center">
      <Typography variant="h6">{transcription.filename}</Typography>
      
      {/* Status badges */}
      <Box display="flex" gap={1}>
        {transcription.ai_enhancement_error && (
          <Tooltip title={transcription.ai_error_message || 'AI enhancement failed'}>
            <Chip 
              icon={<ErrorIcon />}
              label="AI Error"
              color="error"
              size="small"
            />
          </Tooltip>
        )}
        
        <Chip 
          label={transcription.status}
          color={transcription.status === 'completed' ? 'success' : 'default'}
          size="small"
        />
      </Box>
    </Box>
  </CardContent>
</Card>

🔍 PHASE 4: MODEL VALIDATION API (Priority: 🟢 MEDIUM)
Task 4.1: Create Validation Endpoint
File: mp4totext-backend/app/api/credits.py
Location: Add new route after existing routes
Add Endpoint:
pythonfrom fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.ai_model_pricing import AIModelPricing
from app.config import get_settings
import requests
import logging
from typing import Dict, Any
from datetime import datetime
import redis

logger = logging.getLogger(__name__)
settings = get_settings()

# Redis cache for validation results (optional, but recommended)
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
except:
    redis_client = None
    logger.warning("Redis not available, validation caching disabled")


@router.post("/validate-model")
async def validate_model(
    provider: str,
    model_key: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Real-time model availability validation
    
    Checks:
    1. Model exists in database
    2. Model is active
    3. Model is available in provider API (cached 1 hour)
    
    Args:
        provider: AI provider (openai, gemini, groq, together)
        model_key: Model identifier
        
    Returns:
        {
            "available": bool,
            "reason": str (if unavailable),
            "max_tokens": int (if available),
            "context_length": int (if available),
            "last_checked": datetime
        }
    """
    
    logger.info(f"🔍 Validating model: {provider} / {model_key}")
    
    # Step 1: Check database
    db_model = db.query(AIModelPricing).filter_by(
        model_key=model_key,
        provider=provider
    ).first()
    
    if not db_model:
        logger.warning(f"❌ Model not found in database: {model_key}")
        return {
            "available": False,
            "reason": "Model not found in database",
            "suggestion": "Contact admin to add this model",
            "last_checked": datetime.utcnow().isoformat()
        }
    
    if not db_model.is_active:
        logger.warning(f"❌ Model is inactive: {model_key}")
        return {
            "available": False,
            "reason": f"Model is disabled: {db_model.removal_reason or 'No reason provided'}",
            "suggestion": "Choose a different model or contact admin",
            "last_checked": datetime.utcnow().isoformat()
        }
    
    # Step 2: Check API availability (cached)
    cache_key = f"model_validation:{provider}:{model_key}"
    
    # Try cache first
    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"✅ Using cached validation result for {model_key}")
                import json
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
    
    # Perform API check
    try:
        if provider == "together":
            result = await _validate_together_model(model_key, settings.TOGETHER_API_KEY)
        elif provider == "openai":
            result = await _validate_openai_model(model_key, settings.OPENAI_API_KEY)
        elif provider == "groq":
            result = await _validate_groq_model(model_key, settings.GROQ_API_KEY)
        elif provider == "gemini":
            result = await _validate_gemini_model(model_key, settings.GEMINI_API_KEY)
        else:
            result = {
                "available": False,
                "reason": f"Unknown provider: {provider}"
            }
        
        result["last_checked"] = datetime.utcnow().isoformat()
        
        # Cache result for 1 hour
        if redis_client and result.get("available"):
            try:
                import json
                redis_client.setex(cache_key, 3600, json.dumps(result))
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ API validation failed: {e}")
        return {
            "available": False,
            "reason": f"API check failed: {str(e)}",
            "last_checked": datetime.utcnow().isoformat()
        }


async def _validate_together_model(model_key: str, api_key: str) -> Dict[str, Any]:
    """Validate Together AI model availability"""
    try:
        response = requests.get(
            "https://api.together.xyz/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5
        )
        response.raise_for_status()
        
        available_models = response.json()
        model_info = next((m for m in available_models if m["id"] == model_key), None)
        
        if not model_info:
            return {
                "available": False,
                "reason": "Model not found in Together AI API",
                "suggestion": "Model may have been removed. Check https://api.together.ai/models"
            }
        
        return {
            "available": True,
            "max_tokens": model_info.get("max_tokens", 2048),
            "context_length": model_info.get("context_length", 4096),
            "model_info": {
                "display_name": model_info.get("display_name", model_key),
                "type": model_info.get("type", "unknown")
            }
        }
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Together AI API error: {str(e)}")


async def _validate_openai_model(model_key: str, api_key: str) -> Dict[str, Any]:
    """
    Validate OpenAI model availability
    Note: OpenAI doesn't have a public models endpoint, so we rely on known models
    """
    # Known OpenAI models (update this list as needed)
    KNOWN_MODELS = {
        "gpt-5-nano": {"max_tokens": 4096, "context": 128000},
        "gpt-5-mini": {"max_tokens": 4096, "context": 128000},
        "gpt-4.1-nano": {"max_tokens": 4096, "context": 128000},
        "gpt-4.1-mini": {"max_tokens": 4096, "context": 128000},
        "gpt-4o-mini": {"max_tokens": 16384, "context": 128000},
        "gpt-4o": {"max_tokens": 16384, "context": 128000},
        "gpt-4-turbo": {"max_tokens": 4096, "context": 128000},
        "gpt-4": {"max_tokens": 4096, "context": 8192},
        "o1-mini": {"max_tokens": 4096, "context": 128000},
        "o1-preview": {"max_tokens": 4096, "context": 128000},
    }
    
    if model_key in KNOWN_MODELS:
        return {
            "available": True,
            "max_tokens": KNOWN_MODELS[model_key]["max_tokens"],
            "context_length": KNOWN_MODELS[model_key]["context"]
        }
    else:
        # For unknown models, try a test request (costs money, so optional)
        return {
            "available": True,
            "max_tokens": 4096,
            "context_length": 8192,
            "note": "Model not in known list, assuming available"
        }


async def _validate_groq_model(model_key: str, api_key: str) -> Dict[str, Any]:
    """Validate Groq model availability"""
    try:
        response = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5
        )
        response.raise_for_status()
        
        available_models = response.json().get("data", [])
        model_info = next((m for m in available_models if m["id"] == model_key), None)
        
        if not model_info:
            return {
                "available": False,
                "reason": "Model not found in Groq API"
            }
        
        return {
            "available": True,
            "max_tokens": 8192,  # Groq default
            "context_length": 8192
        }
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Groq API error: {str(e)}")


async def _validate_gemini_model(model_key: str, api_key: str) -> Dict[str, Any]:
    """Validate Gemini model availability"""
    # Known Gemini models
    KNOWN_MODELS = {
        "gemini-2.0-flash-exp": {"max_tokens": 8192, "context": 1000000},
        "gemini-2.5-flash-exp": {"max_tokens": 8192, "context": 1000000},
        "gemini-1.5-pro": {"max_tokens": 8192, "context": 2000000},
        "gemini-1.5-flash": {"max_tokens": 8192, "context": 1000000},
        "gemini-pro": {"max_tokens": 8192, "context": 32000},
    }
    
    if model_key in KNOWN_MODELS:
        return {
            "available": True,
            "max_tokens": KNOWN_MODELS[model_key]["max_tokens"],
            "context_length": KNOWN_MODELS[model_key]["context"]
        }
    else:
        return {
            "available": True,
            "max_tokens": 8192,
            "context_length": 1000000,
            "note": "Model not in known list, assuming available"
        }

Task 4.2: Frontend Integration
File: mp4totext-web/src/pages/UploadPage.tsx
Location: Inside component, add validation logic
Add State:
tsxconst [validating, setValidating] = useState(false);
const [modelValidation, setModelValidation] = useState<{
  available: boolean;
  reason?: string;
  max_tokens?: number;
}>({ available: true });
Add Validation Handler:
tsxconst handleModelChange = async (modelKey: string) => {
  if (!aiProvider) {
    toast.error('Please select a provider first');
    return;
  }
  
  setValidating(true);
  setModelValidation({ available: true });
  
  try {
    // Call validation endpoint
    const response = await api.post('/credits/validate-model', {
      provider: aiProvider,
      model_key: modelKey
    });
    
    const validation = response.data;
    setModelValidation(validation);
    
    if (!validation.available) {
      toast.error(`❌ Model unavailable: ${validation.reason}`);
      // Don't set the model if unavailable
      return;
    }
    
    // Model is valid, set it
    setAiModel(modelKey);
    toast.success(`✅ Model validated: ${modelKey}`);
    
    // Optionally show token limits
    if (validation.max_tokens) {
      console.log(`Model supports up to ${validation.max_tokens} tokens`);
    }
    
  } catch (error) {
    console.error('Validation error:', error);
    toast.warning('Could not validate model, proceeding with caution');
    setAiModel(modelKey); // Allow selection even if validation fails
  } finally {
    setValidating(false);
  }
};
Update Model Selector:
tsx<FormControl fullWidth>
  <InputLabel>AI Model</InputLabel>
  <Select
    value={aiModel || ''}
    onChange={(e) => handleModelChange(e.target.value)}
    disabled={!aiProvider || validating}
  >
    {availableModels.map((model) => (
      <MenuItem key={model.model_key} value={model.model_key}>
        {model.model_name}
        {validating && <CircularProgress size={16} sx={{ ml: 1 }} />}
      </MenuItem>
    ))}
  </Select>
  
  {/* Validation feedback */}
  {!modelValidation.available && modelValidation.reason && (
    <FormHelperText error>
      ⚠️ {modelValidation.reason}
    </FormHelperText>
  )}
  
  {validating && (
    <FormHelperText>
      🔍 Checking model availability...
    </FormHelperText>
  )}
</FormControl>

📊 PHASE 5: MODEL HEALTH MONITORING (Priority: 🟢 LOW)
Task 5.1: Add Monitoring Fields to AIModelPricing
File: mp4totext-backend/app/models/ai_model_pricing.py
Location: Inside AIModelPricing class
Add Fields:
pythonclass AIModelPricing(Base):
    __tablename__ = "ai_model_pricing"
    
    # ... existing fields
    
    # 🔧 NEW: Performance Monitoring
    total_requests = Column(Integer, default=0, comment="Total API calls")
    total_errors = Column(Integer, default=0, comment="Total failed calls")
    error_rate = Column(Float, default=0.0, comment="Percentage: (errors/requests)*100")
    consecutive_errors = Column(Integer, default=0, comment="Current error streak")
    last_error_at = Column(DateTime, nullable=True, comment="Most recent error timestamp")
    
    # 🔧 NEW: Performance Metrics
    avg_response_time_ms = Column(Integer, nullable=True, comment="Average API response time")
    avg_tokens_per_request = Column(Integer, nullable=True, comment="Average token usage")
    
    # 🔧 NEW: API Information (from validation)
    max_tokens = Column(Integer, nullable=True, comment="Max output tokens from API")
    context_length = Column(Integer, nullable=True, comment="Max context window from API")
    last_availability_check = Column(DateTime, nullable=True, comment="Last validation check")
    is_api_available = Column(Boolean, default=True, comment="Current API availability status")
    api_check_error = Column(Text, nullable=True, comment="Last API check error message")
    
    # 🔧 NEW: Auto-Disable
    auto_disabled_at = Column(DateTime, nullable=True, comment="When auto-disabled")
    auto_disable_reason = Column(Text, nullable=True, comment="Why auto-disabled")
Create Migration:
bashalembic revision --autogenerate -m "add_model_monitoring_fields"
alembic upgrade head

Task 5.2: Usage Tracking in GeminiService
File: mp4totext-backend/app/services/gemini_service.py
Location: Inside enhance_text method (and other AI methods)
Wrap API Calls:
pythonasync def enhance_text(self, text: str, language: str = "tr", ...):
    # ... existing code
    
    import time
    start_time = time.time()
    
    try:
        # Existing enhancement code
        result = await self._enhance_single_text(text, language, ...)
        
        # 🔧 FIX: Track successful request
        response_time_ms = int((time.time() - start_time) * 1000)
        self._update_model_stats(
            success=True,
            response_time_ms=response_time_ms,
            tokens_used=result.get("word_count", 0)
        )
        
        return result
        
    except Exception as e:
        # 🔧 FIX: Track failed request
        response_time_ms = int((time.time() - start_time) * 1000)
        self._update_model_stats(
            success=False,
            error_message=str(e),
            response_time_ms=response_time_ms
        )
        
        # Check if model should be auto-disabled
        if self._should_auto_disable():
            self._auto_disable_model(reason=str(e))
        
        raise
Add Tracking Methods:
pythondef _update_model_stats(
    self,
    success: bool,
    response_time_ms: int = None,
    tokens_used: int = None,
    error_message: str = None
):
    """Update model performance statistics in database"""
    from app.database import SessionLocal
    from app.models.ai_model_pricing import AIModelPricing
    
    db = SessionLocal()
    try:
        model = db.query(AIModelPricing).filter_by(
            model_key=self.model_name,
            provider=self.provider
        ).first()
        
        if not model:
            logger.warning(f"⚠️ Model {self.model_name} not found in database")
            return
        
        # Update request count
        model.total_requests += 1
        
        if success:
            # Reset consecutive errors
            model.consecutive_errors = 0
            
            # Update average response time (exponential moving average)
            if response_time_ms and model.avg_response_time_ms:
                model.avg_response_time_ms = int(
                    model.avg_response_time_ms * 0.9 + response_time_ms * 0.1
                )
            elif response_time_ms:
                model.avg_response_time_ms = response_time_ms
            
            # Update average tokens
            if tokens_used and model.avg_tokens_per_request:
                model.avg_tokens_per_request = int(
                    model.avg_tokens_per_request * 0.9 + tokens_used * 0.1
                )
            elif tokens_used:
                model.avg_tokens_per_request = tokens_used
                
        else:
            # Update error count
            model.total_errors += 1
            model.consecutive_errors += 1
            model.last_error_at = datetime.utcnow()
            
            # Update error rate
            model.error_rate = (model.total_errors / model.total_requests) * 100
            
            logger.warning(f"⚠️ Model {self.model_name} error rate: {model.error_rate:.2f}%")
            logger.warning(f"   Consecutive errors: {model.consecutive_errors}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"❌ Failed to update model stats: {e}")
        db.rollback()
    finally:
        db.close()


def _should_auto_disable(self) -> bool:
    """Check if model should be automatically disabled"""
    from app.database import SessionLocal
    from app.models.ai_model_pricing import AIModelPricing
    
    db = SessionLocal()
    try:
        model = db.query(AIModelPricing).filter_by(
            model_key=self.model_name,
            provider=self.provider
        ).first()
        
        if not model:
            return False
        
        # Criteria for auto-disable:
        # 1. Error rate > 50% AND at least 10 requests
        # 2. OR consecutive errors >= 10
        
        if model.error_rate > 50 and model.total_requests >= 10:
            logger.warning(f"🚨 Model {self.model_name} has high error rate: {model.error_rate}%")
            return True
        
        if model.consecutive_errors >= 10:
            logger.warning(f"🚨 Model {self.model_name} has {model.consecutive_errors} consecutive errors")
            return True
        
        return False
        
    finally:
        db.close()


def _auto_disable_model(self, reason: str):
    """Automatically disable a failing model"""
    from app.database import SessionLocal
    from app.models.ai_model_pricing import AIModelPricing
    
    db = SessionLocal()
    try:
        model = db.query(AIModelPricing).filter_by(
            model_key=self.model_name,
            provider=self.provider
        ).first()
        
        if not model or not model.is_active:
            return
        
        # Disable model
        model.is_active = False
        model.auto_disabled_at = datetime.utcnow()
        model.auto_disable_reason = f"Auto-disabled due to high error rate ({model.error_rate:.2f}%). Last error: {reason[:200]}"
        
        db.commit()
        
        logger.error("=" * 80)
        logger.error(f"🚨 AUTO-DISABLED MODEL: {self.model_name}")
        logger.error(f"   Provider: {self.provider}")
        logger.error(f"   Error rate: {model.error_rate:.2f}%")
        logger.error(f"   Total requests: {model.total_requests}")
        logger.error(f"   Total errors: {model.total_errors}")
        logger.error(f"   Consecutive errors: {model.consecutive_errors}")
        logger.error(f"   Reason: {reason[:200]}")
        logger.error("=" * 80)
        
        # TODO: Send notification to admin (email, Slack, etc.)
        # await send_admin_notification(
        #     subject=f"Model Auto-Disabled: {self.model_name}",
        #     message=f"Model {self.model_name} was automatically disabled due to {model.error_rate}% error rate."
        # )
        
    except Exception as e:
        logger.error(f"❌ Failed to auto-disable model: {e}")
        db.rollback()
    finally:
        db.close()

🧪 TESTING PROCEDURES
Test 1: Provider Routing (After Phase 1)
Test Case: User selects Together AI + Llama 70B
Steps:
bash# 1. Start backend and worker
cd mp4totext-backend
celery -A app.workers.celery_app worker --loglevel=INFO

# 2. Upload file with specific provider
curl -X POST http://localhost:8000/api/v1/transcriptions/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.mp3" \
  -F 'transcription_options={"ai_enhancement":true,"ai_provider":"together","ai_model":"meta-llama/Llama-3.3-70B-Instruct-Turbo"}'

# 3. Check worker logs
```

**Expected Logs:**
```
🤖 User selected provider: together, model: meta-llama/Llama-3.3-70B-Instruct-Turbo
✅ Model validated: meta-llama/Llama-3.3-70B-Instruct-Turbo
   Provider: together
   Credit multiplier: 1.0
✅ Service initialized: together with meta-llama/Llama-3.3-70B-Instruct-Turbo
🚀 Calling Together AI (Llama 3.1 405B) for lecture notes...
✅ Together AI response received in 2.34 seconds
Expected Database:
sqlSELECT enhanced_text, summary, ai_provider, ai_model, ai_enhancement_error
FROM transcriptions
WHERE id = [new_transcription_id];

-- Should show:
-- enhanced_text: [different from cleaned_text]
-- summary: [actual summary]
-- ai_provider: 'together'
-- ai_model: 'meta-llama/Llama-3.3-70B-Instruct-Turbo'
-- ai_enhancement_error: false

Test 2: Model Not Found (404 Error)
Test Case: User selects unavailable model
Steps:
bash# Upload with model that doesn't exist in API
curl -X POST http://localhost:8000/api/v1/transcriptions/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.mp3" \
  -F 'transcription_options={"ai_enhancement":true,"ai_provider":"together","ai_model":"together-openai/gpt-oss-120b"}'
```

**Expected Logs:**
```
🤖 User selected provider: together, model: together-openai/gpt-oss-120b
❌ Model 'together-openai/gpt-oss-120b' is not active or not found in database
   Available models for together: Query database for active models
[ERROR] ❌ AI enhancement failed: Model 'together-openai/gpt-oss-120b' is not active or not found in database
✅ Error logged to database (ID: 123)
⚠️ Falling back to cleaned text (no enhancement applied)
Expected Database:
sqlSELECT ai_enhancement_error, ai_error_message, ai_error_code
FROM transcriptions
WHERE id = [new_transcription_id];

-- Should show:
-- ai_enhancement_error: true
-- ai_error_message: 'Model 'together-openai/gpt-oss-120b' is not active or not found in database'
-- ai_error_code: 'unknown'

SELECT * FROM ai_error_logs WHERE transcription_id = [new_transcription_id];
-- Should show error log entry
Expected Frontend:

Red error alert visible on detail page
Error message displayed
Model name and provider shown
Retry button present


Test 3: Model Validation API
Test Case: Validate model before upload
Steps:
bash# 1. Validate available model
curl -X POST http://localhost:8000/api/v1/credits/validate-model \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"together","model_key":"meta-llama/Llama-3.3-70B-Instruct-Turbo"}'

# 2. Validate unavailable model
curl -X POST http://localhost:8000/api/v1/credits/validate-model \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider":"together","model_key":"together-openai/gpt-oss-120b"}'
Expected Response (Available):
json{
  "available": true,
  "max_tokens": 6000,
  "context_length": 8192,
  "last_checked": "2025-11-03T15:30:00Z",
  "model_info": {
    "display_name": "Llama 3.3 70B Instruct Turbo",
    "type": "chat"
  }
}
Expected Response (Unavailable):
json{
  "available": false,
  "reason": "Model not found in Together AI API",
  "suggestion": "Model may have been removed. Check https://api.together.ai/models",
  "last_checked": "2025-11-03T15:30:00Z"
}
```

---

### Test 4: Frontend Error Display

**Test Case:** Error alert displays correctly

**Steps:**
1. Upload file with unavailable model
2. Wait for completion
3. Navigate to transcription detail page

**Expected UI:**
```
┌─────────────────────────────────────────────────────┐
│ ⚠️ AI Enhancement Failed                       [🔄 Retry] │
├─────────────────────────────────────────────────────┤
│ Error Details:                                      │
│ Model 'together-openai/gpt-oss-120b' is not active │
│                                                     │
│ [Error Code: unknown]                               │
│                                                     │
│ Selected Configuration:                             │
│ • Provider: together                                │
│ • Model: together-openai/gpt-oss-120b              │
│                                                     │
│ 💡 What to do:                                      │
│ • Try a different AI model using the Retry button   │
│ • Check if your API key is configured correctly     │
│ • Contact support if the issue persists             │
└─────────────────────────────────────────────────────┘

Test 5: Auto-Disable on High Error Rate
Test Case: Model auto-disables after 10 consecutive errors
Steps:
bash# 1. Manually trigger 10+ failures (use broken API key or unavailable model)
for i in {1..12}; do
  curl -X POST http://localhost:8000/api/v1/transcriptions/upload \
    -F "file=@test.mp3" \
    -F 'transcription_options={"ai_enhancement":true,"ai_provider":"together","ai_model":"broken-model"}'
  sleep 2
done

# 2. Check database
psql -d your_database -c "SELECT model_key, is_active, error_rate, consecutive_errors, auto_disabled_at, auto_disable_reason FROM ai_model_pricing WHERE model_key = 'broken-model';"
```

**Expected Database State:**
```
model_key     | is_active | error_rate | consecutive_errors | auto_disabled_at    | auto_disable_reason
--------------+-----------+------------+--------------------+---------------------+--------------------
broken-model  | false     | 100.00     | 12                 | 2025-11-03 15:35:00 | Auto-disabled due to high error rate (100.00%)...
```

**Expected Logs:**
```
⚠️ Model broken-model error rate: 50.00%
⚠️ Consecutive errors: 5
⚠️ Model broken-model error rate: 83.33%
⚠️ Consecutive errors: 10
🚨 Model broken-model has 10 consecutive errors
================================================================================
🚨 AUTO-DISABLED MODEL: broken-model
   Provider: together
   Error rate: 100.00%
   Total requests: 12
   Total errors: 12
   Consecutive errors: 12
   Reason: Model 'broken-model' is not active or not found in database
================================================================================
```

---

## 📋 FINAL CHECKLIST

### Phase 1: Routing Fix ✅
- [ ] Worker uses `transcription_options` to get provider/model
- [ ] Service created with `GeminiService(preferred_provider=..., preferred_model=...)`
- [ ] Model validated in database before use
- [ ] Errors logged to database (`ai_error_logs` table)
- [ ] Transcription marked with error flag
- [ ] Logs show correct provider (not "Calling Gemini" for Together AI)

### Phase 2: Database Schema ✅
- [ ] `transcriptions` table has error fields (`ai_enhancement_error`, `ai_error_message`, `ai_error_code`)
- [ ] `ai_error_logs` table created
- [ ] Migrations run successfully
- [ ] API response includes error fields

### Phase 3: Frontend Display ✅
- [ ] TypeScript interface updated
- [ ] Error alert component added
- [ ] Silent failure warning added
- [ ] Error badge in list view
- [ ] Retry functionality implemented

### Phase 4: Validation API ✅
- [ ] `/validate-model` endpoint created
- [ ] Provider-specific validation implemented (Together, OpenAI, Groq, Gemini)
- [ ] Redis caching configured (optional)
- [ ] Frontend calls validation on model change
- [ ] UI prevents selection of unavailable models

### Phase 5: Monitoring ✅
- [ ] `ai_model_pricing` has monitoring fields
- [ ] `_update_model_stats()` called after every API request
- [ ] `_should_auto_disable()` checks error rate
- [ ] `_auto_disable_model()` disables failing models
- [ ] Admin notification system planned (TODO)

---

## 🎯 SUCCESS CRITERIA

### Before Fix:
```
❌ User selects "Together AI + Llama 70B"
❌ System uses Gemini instead
❌ Model 404 error → Silent failure
❌ Frontend shows "AI Enhanced" but text unchanged
❌ User confused, credits wasted
❌ No error visibility
```

### After Fix:
```
✅ User selects "Together AI + Llama 70B"
✅ System validates model availability
✅ Service uses correct provider
✅ If error → Clear error message
✅ Frontend shows error alert with details
✅ User can retry with different model
✅ Admin can monitor model health
✅ Failing models auto-disable
✅ No credit charge on errors

🚀 DEPLOYMENT STEPS
Step 1: Database Migrations
bashcd mp4totext-backend

# Create all migrations
alembic revision --autogenerate -m "add_ai_error_tracking_to_transcriptions"
alembic revision --autogenerate -m "create_ai_error_logs_table"
alembic revision --autogenerate -m "add_model_monitoring_fields"

# Review migrations
cat alembic/versions/*_add_ai_error_tracking*.py
cat alembic/versions/*_create_ai_error_logs*.py
cat alembic/versions/*_add_model_monitoring*.py

# Apply migrations
alembic upgrade head

# Verify
psql -d your_database -c "\d transcriptions"
psql -d your_database -c "\d ai_error_logs"
psql -d your_database -c "\d ai_model_pricing"
Step 2: Code Changes
bash# Backend
git add app/workers/transcription_worker.py
git add app/models/ai_error_log.py
git add app/models/transcription.py
git add app/models/ai_model_pricing.py
git add app/services/gemini_service.py
git add app/api/credits.py
git add app/schemas/transcription.py

# Frontend
git add src/types/transcription.ts
git add src/pages/TranscriptionDetailPage.tsx
git add src/pages/UploadPage.tsx

git commit -m "fix: Implement AI provider routing and error handling

- Worker now respects user-selected provider/model
- Add model validation before API calls
- Track errors in database (ai_error_logs)
- Display errors in frontend with retry option
- Add model health monitoring and auto-disable
- Implement real-time model validation API

Fixes #XXX"
Step 3: Restart Services
bash# Stop services
sudo systemctl stop mp4totext-worker
sudo systemctl stop mp4totext-backend

# Clear Redis cache (if using)
redis-cli FLUSHDB

# Update code
git pull origin main

# Restart
sudo systemctl start mp4totext-backend
sudo systemctl start mp4totext-worker

# Check logs
sudo journalctl -u mp4totext-worker -f
sudo journalctl -u mp4totext-backend -f
Step 4: Verification
bash# 1. Test routing
curl -X POST http://localhost:8000/api/v1/transcriptions/upload \
  -F "file=@test.mp3" \
  -F 'transcription_options={"ai_enhancement":true,"ai_provider":"together","ai_model":"meta-llama/Llama-3.3-70B-Instruct-Turbo"}'

# 2. Check worker logs → Should show "User selected provider: together"

# 3. Test error handling (unavailable model)
curl -X POST http://localhost:8000/api/v1/transcriptions/upload \
  -F "file=@test.mp3" \
  -F 'transcription_options={"ai_enhancement":true,"ai_provider":"together","ai_model":"together-openai/gpt-oss-120b"}'

# 4. Check database for error log
psql -d your_database -c "SELECT * FROM ai_error_logs ORDER BY created_at DESC LIMIT 5;"

# 5. Open frontend and verify error display

📞 SUPPORT
If Issues Occur:
Issue: Worker still using wrong provider
Fix:
bash# Check if singleton service is cached
# Restart worker to clear
sudo systemctl restart mp4totext-worker

# Or clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
Issue: Migration fails
Fix:
bash# Check current version
alembic current

# Downgrade one step
alembic downgrade -1

# Fix migration file
# Re-upgrade
alembic upgrade head
Issue: Frontend not showing errors
Fix:
bash# Check API response includes error fields
curl http://localhost:8000/api/v1/transcriptions/[id]

# Rebuild frontend
cd mp4totext-web
npm run build

🎓 MAINTENANCE
Weekly Tasks:
bash# Check model health
psql -d your_database -c "
SELECT model_key, provider, error_rate, consecutive_errors, is_active
FROM ai_model_pricing
WHERE error_rate > 10
ORDER BY error_rate DESC;
"

# Review error logs
psql -d your_database -c "
SELECT provider, model_key, error_code, COUNT(*) as count
FROM ai_error_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY provider, model_key, error_code
ORDER BY count DESC;
"
Monthly Tasks:
bash# Clean old error logs (keep 3 months)
psql -d your_database -c "
DELETE FROM ai_error_logs
WHERE created_at < NOW() - INTERVAL '3 months';
"

# Re-enable manually reviewed models
psql -d your_database -c "
UPDATE ai_model_pricing
SET is_active = true, auto_disabled_at = NULL
WHERE model_key = 'reviewed-model-key';
"

✅ DONE!