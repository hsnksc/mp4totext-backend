"""
AssemblyAI Feature Configuration Classes
Her özellik için ayrı config sınıfı
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


# PII Redaction Policies
class PIIPolicy(str, Enum):
    CREDIT_CARD = "credit_card_number"
    EMAIL = "email_address"
    PHONE = "phone_number"
    PERSON_NAME = "person_name"
    LOCATION = "location"
    DATE = "date"
    SSN = "us_social_security_number"


class PIISubstitution(str, Enum):
    HASH = "hash"
    ENTITY_NAME = "entity_name"


# Summarization Types
class SummaryType(str, Enum):
    BULLETS = "bullets"
    PARAGRAPH = "paragraph"
    HEADLINE = "headline"


# ============================================================================
# LLM GATEWAY MODELS (via Lemur API - SDK v0.46.0)
# ============================================================================

class LLMModel(str, Enum):
    """LLM Gateway supported models - Direct REST API Implementation
    
    Model names WITHOUT 'anthropic/' prefix (required by REST API)
    """
    
    # Anthropic Claude models (latest versions)
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"  # Balanced option
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"  # Fast & economical (default)
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    
    # Future models (when LLM Gateway added to Python SDK):
    # - anthropic/claude-4.5-sonnet
    # - anthropic/claude-4-opus
    # - openai/gpt-5
    # - openai/gpt-4o
    # - google/gemini-2.5-pro


# ============================================================================
# LEMUR MODELS (DEPRECATED - Use LLM Gateway instead)
# ============================================================================

class LemurModel(str, Enum):
    """⚠️ DEPRECATED: LeMUR will be sunset on March 31, 2026
    Use LLMModel and LLMGatewayConfig instead"""
    CLAUDE_3_5_SONNET = "anthropic/claude-3-5-sonnet"
    CLAUDE_3_OPUS = "anthropic/claude-3-opus"
    CLAUDE_3_HAIKU = "anthropic/claude-3-haiku"
    CLAUDE_3_SONNET = "anthropic/claude-3-sonnet"
    CLAUDE_2_1 = "anthropic/claude-2-1"
    CLAUDE_2 = "anthropic/claude-2"
    MISTRAL_7B = "assemblyai/mistral-7b"
    DEFAULT = "default"


@dataclass
class SpeechUnderstandingConfig:
    """Speech Understanding özelliklerinin yapılandırması"""
    
    # Speaker Diarization (zaten var)
    speaker_labels: bool = True
    speakers_expected: Optional[int] = None
    
    # Sentiment Analysis - $0.02/hr ✅ ENABLED BY DEFAULT
    sentiment_analysis: bool = True
    
    # Auto Chapters - $0.08/hr ✅ ENABLED BY DEFAULT
    auto_chapters: bool = True
    
    # Entity Detection - $0.08/hr ✅ ENABLED BY DEFAULT
    entity_detection: bool = True
    
    # Topic Detection (IAB Categories) - $0.15/hr ❌ DISABLED (not needed)
    iab_categories: bool = False
    
    # Content Moderation - $0.15/hr ❌ DISABLED (not needed)
    content_safety: bool = False
    
    # Auto Highlights (Key Phrases) - $0.01/hr ✅ ENABLED BY DEFAULT
    auto_highlights: bool = True
    
    # PII Redaction (opsiyonel) - $0.08/hr
    redact_pii: bool = False
    redact_pii_policies: List[PIIPolicy] = field(default_factory=list)
    redact_pii_sub: PIISubstitution = PIISubstitution.HASH
    
    # Language
    language_code: Optional[str] = None


# ============================================================================
# LLM GATEWAY CONFIG (Modern, Recommended)
# ============================================================================

@dataclass
class LLMGatewayConfig:
    """LLM Gateway configuration - Modern replacement for LeMUR"""
    
    # Enable/Disable
    enabled: bool = True
    
    # Model Selection
    model: LLMModel = LLMModel.CLAUDE_3_5_HAIKU  # Fast & economical default
    
    # Generation Parameters
    temperature: float = 0.0  # 0.0 = deterministic, 1.0 = creative
    max_tokens: int = 4000  # Output limit
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    
    # === SUMMARY CONFIG ===
    generate_summary: bool = True
    summary_prompt: str = "Provide a concise summary in bullet points"
    
    # === Q&A CONFIG ===
    enable_qa: bool = True
    questions: List[str] = field(default_factory=lambda: [
        "What are the main topics discussed?",
        "What are the key takeaways?",
        "Are there any decisions made?"
    ])
    
    # === ACTION ITEMS CONFIG ===
    extract_action_items: bool = True
    action_items_prompt: str = """Extract all action items from this transcript.
    Format as a numbered list with:
    - What needs to be done
    - Who is responsible (if mentioned)
    - Deadline (if mentioned)
    
    If no action items found, return: 'No action items identified'"""
    
    # === CUSTOM ANALYSIS ===
    custom_prompts: List[str] = field(default_factory=list)


# ============================================================================
# LEMUR CONFIG (DEPRECATED)
# ============================================================================

@dataclass
class LemurConfig:
    """⚠️ DEPRECATED: LeMUR will be sunset on March 31, 2026
    Use LLMGatewayConfig instead"""
    
    enabled: bool = False
    generate_summary: bool = False
    summary_type: SummaryType = SummaryType.BULLETS
    summary_context: Optional[str] = None
    enable_qa: bool = False
    default_questions: List[str] = field(default_factory=list)
    extract_action_items: bool = False
    custom_prompts: List[str] = field(default_factory=list)
    model: LemurModel = LemurModel.CLAUDE_3_5_SONNET
    max_output_size: int = 4000
    temperature: float = 0.0


@dataclass
class TranscriptionFeatures:
    """Tüm özelliklerin master yapılandırması"""
    
    speech_understanding: SpeechUnderstandingConfig = field(
        default_factory=SpeechUnderstandingConfig
    )
    
    # Modern LLM Gateway (recommended)
    llm_gateway: LLMGatewayConfig = field(default_factory=LLMGatewayConfig)
    
    # Legacy LeMUR (deprecated, kept for backward compatibility)
    lemur: LemurConfig = field(default_factory=LemurConfig)
    
    # Global settings
    language_detection_with_whisper: bool = True
    
    def to_assemblyai_config(self) -> dict:
        """AssemblyAI SDK config dict'e dönüştür"""
        config = {}
        
        su = self.speech_understanding
        
        # Speech Understanding features
        config["speaker_labels"] = su.speaker_labels
        if su.speakers_expected:
            config["speakers_expected"] = su.speakers_expected
            
        config["sentiment_analysis"] = su.sentiment_analysis
        config["auto_chapters"] = su.auto_chapters
        config["entity_detection"] = su.entity_detection
        config["iab_categories"] = su.iab_categories
        # content_safety is not a direct config parameter in TranscriptionConfig
        # It's enabled automatically when you access transcript.content_safety_labels
        config["auto_highlights"] = su.auto_highlights
        
        if su.redact_pii:
            config["redact_pii"] = True
            config["redact_pii_policies"] = [p.value for p in su.redact_pii_policies]
            config["redact_pii_sub"] = su.redact_pii_sub.value
            
        if su.language_code:
            config["language_code"] = su.language_code
            
        return config
    
    def calculate_cost_multiplier(self) -> float:
        """
        Seçili özelliklere göre maliyet çarpanını hesapla
        Base: 1.2 (AssemblyAI base with diarization)
        
        Language-specific features:
        - Sentiment Analysis, Auto Chapters, Key Phrases: English variants only (en, en_au, en_uk, en_us)
        - Entity Detection: All languages
        """
        import logging
        logger = logging.getLogger(__name__)
        
        base_cost = 1.2  # Base transcription with diarization
        extra_cost = 0.0
        
        su = self.speech_understanding
        
        # Language-specific features check
        english_variants = {'en', 'en_au', 'en_uk', 'en_us'}
        detected_lang = su.language_code or 'unknown'
        is_english = detected_lang in english_variants
        
        logger.info(f"💰 Calculating Speech Understanding costs for language: {detected_lang}")
        logger.info(f"   English variant: {'✅ Yes' if is_english else '❌ No'}")
        
        # Speech Understanding costs (per hour -> per minute)
        # Only charge for features that will actually work with the detected language
        charged_features = []
        skipped_features = []
        
        if su.sentiment_analysis:
            if is_english:
                extra_cost += 0.02 / 60  # $0.02/hr (English only)
                charged_features.append("Sentiment Analysis (0.02/60 cr/min)")
            else:
                skipped_features.append("Sentiment Analysis (English only)")
        
        if su.auto_chapters:
            if is_english:
                extra_cost += 0.08 / 60  # $0.08/hr (English only)
                charged_features.append("Auto Chapters (0.08/60 cr/min)")
            else:
                skipped_features.append("Auto Chapters (English only)")
        
        if su.entity_detection:
            extra_cost += 0.03 / 60  # $0.03/hr (works for all languages)
            charged_features.append("Entity Detection (0.03/60 cr/min)")
        
        if su.iab_categories:
            extra_cost += 0.15 / 60  # $0.15/hr (topic detection)
            charged_features.append("IAB Categories (0.15/60 cr/min)")
        
        if su.content_safety:
            extra_cost += 0.15 / 60  # $0.15/hr
            charged_features.append("Content Safety (0.15/60 cr/min)")
        
        if su.auto_highlights:
            if is_english:
                extra_cost += 0.01 / 60  # $0.01/hr (English only - Key Phrases)
                charged_features.append("Key Phrases (0.01/60 cr/min)")
            else:
                skipped_features.append("Key Phrases (English only)")
        
        if charged_features:
            logger.info(f"   ✅ Charged features: {', '.join(charged_features)}")
        if skipped_features:
            logger.info(f"   ⏭️ Skipped features: {', '.join(skipped_features)}")
        
        if su.redact_pii:
            extra_cost += 0.08 / 60  # $0.08/hr
        
        # LeMUR costs
        if self.lemur.enabled and self.lemur.generate_summary:
            extra_cost += 0.03 / 60  # $0.03/hr
        
        return base_cost + (extra_cost * 60)  # Convert back to per minute
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "speech_understanding": {
                "speaker_labels": self.speech_understanding.speaker_labels,
                "sentiment_analysis": self.speech_understanding.sentiment_analysis,
                "auto_chapters": self.speech_understanding.auto_chapters,
                "entity_detection": self.speech_understanding.entity_detection,
                "iab_categories": self.speech_understanding.iab_categories,
                "content_safety": self.speech_understanding.content_safety,
                "auto_highlights": self.speech_understanding.auto_highlights,
                "redact_pii": self.speech_understanding.redact_pii,
                "language_code": self.speech_understanding.language_code
            },
            "llm_gateway": {
                "enabled": self.llm_gateway.enabled,
                "generate_summary": self.llm_gateway.generate_summary,
                "enable_qa": self.llm_gateway.enable_qa,
                "extract_action_items": self.llm_gateway.extract_action_items,
                "model": self.llm_gateway.model
            },
            "lemur": {
                "enabled": self.lemur.enabled,
                "generate_summary": self.lemur.generate_summary,
                "summary_type": self.lemur.summary_type.value if self.lemur.summary_type else None,
                "enable_qa": self.lemur.enable_qa,
                "extract_action_items": self.lemur.extract_action_items,
                "model": self.lemur.model.value if self.lemur.model else "default"
            }
        }
