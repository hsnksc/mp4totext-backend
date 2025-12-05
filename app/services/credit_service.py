"""
Credit Service - Manages user credits and transactions
"""

import logging
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.credit_transaction import CreditTransaction, OperationType
from app.models.transcription import Transcription

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits"""
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits: {required} required, {available} available")


class CreditPricing:
    """
    Credit pricing configuration - Dynamically loaded from database
    Falls back to hardcoded defaults if database is unavailable
    """
    
    # Fallback defaults (used if database is unavailable)
    # Now uses Float for fractional credits
    # Updated: %75 kar marjlı yeni fiyatlar (Aralık 2025)
    # Formül: Piyasa Maliyeti × 1.75 ÷ $0.02 = Kredi
    _DEFAULT_PRICING = {
        "transcription_base": 0.53,       # 0.53 kredi/dakika - Whisper $0.006/dk × 1.75 ÷ $0.02
        "speaker_recognition": 0.18,      # 0.18 kredi/dakika - Diarizasyon dahil
        "speaker_diarization": 0.18,      # 0.18 kredi/dakika - pyannote.audio Modal GPU
        "youtube_download": 0.88,         # 0.88 kredi/video - Sabit ücret
        "ai_enhancement": 20.0,           # Base fiyat - model çarpanı uygulanır
        "lecture_notes": 30.0,            # Base fiyat - model çarpanı uygulanır
        "custom_prompt": 25.0,            # Base fiyat - model çarpanı uygulanır
        "exam_questions": 35.0,           # Base fiyat - model çarpanı uygulanır
        "translation": 15.0,              # Base fiyat - model çarpanı uygulanır
        "tavily_web_search": 0.88,        # 0.88 kredi/arama - $0.01/arama × 1.75 ÷ $0.02
        "assemblyai_speech_understanding_per_minute": 1.05,  # 1.05 kredi/dk - $0.012/dk × 1.75 ÷ $0.02
        "assemblyai_llm_gateway": 4.38,   # 4.38 kredi/istek - ~$0.05/istek × 1.75 ÷ $0.02
        "entity_detection_per_minute": 0.26,  # 0.26 kredi/dk - $0.003/dk × 1.75 ÷ $0.02
    }
    
    def __init__(self, db: Session):
        """Initialize pricing with database session"""
        self.db = db
        self._pricing_cache: Dict[str, int] = {}
        self._load_pricing()
    
    def _load_pricing(self):
        """Load pricing from database"""
        try:
            from app.models.credit_pricing import CreditPricingConfig
            
            configs = self.db.query(CreditPricingConfig).filter_by(is_active=True).all()
            
            if configs:
                self._pricing_cache = {config.operation_key: config.cost_per_unit for config in configs}
                logger.info(f"✅ Loaded {len(self._pricing_cache)} pricing configs from database")
            else:
                logger.warning("⚠️ No pricing configs found in database, using defaults")
                self._pricing_cache = self._DEFAULT_PRICING.copy()
        except Exception as e:
            logger.error(f"❌ Failed to load pricing from database: {e}")
            self._pricing_cache = self._DEFAULT_PRICING.copy()
    
    def get_price(self, operation_key: str) -> float:
        """Get price for an operation (with fallback to defaults) - now returns Float"""
        return float(self._pricing_cache.get(operation_key, self._DEFAULT_PRICING.get(operation_key, 0.0)))
    
    @property
    def TRANSCRIPTION_BASE(self) -> float:
        return self.get_price("transcription_base")
    
    @property
    def SPEAKER_RECOGNITION(self) -> float:
        return self.get_price("speaker_recognition")
    
    @property
    def SPEAKER_DIARIZATION(self) -> float:
        """pyannote.audio 3.1 Modal GPU diarization - 0.25 credits/min"""
        return self.get_price("speaker_diarization")
    
    @property
    def YOUTUBE_DOWNLOAD(self) -> float:
        return self.get_price("youtube_download")
    
    @property
    def AI_ENHANCEMENT(self) -> float:
        return self.get_price("ai_enhancement")
    
    @property
    def LECTURE_NOTES(self) -> float:
        return self.get_price("lecture_notes")
    
    @property
    def CUSTOM_PROMPT(self) -> float:
        return self.get_price("custom_prompt")
    
    @property
    def EXAM_QUESTIONS(self) -> float:
        return self.get_price("exam_questions")
    
    @property
    def TRANSLATION(self) -> float:
        return self.get_price("translation")
    
    @property
    def TAVILY_WEB_SEARCH(self) -> float:
        return self.get_price("tavily_web_search")
    
    @property
    def ASSEMBLYAI_SPEECH_UNDERSTANDING_PER_MINUTE(self) -> float:
        return self.get_price("assemblyai_speech_understanding_per_minute")
    
    @property
    def ASSEMBLYAI_LLM_GATEWAY(self) -> float:
        return self.get_price("assemblyai_llm_gateway")
    
    @property
    def ENTITY_DETECTION_PER_MINUTE(self) -> float:
        return self.get_price("entity_detection_per_minute")
    
    def calculate_transcription_cost(
        self, 
        duration_seconds: float, 
        enable_diarization: bool = False,
        is_youtube: bool = False,
        transcription_provider: str = "openai_whisper"
    ) -> float:
        """
        Calculate cost for transcription based on duration and features
        
        Pricing (with Float support):
        - OpenAI Whisper: 1.0 kredi/dakika (base)
        - AssemblyAI: 1.2 kredi/dakika (1.2x, includes diarization + Whisper language detection)
        - YouTube download: Fixed cost
        
        Args:
            duration_seconds: Audio duration in seconds
            enable_diarization: Whether speaker diarization is enabled (AssemblyAI)
            is_youtube: Whether this is a YouTube video transcription
            transcription_provider: "openai_whisper" or "assemblyai"
            
        Returns:
            Total credit cost (Float - fractional credits supported!)
            
        Example:
            60 saniye OpenAI Whisper: 1 × 1.0 = 1.0 kredi
            60 saniye AssemblyAI: 1 × 1.2 = 1.2 kredi
        """
        minutes = duration_seconds / 60.0  # Don't round - use exact minutes
        
        # Provider-based pricing
        if transcription_provider == "assemblyai" or enable_diarization:
            # AssemblyAI: 1.2x cost (includes speaker diarization + language detection)
            cost = 1.2 * minutes
        else:
            # OpenAI Whisper: Base cost (1 kredi/dakika)
            cost = self.TRANSCRIPTION_BASE * minutes
        
        if is_youtube:
            cost += self.YOUTUBE_DOWNLOAD
        
        # Return float - fractional credits now supported!
        return round(cost, 2)  # Round to 2 decimal places (0.01 kredi precision)


class CreditService:
    """Service for managing user credits"""
    
    def __init__(self, db: Session):
        self.db = db
        self.pricing = CreditPricing(db)  # Dynamic pricing instance
    
    def get_balance(self, user_id: int) -> float:
        """Get user's current credit balance (Float for fractional credits)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return float(user.credits or 0.0)
    
    def calculate_operation_cost(self, operation_key: str, model_key: str = "gemini-2.5-flash", provider: str = "gemini") -> float:
        """
        Calculate final credit cost with model multiplier
        
        Args:
            operation_key: Operation type (lecture_notes, custom_prompt, etc.)
            model_key: AI model identifier (gemini-2.5-flash, gemini-2.5-pro, etc.)
            provider: AI provider (gemini, openai, groq, together)
        
        Returns:
            Final credit cost (Float - base operation cost × model multiplier)
        
        Example:
            >>> calculate_operation_cost("lecture_notes", "gemini-2.5-pro", "gemini")
            75.0  # 30 base × 2.5 multiplier
        """
        from app.models.ai_model_pricing import AIModelPricing
        
        # Get base operation cost
        base_cost = self.pricing.get_price(operation_key)
        
        # Get model multiplier from database (MUST match both provider and model_key)
        model_pricing = self.db.query(AIModelPricing).filter(
            AIModelPricing.model_key == model_key,
            AIModelPricing.provider == provider,  # ← CRITICAL: Must match provider!
            AIModelPricing.is_active == True
        ).first()
        
        # Fallback to default model if requested model not found
        if not model_pricing:
            logger.warning(f"⚠️ Model '{model_key}' (provider: {provider}) not found, using default model")
            model_pricing = self.db.query(AIModelPricing).filter(
                AIModelPricing.is_default == True
            ).first()
        
        # Get multiplier (default to 1.0 if no model found)
        multiplier = model_pricing.credit_multiplier if model_pricing else 1.0
        
        # Calculate final cost (Float - supports fractional credits)
        final_cost = round(base_cost * multiplier, 2)  # Round to 2 decimal places
        
        logger.info(f"💰 Cost calculated: {operation_key} with {model_key} ({provider}) = {base_cost} × {multiplier} = {final_cost} credits")
        
        return final_cost
    
    def calculate_text_based_cost(self, text: str, model_key: str, provider: str = "together") -> float:
        """
        Calculate credit cost based on character count (for Together AI / text-based pricing)
        
        Args:
            text: Input text to process
            model_key: AI model identifier (e.g., "meta-llama/Llama-3.3-70B-Instruct-Turbo")
            provider: AI provider (default: "together")
        
        Returns:
            Final credit cost (Float - character_count / 1000 × cost_per_1k_chars)
        
        Example:
            >>> calculate_text_based_cost("Hello world" * 1000, "meta-llama/Llama-3.3-70B-Instruct-Turbo", "together")
            1.12  # 11000 chars / 1000 × 0.0968 = 1.0648 → rounded to 1.06
        """
        from app.models.ai_model_pricing import AIModelPricing
        
        # Get character count
        char_count = len(text)
        
        # Get model pricing from database
        model_pricing = self.db.query(AIModelPricing).filter(
            AIModelPricing.model_key == model_key,
            AIModelPricing.provider == provider,
            AIModelPricing.is_active == True
        ).first()
        
        if not model_pricing:
            logger.warning(f"⚠️ Model '{model_key}' (provider: {provider}) not found for text-based pricing")
            return 0.0
        
        if not model_pricing.cost_per_1k_chars:
            logger.warning(f"⚠️ Model '{model_key}' has no cost_per_1k_chars set, falling back to multiplier system")
            # Fallback to old system (base cost × multiplier)
            base_cost = self.pricing.get_price("ai_enhancement")  # Default operation
            return round(base_cost * model_pricing.credit_multiplier, 2)
        
        # Calculate cost: (char_count / 1000) × cost_per_1k_chars
        final_cost = (char_count / 1000.0) * model_pricing.cost_per_1k_chars
        final_cost = round(final_cost, 2)  # Round to 2 decimal places
        
        logger.info(
            f"💰 Text-based cost: {char_count} chars with {model_key} ({provider}) = "
            f"({char_count}/1000) × {model_pricing.cost_per_1k_chars} = {final_cost} credits"
        )
        
        return final_cost
    
    def check_sufficient_credits(self, user_id: int, required: float) -> bool:
        """Check if user has enough credits (Float for fractional credits)"""
        balance = self.get_balance(user_id)
        return balance >= required
    
    def deduct_credits(
        self,
        user_id: int,
        amount: float,  # Float for fractional credits
        operation_type: OperationType,
        description: str,
        transcription_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Deduct credits from user account and create transaction record
        
        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check balance
        if user.credits < amount:
            raise InsufficientCreditsError(required=amount, available=user.credits)
        
        # Deduct credits
        user.credits -= amount
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,  # Negative for deduction
            operation_type=operation_type,
            description=description,
            transcription_id=transcription_id,
            extra_info=json.dumps(metadata) if metadata else None,
            balance_after=user.credits
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"💰 Credits deducted: user={user_id}, amount={amount}, balance={user.credits}, type={operation_type}")
        
        return transaction
    
    def add_credits(
        self,
        user_id: int,
        amount: float,  # Float for fractional credits
        operation_type: OperationType,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> CreditTransaction:
        """
        Add credits to user account (purchase, bonus, refund, etc.) - supports fractional credits
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Add credits
        user.credits += amount
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,  # Positive for addition
            operation_type=operation_type,
            description=description,
            extra_info=json.dumps(metadata) if metadata else None,
            balance_after=user.credits
        )
        
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        
        logger.info(f"💰 Credits added: user={user_id}, amount={amount}, balance={user.credits}, type={operation_type}")
        
        return transaction
    
    def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[CreditTransaction]:
        """Get user's credit transaction history"""
        return (
            self.db.query(CreditTransaction)
            .filter(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    def refund_transaction(
        self,
        transaction_id: int,
        reason: str
    ) -> CreditTransaction:
        """
        Refund a previous transaction
        """
        original_transaction = self.db.query(CreditTransaction).filter(
            CreditTransaction.id == transaction_id
        ).first()
        
        if not original_transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if original_transaction.amount >= 0:
            raise ValueError("Cannot refund a credit addition")
        
        # Refund amount is opposite of original
        refund_amount = abs(original_transaction.amount)
        
        return self.add_credits(
            user_id=original_transaction.user_id,
            amount=refund_amount,
            operation_type=OperationType.REFUND,
            description=f"Refund for transaction #{transaction_id}: {reason}",
            metadata={
                "original_transaction_id": transaction_id,
                "reason": reason
            }
        )


# Singleton instance
_credit_service_instance: Optional[CreditService] = None


def get_credit_service(db: Session) -> CreditService:
    """Get or create credit service instance"""
    return CreditService(db)
