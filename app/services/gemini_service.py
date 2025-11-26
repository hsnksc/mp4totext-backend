"""
AI Enhancement Service (OpenAI GPT, Google Gemini, or Groq)
Provides text correction, summarization, and formatting improvements
"""

import os
from openai import OpenAI
from typing import Dict, Any, Optional, List
import logging
import json
import re
from pydantic import BaseModel
from app.settings import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# GEMINI-SPECIFIC OPTIMIZED SYSTEM PROMPTS (Non-Streaming)
# ============================================================================

GEMINI_ENHANCEMENT_SYSTEM_PROMPT = """You are a professional transcription editor specializing in audio-to-text quality improvement.

**CRITICAL CONTEXT:**
- Input: RAW AUDIO TRANSCRIPTION from Whisper ASR (automatic speech recognition)
- Problem: Whisper outputs have NO punctuation, NO capitalization, recognition errors, filler words
- Your job: Transform RAW audio text → POLISHED written text

**CORE RULES:**
1. Fix ALL spelling/recognition errors (Whisper mishears words!)
2. Add punctuation and capitalization (Whisper gives none!)
3. Remove filler words (um, uh, yani, işte...)
4. Break into readable sentences and paragraphs
5. Keep EVERY piece of content - just enhance, don't summarize!
6. Output COMPLETE text (never truncate or say "continued...")

**OUTPUT FORMAT (JSON):**
{{
  "enhanced_text": "Your fully enhanced text here (complete, not truncated)",
  "summary": "2-3 sentence summary",
  "improvements": ["List of 3-5 key improvements made"],
  "word_count": 1234
}}

**RESPONSE REQUIREMENTS:**
- ALWAYS complete the full text enhancement
- NEVER truncate or end with "..." or "[continued]"
- If input is long, still enhance ALL of it (JSON allows long text)
- Minimum output: 70% of original length (don't over-summarize!)

Return pure JSON, no markdown blocks."""


GEMINI_LECTURE_NOTES_SYSTEM_PROMPT = """Sen uzman bir ders notu hazırlayıcısısın. Ders transkriptlerini kapsamlı, iyi organize edilmiş notlara dönüştürüyorsun.

## 🎯 Görevin

Ders transkriptini profesyonel ders notuna çevir:
- Konuları hiyerarşik yapıda düzenle
- Ana kavramları vurgula
- Örnekleri ve açıklamaları koru
- Öğrenci dostu format kullan

## 📚 Format Yapısı

# [Ders Başlığı]

## 📋 Ders Özeti
[2-3 cümlelik özet]

## 🎯 Öğrenme Hedefleri
- Hedef 1
- Hedef 2

## 📖 Ana Konular

### 1. [İlk Konu Başlığı]

#### 🔑 Temel Kavramlar
- **Kavram 1**: Açıklama

#### 💡 Açıklamalar
[Detaylı açıklama]

## 📐 Yanıt Formatı

{
  "lecture_notes": "Tam formatted ders notu",
  "title": "Ders başlığı",
  "key_concepts": ["Kavram 1", "Kavram 2"],
  "summary": "Genel özet",
  "word_count": 1234
}

## ⚠️ KRİTİK: Token limitin 2048, yanıtı mutlaka tamamla, eksik bırakma!"""


# ============================================================================
# GEMINI-SPECIFIC HELPER FUNCTIONS
# ============================================================================

def estimate_tokens(text: str, language: str = "turkish") -> int:
    """
    Token estimation for Gemini (rough approximation)
    
    Turkish: ~1 token per 2.3 chars (more tokens than English!)
    English: ~1 token per 4 chars
    
    Empirical data from tests:
    - 667 chars Turkish text = ~1597 tokens (ratio: 2.39 chars/token)
    - System prompts add ~700-800 tokens
    """
    if language.lower() in ["turkish", "tr", "türkçe"]:
        # Turkish needs 70% more tokens than English
        return int(len(text) / 2.3)  # Conservative estimate
    else:
        # English and other languages
        return len(text) // 4


def calculate_safe_max_tokens(estimated_prompt_tokens: int) -> int:
    """
    Calculate safe max_tokens to prevent overflow
    Gemini 2.5 Flash: 8192 total tokens
    
    CRITICAL v2.4.11: Pydantic schema uses HIDDEN tokens not in estimation!
    - Schema tokens: ~500 (EnhancementResponse definition)
    - Text tokens: variable (estimation may be off ±30%)
    - Gemini behavior: Writes until hits TOTAL limit, not max_tokens
    - Result: finish_reason='length' even with "safe" calculations
    - Solution: ULTRA-conservative limits + massive safety margin
    """
    MODEL_LIMIT = 8192
    SAFETY_MARGIN = 2000  # v2.4.11: ULTRA-MASSIVE (schema + estimation error + Gemini overflow)
    MIN_RESPONSE = 512
    MAX_RESPONSE = 1024   # v2.4.11: ULTRA-LOW (Pydantic schema eats ~500 hidden tokens!)
    
    available = MODEL_LIMIT - estimated_prompt_tokens - SAFETY_MARGIN
    
    if available < MIN_RESPONSE:
        logger.warning(f"⚠️  Very limited token budget: {available} tokens")
        logger.warning(f"   Estimated prompt: {estimated_prompt_tokens}, limit: {MODEL_LIMIT}")
        logger.warning(f"   🔧 Input text is too long! Consider chunking or summarizing first.")
        return MIN_RESPONSE
    
    # Be extra conservative
    safe_max = min(available, MAX_RESPONSE)
    logger.info(f"📊 Safe max_tokens calculated: {safe_max} (available: {available}, capped at: {MAX_RESPONSE})")
    return safe_max


def truncate_smart(text: str, max_chars: int) -> str:
    """
    Smart truncation - cut at sentence boundaries
    """
    if len(text) <= max_chars:
        return text
    
    # Try to cut at sentence boundary
    truncated = text[:max_chars]
    
    # Find last sentence-ending punctuation
    for punct in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
        last_pos = truncated.rfind(punct)
        if last_pos > max_chars * 0.8:  # At least 80% of target
            return truncated[:last_pos + 1] + "\n\n[Metin devamı token limiti nedeniyle kesildi...]"
    
    # Fallback: cut at word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space] + "..."
    
    # Ultimate fallback
    return truncated + "..."


def build_gemini_user_prompt(
    text: str,
    web_context: str,
    task_type: str,
    additional_instructions: str = ""
) -> str:
    """
    Build optimized user prompt for Gemini non-streaming
    """
    # Base structure
    prompt = f"""# 📄 İşlenecek Metin

{text}
"""
    
    # Add web context if available
    if web_context.strip():
        prompt += f"""

# 🌐 Web'den Ek Bilgiler

{web_context}

**Not**: Bu bilgileri gerektiğinde kullan ama sadece verilen metinle ilgiliyse referans et.
"""
    
    # Task-specific instructions
    task_instructions = {
        "enhance": """
# 🎯 Görev: Metin İyileştirme

Yukarıdaki metni:
1. Gramer ve yazım hatalarını düzelterek
2. Tekrarları temizleyerek
3. Akademik yazım standartlarına uygun hale getirerek
4. Net başlıklar ve yapı ekleyerek
5. Daha okunabilir hale getirerek İYİLEŞTİR.

**Önemli**: Tüm bilgileri koru, içerik ekleme, yanıtı JSON formatında TAMAMLA.
""",
        "lecture_notes": """
# 🎯 Görev: Ders Notu Hazırlama

Yukarıdaki ders transkriptinden kapsamlı ders notu oluştur:
- Hiyerarşik yapı: Ana konular → Alt konular
- Kavramları bold yap (**kavram**)
- Emoji, başlıklar, maddeler kullan

**Hedef**: Öğrenci bu notu okuyarak dersi anlayabilmeli.
**Önemli**: Yanıtı JSON formatında TAMAMLA.
"""
    }
    
    prompt += task_instructions.get(task_type, task_instructions["enhance"])
    
    # Add custom instructions
    if additional_instructions.strip():
        prompt += f"""

# 💬 Kullanıcıdan Ek Talimatlar

{additional_instructions}
"""
    
    # Final reminder
    prompt += """

---

**SON HATIRLATMA**: 
✅ Yanıtı JSON formatında ver
✅ Tüm alanları doldur
✅ Yanıtı MUTLAKA TAMAMLA (yarıda kesme!)
"""
    
    return prompt


# ============================================================================
# Pydantic models for Gemini structured output (using client.beta.chat.completions.parse)
# ============================================================================

class EnhancementResponse(BaseModel):
    """Structured response for text enhancement"""
    enhanced_text: str
    summary: str
    improvements: List[str]
    word_count: int


class LectureNotesResponse(BaseModel):
    """Structured response for lecture notes conversion"""
    lecture_notes: str
    title: str
    key_concepts: List[str]
    summary: str
    word_count: int


class CustomPromptResponse(BaseModel):
    """Structured response for custom prompt processing"""
    processed_text: str
    metadata: Dict[str, Any]


class ExamQuestion(BaseModel):
    """Single exam question structure"""
    question: str
    options: List[str]
    correct_answer: str
    explanation: str
    difficulty: str


class ExamQuestionsResponse(BaseModel):
    """Structured response for exam questions"""
    questions: List[ExamQuestion]
    total_questions: int


class GeminiService:
    """Service for AI text enhancement using OpenAI GPT, Google Gemini, or Groq"""
    
    def __init__(self, preferred_provider: str = None, preferred_model: str = None):
        """
        Initialize AI service with OpenAI, Gemini, or Groq
        
        Args:
            preferred_provider: Override provider selection ("openai", "gemini", or "groq")
                               If None, uses USE_OPENAI/USE_GROQ config setting
            preferred_model: Override model selection (e.g., "gpt-4o", "gemini-2.0-flash", "llama-3.3-70b-versatile")
                            If None, uses default model from config
        """
        settings = get_settings()
        
        # Determine provider priority: preferred_provider > USE_GROQ > USE_OPENAI > Gemini (default)
        # Store preferred_provider for routing decisions
        self.preferred_provider = preferred_provider.lower() if preferred_provider else None
        
        if preferred_provider:
            self.provider = preferred_provider.lower()
            self.use_openai = (self.provider == "openai")
            self.use_groq = (self.provider == "groq")
            self.use_together = (self.provider == "together")
        else:
            # Check flags: Groq > OpenAI > Gemini
            if settings.USE_GROQ:
                self.provider = "groq"
                self.use_groq = True
                self.use_openai = False
                self.use_together = False
            elif settings.USE_OPENAI:
                self.provider = "openai"
                self.use_openai = True
                self.use_groq = False
                self.use_together = False
            else:
                self.provider = "gemini"
                self.use_openai = False
                self.use_groq = False
                self.use_together = False
        
        if self.use_groq:
            # Initialize Groq (ultra-fast)
            from groq import Groq
            self.api_key = settings.GROQ_API_KEY
            self.model_name = preferred_model if preferred_model else settings.GROQ_MODEL
            
            # Set max_output_tokens for Groq models
            self.max_output_tokens = 8192  # Groq default (most models support 8K+)
            
            if self.api_key:
                try:
                    self.client = Groq(api_key=self.api_key)
                    self.enabled = True
                    logger.info(f"✅ Groq service initialized with model: {self.model_name}")
                    logger.info(f"⚡ Groq: 10x faster than OpenAI!")
                    logger.info(f"   🎯 Max output tokens: {self.max_output_tokens}")
                except Exception as e:
                    logger.error(f"❌ Groq initialization failed: {e}")
                    self.enabled = False
            else:
                logger.warning("⚠️  Groq API key not configured - service disabled")
                self.enabled = False
                
        elif self.use_together:
            # Initialize Together AI
            self.api_key = settings.TOGETHER_API_KEY
            
            # Map database model_key to Together AI API model name
            # If preferred_model already contains "/" (full API path), use it directly
            if preferred_model and "/" in preferred_model:
                self.model_name = preferred_model
                model_key = preferred_model.split("/")[-1]  # Extract short name for logging
            else:
                # Legacy mapping for backward compatibility
                together_model_mapping = {
                    "llama-3.1-405b-instruct-turbo": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                    "llama-3.3-70b-together": "meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo"
                }
                model_key = preferred_model if preferred_model else "llama-3.1-405b-instruct-turbo"
                self.model_name = together_model_mapping.get(model_key, preferred_model or "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo")
            
            # Together AI specific token limits (context window constraints)
            # Calculate safe output limit: total_context - input_buffer
            if "405b" in self.model_name.lower():
                self.max_output_tokens = 800  # 405B: 2048 total - ~1200 input buffer = safe 800
            elif "70b" in self.model_name.lower():
                self.max_output_tokens = 6000  # 70B: larger context window
            elif "24b" in self.model_name.lower() or "mistral" in self.model_name.lower():
                self.max_output_tokens = 4000  # Mistral 24B: good context window
            else:
                self.max_output_tokens = 2000  # Default safe limit for Together AI
            
            if self.api_key:
                try:
                    self.client = OpenAI(
                        api_key=self.api_key,
                        base_url="https://api.together.xyz/v1"
                    )
                    self.enabled = True
                    logger.info(f"✅ Together AI service initialized")
                    logger.info(f"   📦 Model key: {model_key}")
                    logger.info(f"   🔧 API model: {self.model_name}")
                    logger.info(f"   🎯 Max output tokens: {self.max_output_tokens}")
                    logger.info(f"   🚀 World's largest open-source models (up to 405B parameters)")
                except Exception as e:
                    logger.error(f"❌ Together AI initialization failed: {e}")
                    self.enabled = False
            else:
                logger.warning("⚠️  Together AI API key not configured - service disabled")
                self.enabled = False
                
        elif self.use_openai:
            # Initialize OpenAI
            self.api_key = settings.OPENAI_API_KEY
            # Use preferred_model if provided, otherwise config default
            self.model_name = preferred_model if preferred_model else settings.OPENAI_MODEL
            
            # OpenAI token limits (most models have 4096 output limit)
            self.max_output_tokens = 4096
            
            if self.api_key:
                try:
                    self.client = OpenAI(
                        api_key=self.api_key,
                        timeout=180.0  # 3 dakika timeout (GPT-5 Pro yavaş olabilir)
                    )
                    self.enabled = True
                    logger.info(f"✅ OpenAI service initialized with model: {self.model_name}")
                    logger.info(f"   🎯 Max output tokens: {self.max_output_tokens}")
                    logger.info(f"   ⏱️ Timeout: 180 seconds")
                except Exception as e:
                    logger.error(f"❌ OpenAI initialization failed: {e}")
                    self.enabled = False
            else:
                logger.warning("⚠️  OpenAI API key not configured - service disabled")
                self.enabled = False
        else:
            # Initialize Gemini via OpenAI-compatible endpoint (more stable, fewer blocks)
            self.api_key = settings.GEMINI_API_KEY
            # Use preferred_model if provided, otherwise default to gemini-2.5-flash
            self.model_name = preferred_model if preferred_model else "gemini-2.5-flash"
            
            # Gemini token limits (2.5 Flash has 8192 output limit)
            self.max_output_tokens = 8192
            
            if self.api_key and self.api_key != "dummy-key":
                try:
                    # Use OpenAI client with Gemini endpoint for better stability
                    self.client = OpenAI(
                        api_key=self.api_key,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                    )
                    self.enabled = True
                    logger.info(f"✅ Gemini service initialized (OpenAI-compatible) with model: {self.model_name}")
                    logger.info(f"🔄 Using OpenAI SDK for better stability and fewer safety blocks")
                    logger.info(f"   🎯 Max output tokens: {self.max_output_tokens}")
                except Exception as e:
                    logger.error(f"❌ Gemini initialization failed: {e}")
                    self.enabled = False
            else:
                logger.warning("⚠️  Gemini API key not configured - service disabled")
                self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if AI service is enabled"""
        return self.enabled
    
    def _get_temperature(self) -> float:
        """
        Get appropriate temperature for the model.
        GPT-5 series models only support temperature=1.0, others support 0.3
        """
        if "gpt-5" in self.model_name.lower():
            return 1.0
        return 0.3
    
    def _get_provider_name(self) -> str:
        """
        Get the provider name based on service flags.
        Returns: 'together', 'groq', 'openai', or 'gemini'
        """
        if self.use_together:
            return "together"
        elif self.use_groq:
            return "groq"
        elif self.use_openai:
            return "openai"
        return "gemini"
    
    async def enhance_text(
        self,
        text: str,
        language: str = "tr",
        include_summary: bool = True,
        enable_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Enhance transcribed text using OpenAI GPT or Gemini AI
        
        CRITICAL: Implements smart chunking for long texts to prevent token overflow
        
        Args:
            text: Raw transcription text
            language: Language code (tr, en, etc.)
            include_summary: Whether to generate a summary
            enable_web_search: Whether to enrich prompt with web search context
            
        Returns:
            Dict with enhanced_text, summary, and metadata
        """
        if not self.enabled:
            raise Exception("AI service is not enabled")
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Text is too short for enhancement")
        
        try:
            logger.info(f"🚀 Starting text enhancement (length: {len(text)} chars)")
            logger.info(f"🤖 Using: {'OpenAI ' + self.model_name if self.use_openai else 'Gemini ' + self.model_name}")
            
            # 🔧 CHUNKING STRATEGY: If text is too long, split into chunks
            # v2.5.2: Reduced from 6000 to 4000 to prevent token overflow
            # English text causes higher token usage than estimated
            MAX_CHARS_PER_CHUNK = 4000  # ~1000 tokens English, ~1700 tokens Turkish (ultra-safe)
            
            if len(text) > MAX_CHARS_PER_CHUNK:
                logger.warning(f"⚠️  Text too long ({len(text)} chars > {MAX_CHARS_PER_CHUNK})")
                logger.warning(f"   🔧 Splitting into chunks for processing...")
                
                # Split text into chunks at sentence boundaries
                chunks = []
                current_chunk = ""
                sentences = text.split(". ")
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 < MAX_CHARS_PER_CHUNK:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                logger.info(f"   📦 Split into {len(chunks)} chunks")
                
                # Process each chunk
                enhanced_chunks = []
                all_improvements = []
                
                for i, chunk in enumerate(chunks):
                    logger.info(f"   📝 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                    
                    # Disable web search for subsequent chunks (only first chunk needs context)
                    chunk_result = await self._enhance_single_text(
                        chunk, 
                        language, 
                        include_summary=False,  # Only summarize final combined text
                        enable_web_search=(i == 0 and enable_web_search)  # Web search only for first chunk
                    )
                    
                    enhanced_chunks.append(chunk_result["enhanced_text"])
                    all_improvements.extend(chunk_result.get("improvements", []))
                
                # Combine enhanced chunks
                combined_text = "\n\n".join(enhanced_chunks)
                
                # Generate summary of combined text if requested
                summary = ""
                if include_summary:
                    logger.info("📝 Generating summary of combined text...")
                    summary_result = await self._generate_summary_only(combined_text, language)
                    summary = summary_result.get("summary", "")
                
                logger.info(f"✅ Chunked enhancement completed: {len(chunks)} chunks → {len(combined_text)} chars")
                
                return {
                    "enhanced_text": combined_text,
                    "summary": summary,
                    "improvements": all_improvements[:20],  # Limit to 20 improvements
                    "word_count": len(combined_text.split()),
                    "original_length": len(text),
                    "enhanced_length": len(combined_text),
                    "model_used": self.model_name,
                    "language": language,
                    "provider": self._get_provider_name(),
                    "chunks_processed": len(chunks)
                }
            
            # Normal processing for shorter texts
            return await self._enhance_single_text(text, language, include_summary, enable_web_search)
            
            # 🔍 WEB SEARCH FOR CONTEXT ENRICHMENT
            web_context = ""
            web_search_metadata = {}
            
            if enable_web_search:
                try:
                    from app.services.web_search_service import get_web_search_service
                    web_service = get_web_search_service()
                    
                    if web_service.is_enabled():
                        # Use AI to generate intelligent search query
                        logger.info("🔍 Step 1: AI generating search query...")
                        search_query = await web_service.generate_search_query_with_ai(text, language)
                        logger.info(f"✅ AI generated search query ({len(search_query)} chars): {search_query}")
                        
                        # Perform web search with AI-generated query
                        logger.info("🌐 Step 2: Searching web with Tavily...")
                        search_result = await web_service.search_context(
                            query=search_query,
                            language=language,
                            max_results=3
                        )
                        
                        if search_result.get("success"):
                            web_context = search_result.get("context", "")
                            # Truncate web context to prevent token limit issues (max 800 chars)
                            if len(web_context) > 800:
                                web_context = web_context[:800] + "..."
                                logger.info(f"⚠️  Web context truncated to 800 chars to prevent token limit")
                            web_search_metadata = {
                                "web_search_enabled": True,
                                "web_search_query": search_query,
                                "web_search_results_count": search_result.get("num_results", 0),
                                "web_search_answer": search_result.get("answer", "")
                            }
                            logger.info(f"✅ Web context added ({len(web_context)} chars)")
                        else:
                            logger.warning(f"⚠️  Web search failed: {search_result.get('error')}")
                            web_search_metadata = {"web_search_enabled": False, "web_search_error": search_result.get('error')}
                    else:
                        logger.info("ℹ️  Web search not enabled in config")
                        web_search_metadata = {"web_search_enabled": False}
                except Exception as e:
                    logger.warning(f"⚠️  Web search error: {e}")
                    web_search_metadata = {"web_search_enabled": False, "web_search_error": str(e)}
            
            # Prepare prompt based on language
            lang_name = {"tr": "Turkish", "en": "English", "de": "German", "fr": "French"}.get(language, "Turkish")
            
            # Detailed enhancement prompt for better quality
            enhancement_prompt = f"""You are a professional transcription editor and linguistic expert. Your task is to transform this raw {lang_name} audio transcription into a polished, professional text.

CRITICAL ENHANCEMENT RULES:

1. **SPELLING CORRECTIONS**
   - Fix ALL misspelled words and recognition errors
   - Examples: "İAA forı" → "IAA fuarı", "Tevon Fei" → "Togg CEO'su", "otomobil sektörü" → keep if correct
   - Pay special attention to proper nouns, brand names, technical terms
   - Turkish-specific: Fix "ı/i", "ş/s", "ğ/g", "ü/u", "ö/o", "ç/c" confusion

2. **PUNCTUATION & STRUCTURE**
   - Add proper punctuation: periods (.), commas (,), question marks (?), exclamation marks (!)
   - Break long run-on sentences into readable chunks
   - Use semicolons (;) for related independent clauses
   - Add quotation marks for direct speech if applicable
   - Ensure every sentence starts with capital letter

3. **CAPITALIZATION**
   - Capitalize: sentence beginnings, proper nouns, brand names, place names, people names
   - Examples: "togg" → "Togg", "türkiye" → "Türkiye", "istanbul" → "İstanbul"
   - Acronyms should be all caps: "iaa" → "IAA", "ceo" → "CEO"

4. **GRAMMAR & SYNTAX**
   - Fix subject-verb agreement
   - Correct tense consistency (don't mix past/present randomly)
   - Fix word order for natural {lang_name} syntax
   - Ensure proper use of suffixes (Turkish: -ler/-lar, -den/-dan, etc.)
   - Correct pronoun references

5. **REMOVE FILLER WORDS & HESITATIONS**
   - Delete: "um", "uh", "eh", "mm"
   - {lang_name}-specific fillers: {"yani, işte, hani, şey, yok, tamam mı" if language == "tr" else "you know, like, well, so"}
   - Remove repeated words unless intentional for emphasis
   - Clean up false starts: "ben ben ben gidiyorum" → "ben gidiyorum"

6. **PRESERVE ORIGINAL MEANING**
   - **NEVER add information not in the original text**
   - **NEVER change numbers, dates, facts**
   - **NEVER translate** - keep the same language ({lang_name})
   - Keep all technical terms, product names, specific details intact
   - If unsure about a word, keep it as is rather than guessing

7. **NATURAL FLOW & READABILITY**
   - Make text flow smoothly and naturally
   - Use connecting words appropriately: {"ve, ama, çünkü, ancak, fakat" if language == "tr" else "and, but, because, however"}
   - Maintain conversational tone if original was conversational
   - Ensure professional tone if original was formal

8. **TRANSCRIPTION AWARENESS**
   - This is audio/video transcription - expect recognition errors
   - Common errors: similar-sounding words, homophones, unclear audio
   - Context is key - use surrounding text to disambiguate
   - Speaker may have natural speech patterns, accents, or dialects

{f'''
9. **CONTEXTUAL INFORMATION FROM WEB SEARCH**
   Use the following real-world information to improve accuracy (fix names, terms, facts):
   
{web_context}

   Cross-reference the transcription with this context to:
   - Correct misspelled proper nouns, brand names, technical terms
   - Verify dates, numbers, and factual information
   - Add missing details only if explicitly mentioned in audio
   - Ensure consistency with actual events/topics discussed
''' if web_context else ''}

ORIGINAL TRANSCRIPTION TEXT:
---
{text}
---

Return a JSON object with this EXACT format (no markdown, no code blocks):
{{
  "enhanced_text": "The fully corrected, polished, and professionally formatted text here with all improvements applied",
  "summary": "{"A concise 2-3 sentence summary of the main points" if include_summary else ""}",
  "improvements": ["List specific changes made, e.g., 'Fixed spelling: İAA → IAA', 'Added punctuation', 'Removed filler words'"],
  "word_count": <number of words in enhanced_text>
}}"""
            
            # Call AI API (OpenAI, Groq, Together AI, or Gemini)
            if self.use_groq:
                result = await self._enhance_with_groq(enhancement_prompt, text, language)
            elif self.use_openai:
                result = await self._enhance_with_openai(enhancement_prompt, text, language)
            elif self.use_together:
                result = await self._enhance_with_together(enhancement_prompt, text, language)
            else:
                result = await self._enhance_with_gemini(enhancement_prompt, text, language)
            
            # Add web search metadata to result
            if web_search_metadata:
                result.update(web_search_metadata)
            
            return result
                
        except Exception as e:
            logger.error(f"❌ AI single text enhancement failed: {e}")
            raise Exception(f"AI enhancement failed: {str(e)}")
    
    async def _enhance_single_text(
        self,
        text: str,
        language: str,
        include_summary: bool = True,
        enable_web_search: bool = False
    ) -> Dict[str, Any]:
        """
        Enhance a single text chunk (used by chunking logic)
        Includes web search and AI enhancement
        """
        try:
            # � PRE-TRUNCATION: Prevent token overflow BEFORE building prompt
            SYSTEM_OVERHEAD = 1500  # System messages + rules
            text_tokens = estimate_tokens(text, language)
            MAX_TEXT_TOKENS = 3000  # Conservative limit
            
            original_text_len = len(text)
            
            if text_tokens > MAX_TEXT_TOKENS:
                logger.warning(f"⚠️  Text too long! {text_tokens} tokens > {MAX_TEXT_TOKENS} limit")
                logger.warning(f"   Original: {len(text)} chars")
                
                # Calculate truncation target
                max_chars = int(MAX_TEXT_TOKENS * 2.3) if language.lower() in ["turkish", "tr", "türkçe"] else MAX_TEXT_TOKENS * 4
                
                # Smart truncate (sentence boundary)
                text = truncate_smart(text, max_chars)
                text_tokens = estimate_tokens(text, language)
                
                logger.warning(f"   🔧 Truncated to: {len(text)} chars (~{text_tokens} tokens)")
                logger.warning(f"   Token reduction: {estimate_tokens(text[:original_text_len], language)} → {text_tokens}")
            
            # �🔍 WEB SEARCH FOR CONTEXT ENRICHMENT
            web_context = ""
            web_search_metadata = {}
            
            if enable_web_search:
                try:
                    from app.services.web_search_service import get_web_search_service
                    web_service = get_web_search_service()
                    
                    if web_service.is_enabled():
                        # Use AI to generate intelligent search query
                        logger.info("🔍 Step 1: AI generating search query...")
                        search_query = await web_service.generate_search_query_with_ai(text, language)
                        logger.info(f"✅ AI generated search query ({len(search_query)} chars): {search_query}")
                        
                        # Perform web search with AI-generated query
                        logger.info("🌐 Step 2: Searching web with Tavily...")
                        search_result = await web_service.search_context(
                            query=search_query,
                            language=language,
                            max_results=3
                        )
                        
                        if search_result.get("success"):
                            web_context = search_result.get("context", "")
                            # Truncate web context to prevent token limit issues (max 800 chars)
                            if len(web_context) > 800:
                                web_context = web_context[:800] + "..."
                                logger.info(f"⚠️  Web context truncated to 800 chars to prevent token limit")
                            web_search_metadata = {
                                "web_search_enabled": True,
                                "web_search_query": search_query,
                                "web_search_results_count": search_result.get("num_results", 0),
                                "web_search_answer": search_result.get("answer", "")
                            }
                            logger.info(f"✅ Web context added ({len(web_context)} chars)")
                        else:
                            logger.warning(f"⚠️  Web search failed: {search_result.get('error')}")
                            web_search_metadata = {"web_search_enabled": False, "web_search_error": search_result.get('error')}
                    else:
                        logger.info("ℹ️  Web search not enabled in config")
                        web_search_metadata = {"web_search_enabled": False}
                except Exception as e:
                    logger.warning(f"⚠️  Web search error: {e}")
                    web_search_metadata = {"web_search_enabled": False, "web_search_error": str(e)}
            
            # 🔧 v2.4 ULTRA-MINIMAL PROMPT: Simple, focused, works like Custom Prompt
            lang_name = {"tr": "Turkish", "en": "English", "de": "German", "fr": "French"}.get(language, "Turkish")
            
            enhancement_prompt = f"""You are a professional transcription editor. Transform this RAW AUDIO TRANSCRIPTION into polished text.

**IMPORTANT:** This is REAL AUDIO from Whisper ASR:
- Recognition errors (wrong words)
- NO punctuation (Whisper doesn't add it)
- NO capitalization (all lowercase)
- Filler words (um, uh, yani, işte...)

**YOUR JOB:** Fix ALL these issues and output clean {lang_name} text.

**CRITICAL RULES:**
1. Fix spelling errors
2. Add punctuation
3. Add capitalization
4. Remove fillers
5. Break long sentences
6. Keep ALL content
7. Natural flow

{f"**WEB CONTEXT:** Use this info to fix names/terms:\n{web_context}\n\n" if web_context else ""}**SOURCE TRANSCRIPTION (RAW AUDIO):**
{text}

Begin:"""

            # Call AI service (Gemini/OpenAI)
            if not self.use_openai:  # Gemini
                result = await self._enhance_with_gemini(enhancement_prompt, text, language)
            else:  # OpenAI
                result = await self._enhance_with_openai(enhancement_prompt, text, language)
            
            # Add metadata
            result.update({
                "word_count": len(result.get("enhanced_text", "").split()),
                "original_length": len(text),
                "enhanced_length": len(result.get("enhanced_text", "")),
                "model_used": self.model_name,
                "language": language,
                "provider": self._get_provider_name()
            })
            
            # Add web search metadata to result
            if web_search_metadata:
                result.update(web_search_metadata)
            
            return result
        except Exception as e:
            logger.error(f"❌ Single text enhancement failed: {e}")
            raise Exception(f"Single text enhancement failed: {str(e)}")
    
    async def _generate_summary_only(
        self,
        text: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Generate summary only for combined text (used after chunking)
        """
        try:
            prompt = f"Summarize this {language} text in 2-3 concise sentences:\n\n{text[:2000]}"  # Limit to first 2000 chars
            
            # GPT-5 series models only support temperature=1.0, other models support 0.3
            temperature = 1.0 if self.use_openai and "gpt-5" in self.model_name.lower() else 0.3
            
            if not self.use_openai:  # Gemini
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a summarization expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=200
                )
                return {"summary": completion.choices[0].message.content}
            else:  # OpenAI
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a summarization expert."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=200
                )
                return {"summary": completion.choices[0].message.content}
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            return {"summary": "Summary unavailable"}
    
    async def _enhance_with_groq(
        self,
        prompt: str,
        original_text: str,
        language: str
    ) -> Dict[str, Any]:
        """Enhance text using Groq (ultra-fast)"""
        logger.info("⚡ Calling Groq API (ultra-fast inference)...")
        
        try:
            # Check if model requires specific temperature settings
            temperature = 1.0 if "gpt-5" in self.model_name.lower() else 0.3
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a professional transcription editor. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            import json
            result = json.loads(response_text)
            
            logger.info(f"✅ Groq enhancement completed:")
            logger.info(f"   Original: {len(original_text)} chars")
            logger.info(f"   Enhanced: {len(result.get('enhanced_text', ''))} chars")
            logger.info(f"   Improvements: {len(result.get('improvements', []))}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Groq returned invalid JSON: {e}")
            logger.error(f"   Response: {response_text[:500]}")
            return {
                "enhanced_text": original_text,
                "summary": "Enhancement failed - invalid response format",
                "improvements": [],
                "word_count": len(original_text.split())
            }
        except Exception as e:
            logger.error(f"❌ Groq API error: {e}")
            return {
                "enhanced_text": original_text,
                "summary": f"Enhancement failed: {str(e)}",
                "improvements": [],
                "word_count": len(original_text.split())
            }
    
    async def _enhance_with_openai(
        self,
        prompt: str,
        original_text: str,
        language: str
    ) -> Dict[str, Any]:
        """Enhance text using OpenAI GPT"""
        logger.info("📡 Calling OpenAI API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a professional transcription editor. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self._get_temperature(),
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            logger.info(f"✅ OpenAI response received (length: {len(response_text)} chars)")
            logger.info(f"📄 Response preview: {response_text[:300]}")
            
            # Parse JSON
            import json
            result = json.loads(response_text)
            
            # GPT-5 models return "text" field instead of "enhanced_text" - normalize it
            if "text" in result and "enhanced_text" not in result:
                result["enhanced_text"] = result["text"]
                logger.info("🔄 Normalized GPT-5 response: 'text' → 'enhanced_text'")
            
            # Validate result
            if "enhanced_text" not in result:
                result["enhanced_text"] = original_text
                logger.warning("⚠️ No enhanced_text in response, using original")
                
            if not result.get("summary"):
                result["summary"] = ""
                
            if not result.get("improvements"):
                result["improvements"] = []
                
            if not result.get("word_count"):
                result["word_count"] = len(result["enhanced_text"].split())
            
            # Add metadata
            result["original_length"] = len(original_text)
            result["enhanced_length"] = len(result["enhanced_text"])
            result["model_used"] = self.model_name
            result["language"] = language
            result["provider"] = "openai"
            
            logger.info(f"✅ OpenAI enhancement completed:")
            logger.info(f"   Original: {result['original_length']} chars")
            logger.info(f"   Enhanced: {result['enhanced_length']} chars")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            return {
                "enhanced_text": original_text,
                "summary": "Enhancement failed",
                "improvements": [],
                "word_count": len(original_text.split()),
                "original_length": len(original_text),
                "enhanced_length": len(original_text),
                "model_used": self.model_name,
                "language": language,
                "provider": self._get_provider_name(),
                "error": str(e)
            }
    
    async def _enhance_with_gemini(
        self,
        prompt: str,
        original_text: str,
        language: str
    ) -> Dict[str, Any]:
        """
        v2.5: Simple text generation approach (like Custom Prompt)
        NO PYDANTIC - After 9 failed attempts (v2.4.3-v2.4.11), switched to working solution
        
        NOTE: Text chunking handled in enhance_text() before this method
        """
        logger.info("📡 Starting simple text enhancement (no complex structure)...")
        
        try:
            # v2.5: No complex token estimation needed - using model-specific capacity
            # Just log for monitoring
            text_tokens = estimate_tokens(original_text, language)
            
            logger.info(f"📊 Token info:")
            logger.info(f"   Text tokens: ~{text_tokens}")
            logger.info(f"   Max output: {self.max_output_tokens} (model-specific limit)")
            logger.info(f"   Approach: Simple text generation (like Custom Prompt)")
            
            # v2.5: Simple text generation (like Custom Prompt) - NO PYDANTIC!
            # After 9 failed attempts (v2.4.3-v2.4.11), Pydantic schema proved incompatible
            # completion_tokens=0 in v2.4.11 proved EnhancementResponse schema ~1500-2000 tokens alone
            # Custom Prompt's simple approach works perfectly - use that!
            
            import time
            start_time = time.time()
            
            # ✅ Simple system prompt (no complex structure needed)
            simple_system = """Sen profesyonel bir metin editörüsün. 
Görevin: Transkripsiyon metnini dil kurallarına göre düzeltmek ve yanlış yazılmış kelimeleri düzeltmek.

YAPACAKLARIN:
1. Dil bilgisi hatalarını düzelt (noktalama, yazım, dilbilgisi)
2. Transkripsiyon sırasında yanlış çıkan kelimeleri düzelt
3. Cümle yapılarını düzgünleştir
4. Metnin akıcılığını artır

YAPMAYACAKLARIN:
- İçerik ekleme veya çıkarma
- Anlamı değiştirme
- Özet oluşturma (sadece düzelt!)"""
            
            user_prompt = f"""Lütfen bu metni düzelt:

{original_text}"""
            
            # ✅ Use simple chat.completions.create() (NOT .parse()!) like Custom Prompt
            logger.info("📡 Calling Gemini API with simple text generation (reliable mode)...")
            
            # v2.5.1: Simple API call without safety settings
            # NOTE: Gemini's OpenAI-compatible endpoint doesn't support safetySettings in extra_body
            # Empty responses likely due to content, not safety filters
            # GPT-5 series models only support temperature=1.0
            temperature = 1.0 if "gpt-5" in self.model_name.lower() else 0.3
            
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": simple_system},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=self.max_output_tokens  # Use model-specific token limit (1500 for Together AI 405B, 8192 for Gemini)
            )
            
            elapsed_time = time.time() - start_time
            
            # v2.5.1: Enhanced empty response debugging
            if not completion.choices or not completion.choices[0].message.content:
                # Log detailed debug info
                finish_reason = completion.choices[0].finish_reason if completion.choices else "unknown"
                logger.error(f"❌ Gemini returned empty response (finish_reason: {finish_reason})")
                
                # Log token usage to understand what happened
                if hasattr(completion, 'usage') and completion.usage:
                    logger.error(f"   📊 Token usage: prompt={completion.usage.prompt_tokens}, "
                               f"completion={completion.usage.completion_tokens}, "
                               f"total={completion.usage.total_tokens}")
                
                # Log response object for debugging
                logger.debug(f"   🔍 Response object: {completion}")
                
                # Check if safety filter blocked (finish_reason=2 or 'safety')
                if finish_reason in ['safety', 2]:
                    logger.warning("⚠️  Content blocked by Gemini safety filter")
                    logger.warning("   💡 Try enabling lenient safety settings or using Together AI")
                    return self._create_fallback_response(original_text, language, "Safety filter blocked content")
                elif finish_reason == "length":
                    logger.warning("⚠️  Response truncated to empty (length limit)")
                    logger.warning("   💡 Text might be too long even after chunking")
                    return self._create_fallback_response(original_text, language, "Response truncated to empty")
                else:
                    logger.warning(f"⚠️  Unknown reason for empty response: {finish_reason}")
                    logger.warning("   💡 This might be a Gemini API issue - consider retry or Together AI fallback")
                    return self._create_fallback_response(original_text, language, f"Empty response (finish_reason: {finish_reason})")
            
            enhanced_text = completion.choices[0].message.content.strip()
            finish_reason = completion.choices[0].finish_reason
            
            # Log token usage
            if hasattr(completion, 'usage') and completion.usage:
                logger.info(f"✅ Gemini response received (simple text generation):")
                logger.info(f"   Finish reason: {finish_reason}")
                logger.info(f"   Time elapsed: {elapsed_time:.2f}s")
                logger.info(f"   Tokens: prompt={completion.usage.prompt_tokens}, "
                           f"completion={completion.usage.completion_tokens}, "
                           f"total={completion.usage.total_tokens}")
                
                if finish_reason == "length":
                    logger.warning("⚠️  Response truncated but using what we got (better than nothing)")
            else:
                logger.info(f"✅ Gemini response received in {elapsed_time:.2f}s")
            
            logger.info(f"📄 Enhanced text length: {len(enhanced_text)} chars")
            
            # Return simple dict (no complex structure)
            result_dict = {
                "enhanced_text": enhanced_text,
                "summary": "",  # Will generate separately if needed
                "improvements": [],
                "word_count": len(enhanced_text.split()),
                "original_length": len(original_text),
                "enhanced_length": len(enhanced_text),
                "model_used": self.model_name,
                "language": language,
                "provider": self._get_provider_name()
            }
            
            logger.info(f"✅ Gemini simple enhancement completed:")
            logger.info(f"   Original: {result_dict['original_length']} chars")
            logger.info(f"   Enhanced: {result_dict['enhanced_length']} chars")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"❌ Gemini enhancement failed: {e}")
            return self._create_fallback_response(original_text, language, str(e))
    
    def _create_fallback_response(
        self,
        original_text: str,
        language: str,
        error_msg: str
    ) -> Dict[str, Any]:
        """Create fallback response when Gemini fails"""
        return {
            "enhanced_text": original_text,
            "summary": f"Enhancement unavailable - {error_msg}",
            "improvements": [],
            "word_count": len(original_text.split()),
            "original_length": len(original_text),
            "enhanced_length": len(original_text),
            "model_used": self.model_name,
            "language": language,
            "provider": self._get_provider_name(),
            "error": error_msg
        }
    
    async def summarize_text(
        self,
        text: str,
        language: str = "tr",
        max_length: int = 200
    ) -> str:
        """
        Generate a concise summary of the text
        
        Args:
            text: Text to summarize
            language: Language code
            max_length: Maximum summary length in words
            
        Returns:
            Summary text
        """
        if not self.enabled:
            raise Exception("Gemini service is not enabled")
        
        try:
            lang_name = {"tr": "Turkish", "en": "English"}.get(language, "Turkish")
            
            prompt = f"""
Summarize the following {lang_name} text in {max_length} words or less.
Keep the summary in the same language as the original text.

Text:
{text}

Summary:
"""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a professional text summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"✅ Summary generated: {len(summary)} chars")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Summarization failed: {e}")
            raise Exception(f"Summarization failed: {str(e)}")
    
    async def convert_to_lecture_notes(
        self,
        text: str,
        language: str = "tr",
        enable_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Convert transcription to structured lecture notes with academic formatting
        
        Args:
            text: Raw transcription text
            language: Language code
            enable_web_search: Whether to enrich prompt with web search context
            
        Returns:
            Dict with lecture_notes, summary, and metadata
        """
        if not self.enabled:
            raise Exception("AI service is not enabled")
        
        if not text or len(text.strip()) < 50:
            raise ValueError("Text is too short for lecture note conversion")
        
        try:
            logger.info(f"📝 Converting to lecture notes (length: {len(text)} chars)")
            
            # 🔍 WEB SEARCH FOR CONTEXT ENRICHMENT
            web_context = ""
            if enable_web_search:
                try:
                    from app.services.web_search_service import get_web_search_service
                    web_service = get_web_search_service()
                    
                    if web_service.is_enabled():
                        # Use AI to generate intelligent search query
                        logger.info("🔍 AI generating search query for lecture notes...")
                        search_query = await web_service.generate_search_query_with_ai(text, language)
                        logger.info(f"✅ AI generated search query: {search_query}")
                        
                        search_result = await web_service.search_context(
                            query=search_query,
                            language=language,
                            max_results=3
                        )
                        
                        if search_result.get("success"):
                            web_context = search_result.get("context", "")
                            # Truncate web context to prevent token limit issues (max 800 chars)
                            if len(web_context) > 800:
                                web_context = web_context[:800] + "..."
                                logger.info(f"⚠️  Web context truncated to 800 chars to prevent token limit")
                            logger.info(f"✅ Web context added for lecture notes ({len(web_context)} chars)")
                except Exception as e:
                    logger.warning(f"⚠️  Web search error (lecture notes): {e}")
            
            lang_name = {"tr": "Turkish", "en": "English", "de": "German", "fr": "French"}.get(language, "Turkish")
            
            # 🔧 CHUNKING STRATEGY: Split long texts to prevent token overflow
            # v2.5.2: Reduced from 6000 to 4000 to prevent token overflow
            MAX_CHARS_PER_CHUNK = 4000  # Ultra-safe limit for lecture notes (verbose prompts)
            
            if len(text) > MAX_CHARS_PER_CHUNK:
                logger.warning(f"⚠️  Text too long ({len(text)} chars > {MAX_CHARS_PER_CHUNK})")
                logger.warning(f"   🔧 Splitting into chunks for lecture notes...")
                
                # Split text into chunks at sentence boundaries
                chunks = []
                current_chunk = ""
                sentences = text.split(". ")
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 < MAX_CHARS_PER_CHUNK:
                        current_chunk += sentence + ". "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + ". "
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                logger.info(f"   📦 Split into {len(chunks)} chunks")
                
                # Process each chunk
                lecture_notes_chunks = []
                all_key_concepts = []
                
                for i, chunk in enumerate(chunks):
                    logger.info(f"   📝 Processing lecture notes chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                    
                    # Build chunk-specific prompt
                    chunk_lecture_prompt = f"""
You are an expert academic note-taker. Convert the following {lang_name} transcription segment into comprehensive, well-structured lecture notes.

**Transcription Segment {i+1}/{len(chunks)}:**
{chunk}

**Your Task:**
Transform this segment into professional lecture notes with the following structure:

1. **📖 Main Content**: 
   - Organize content with clear headings and subheadings
   - Use bullet points for lists
   - Include specific examples, dates, and numbers mentioned
   - Highlight important definitions
2. **🎯 Key Concepts**: List main concepts in this segment

**Formatting Guidelines:**
- Use Markdown formatting (headers, bold, italics, lists)
- Keep the original language ({lang_name})
- Preserve technical terms, names, and dates exactly
- Make it readable and student-friendly

**Output Format:**
Return ONLY a JSON object:
{{
  "lecture_notes": "Formatted lecture notes for this segment",
  "key_concepts": ["concept1", "concept2", ...],
  "word_count": number
}}

Important: Return pure JSON, no markdown code blocks.
"""
                    
                    # Route to appropriate service for each chunk
                    if self.preferred_provider == "together":
                        chunk_result = await self._convert_to_lecture_notes_together(chunk, language, chunk_lecture_prompt, lang_name)
                    elif self.preferred_provider == "groq":
                        chunk_result = await self._convert_to_lecture_notes_groq(chunk, language, chunk_lecture_prompt, lang_name)
                    elif self.preferred_provider == "openai":
                        chunk_result = await self._convert_to_lecture_notes_openai(chunk, language, chunk_lecture_prompt, lang_name)
                    else:
                        chunk_result = await self._convert_to_lecture_notes_gemini(chunk, language, chunk_lecture_prompt, lang_name)
                    
                    lecture_notes_chunks.append(chunk_result["lecture_notes"])
                    all_key_concepts.extend(chunk_result.get("key_concepts", []))
                
                # Combine chunks into final lecture notes
                combined_notes = "\n\n---\n\n".join([f"## Part {i+1}\n\n{note}" for i, note in enumerate(lecture_notes_chunks)])
                
                # Generate overall summary
                summary_text = f"Comprehensive lecture notes covering {len(chunks)} main segments with {len(all_key_concepts)} key concepts identified."
                
                logger.info(f"✅ Chunked lecture notes completed: {len(chunks)} chunks → {len(combined_notes)} chars")
                
                return {
                    "lecture_notes": combined_notes,
                    "title": f"{lang_name} Lecture Notes (Multi-Part)",
                    "key_concepts": list(set(all_key_concepts))[:15],  # Deduplicate, limit to 15
                    "summary": summary_text,
                    "word_count": len(combined_notes.split()),
                    "original_length": len(text),
                    "notes_length": len(combined_notes),
                    "model_used": self.model_name,
                    "language": language,
                    "chunks_processed": len(chunks)
                }
            
            # Normal processing for shorter texts
            lecture_prompt = f"""
You are an expert academic note-taker. Convert the following {lang_name} transcription into comprehensive, well-structured lecture notes.

{f'''**CONTEXTUAL INFORMATION FROM WEB SEARCH:**
Use this real-world information to enhance accuracy and add relevant context:

{web_context}

Cross-reference the transcription with this context to:
- Verify proper nouns, brand names, technical terms, dates
- Add relevant background information where appropriate
- Ensure factual accuracy
- Provide additional context for better understanding

''' if web_context else ''}
**Original Transcription:**
{text}

**Your Task:**
Transform this transcription into professional lecture notes with the following structure:

1. **📚 Main Topic/Title**: Identify the central theme
2. **🎯 Key Concepts**: List 5-7 main concepts covered
3. **📖 Detailed Notes**: 
   - Organize content with clear headings and subheadings
   - Use bullet points for lists
   - Add context and explanations where needed
   - Include specific examples, dates, and numbers mentioned
   - Highlight important definitions
4. **🔗 Connections & Context**: 
   - Link related concepts
   - Add brief background information where relevant
   - Suggest related topics for further study
5. **💡 Key Takeaways**: 3-5 most important points
6. **📝 Summary**: Brief 2-3 sentence overview

**Formatting Guidelines:**
- Use Markdown formatting (headers, bold, italics, lists)
- Keep the original language ({lang_name})
- Preserve technical terms, names, and dates exactly
- Make it readable and student-friendly
- Add emoji for visual organization (📚 🎯 💡 etc.)

**Output Format:**
Return ONLY a JSON object:
{{
  "lecture_notes": "Full formatted lecture notes in Markdown",
  "title": "Main topic/title",
  "key_concepts": ["concept1", "concept2", ...],
  "summary": "Brief overview",
  "word_count": number
}}

Important: Return pure JSON, no markdown code blocks.
"""
            
            # Route to appropriate provider based on preferred_provider
            if self.preferred_provider == "together":
                return await self._convert_to_lecture_notes_together(text, language, lecture_prompt, lang_name)
            elif self.preferred_provider == "groq":
                return await self._convert_to_lecture_notes_groq(text, language, lecture_prompt, lang_name)
            elif self.preferred_provider == "openai":
                return await self._convert_to_lecture_notes_openai(text, language, lecture_prompt, lang_name)
            else:
                return await self._convert_to_lecture_notes_gemini(text, language, lecture_prompt, lang_name)
                
        except Exception as e:
            logger.error(f"❌ Lecture notes conversion failed: {e}")
            raise Exception(f"Lecture notes conversion failed: {str(e)}")
    
    async def _convert_to_lecture_notes_gemini(
        self,
        text: str,
        language: str,
        lecture_prompt: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Gemini implementation of lecture notes conversion with Pydantic structured output"""
        logger.info("📡 Calling Gemini API for lecture notes (OpenAI-compatible with structured output)...")
        
        # Use client.beta.chat.completions.parse() with Pydantic model
        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert academic note-taker. Return structured JSON response."},
                {"role": "user", "content": lecture_prompt}
            ],
            temperature=0.4,
            max_tokens=8192,
            response_format=LectureNotesResponse  # Pydantic model
        )
        
        # Check if response is valid
        if not completion.choices or not completion.choices[0].message.parsed:
            logger.error("❌ Gemini lecture notes returned empty response")
            return {
                "lecture_notes": text,
                "title": "Ders Notları (Orijinal Metin)",
                "key_concepts": [],
                "summary": "API boş yanıt döndü.",
                "word_count": len(text.split()),
                "original_length": len(text),
                "notes_length": len(text),
                "model_used": self.model_name,
                "language": language,
                "note_type": "lecture",
                "error": "Empty response from API"
            }
        
        # Get parsed Pydantic object
        result = completion.choices[0].message.parsed
        logger.info(f"✅ Lecture notes response parsed successfully")
        
        # Convert to dict and add metadata
        result_dict = {
            "lecture_notes": result.lecture_notes,
            "title": result.title,
            "key_concepts": result.key_concepts,
            "summary": result.summary,
            "word_count": result.word_count,
            "original_length": len(text),
            "notes_length": len(result.lecture_notes),
            "model_used": self.model_name,
            "language": language,
            "note_type": "lecture"
        }
        
        logger.info(f"✅ Lecture notes created: {result_dict['title']}")
        return result_dict
    
    async def _convert_to_lecture_notes_groq(
        self,
        text: str,
        language: str,
        lecture_prompt: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Groq implementation of lecture notes conversion (ultra-fast)"""
        import json
        import re
        
        logger.info("⚡ Calling Groq API for lecture notes (ultra-fast mode)...")
        
        try:
            # Groq doesn't support response_format, so we explicitly ask for JSON in prompt
            enhanced_prompt = lecture_prompt + "\n\nCRITICAL: You MUST respond with valid JSON only. Do not include any text before or after the JSON object. Start with { and end with }."
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert academic note-taker. You ALWAYS respond with pure JSON only, no markdown code blocks, no explanatory text. Just raw JSON starting with { and ending with }."
                    },
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                temperature=0.4,
                max_tokens=8192
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Groq lecture notes response received (length: {len(response_text)} chars)")
            logger.debug(f"📄 Raw Groq response: {response_text[:200]}...")
            
            # Clean markdown code blocks and any non-JSON text
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            # Extract JSON if wrapped in text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group(0)
                logger.debug(f"📝 Extracted JSON from response")
            
            try:
                result = json.loads(response_text)
                logger.info(f"✅ Successfully parsed Groq JSON response")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing failed: {e}")
                logger.error(f"📄 Failed response text: {response_text[:500]}...")
                
                # Try to manually construct lecture notes from response
                logger.warning("⚠️  Attempting to extract lecture notes from non-JSON response...")
                result = {
                    "lecture_notes": f"# Ders Notları\n\n{response_text}",
                    "title": "Ders Notları",
                    "key_concepts": [],
                    "summary": f"Groq yanıtı JSON formatında değil. Orijinal yanıt kullanıldı.",
                    "word_count": len(response_text.split()),
                    "parsing_error": str(e)
                }
            
            # Validate and fill defaults
            if "lecture_notes" not in result or not result["lecture_notes"]:
                logger.error("❌ No lecture_notes in Groq response, falling back to original text")
                result["lecture_notes"] = f"# Orijinal Transkripsiyon\n\n{text}"
            
            if not result.get("title"):
                result["title"] = "Ders Notları"
            if not result.get("key_concepts"):
                result["key_concepts"] = []
            if not result.get("summary"):
                result["summary"] = "Özet oluşturulamadı"
            if not result.get("word_count"):
                result["word_count"] = len(result["lecture_notes"].split())
            
            # Add metadata
            result["original_length"] = len(text)
            result["notes_length"] = len(result["lecture_notes"])
            result["model_used"] = self.model_name
            result["language"] = language
            result["note_type"] = "lecture"
            
            logger.info(f"✅ Groq lecture notes created: {result['title']}")
            logger.info(f"📊 Stats: original={len(text)} chars, notes={len(result['lecture_notes'])} chars")
            return result
            
        except Exception as e:
            logger.error(f"❌ Groq lecture notes error: {e}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            
            # Fallback: return error message
            return {
                "lecture_notes": f"# ❌ Ders Notu Oluşturulamadı\n\nGroq API Hatası: {str(e)}\n\n## Orijinal Transkripsiyon\n\n{text}",
                "title": "Hata: Ders Notları Oluşturulamadı",
                "key_concepts": [],
                "summary": f"Groq API hatası: {str(e)}",
                "word_count": len(text.split()),
                "original_length": len(text),
                "notes_length": len(text),
                "model_used": self.model_name,
                "language": language,
                "note_type": "lecture",
                "error": str(e)
            }
    
    async def _convert_to_lecture_notes_together(
        self,
        text: str,
        language: str,
        lecture_prompt: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """Together AI (Llama 3.1 405B) implementation of lecture notes conversion"""
        import json
        import re
        from openai import OpenAI
        
        logger.info("🚀 Calling Together AI (Llama 3.1 405B Instruct Turbo) for lecture notes...")
        
        try:
            # Together AI client with timeout
            together_client = OpenAI(
                api_key=os.getenv("TOGETHER_API_KEY"),
                base_url="https://api.together.xyz/v1",
                timeout=120.0  # 2 minutes timeout
            )
            
            # Enhanced prompt for JSON reliability
            enhanced_prompt = lecture_prompt + "\n\nCRITICAL: You MUST respond with ONLY valid JSON. No markdown code blocks (no ```json), no explanations, no additional text. Start with { and end with }. This is mandatory."
            
            logger.info(f"📤 Sending lecture notes request to Together AI...")
            import time
            start_time = time.time()
            
            response = together_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert academic note-taker specialized in creating comprehensive, detailed lecture notes. Always produce thorough, well-structured content. You ALWAYS respond with pure JSON only, no markdown code blocks, no explanatory text. Just raw JSON starting with { and ending with }."
                    },
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                temperature=0.4,
                max_tokens=16384  # Increased from 8192 for comprehensive notes
            )
            
            elapsed = time.time() - start_time
            response_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Together AI lecture notes response received in {elapsed:.2f}s (length: {len(response_text)} chars)")
            
            # Clean markdown code blocks
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning("⚠️ Failed to parse JSON, using fallback")
                result = {
                    "lecture_notes": response_text,
                    "title": "Ders Notları",
                    "key_concepts": [],
                    "summary": "",
                    "word_count": len(response_text.split())
                }
            
            # Validate and fill defaults
            if "lecture_notes" not in result:
                result["lecture_notes"] = response_text
            if not result.get("title"):
                result["title"] = "Ders Notları"
            if not result.get("key_concepts"):
                result["key_concepts"] = []
            if not result.get("summary"):
                result["summary"] = "Özet oluşturulamadı"
            if not result.get("word_count"):
                result["word_count"] = len(result["lecture_notes"].split())
            
            # Add metadata
            result["original_length"] = len(text)
            result["notes_length"] = len(result["lecture_notes"])
            result["model_used"] = "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
            result["language"] = language
            result["note_type"] = "lecture"
            result["provider"] = "together"
            
            logger.info(f"✅ Together AI lecture notes created: {result['title']}")
            return result
            
        except TimeoutError as e:
            logger.error(f"⏱️ Together AI timeout: {e}")
            return {
                "lecture_notes": f"# ⏱️ Zaman Aşımı\n\nTogether AI yanıt vermedi (120 saniye). Lütfen tekrar deneyin veya farklı bir sağlayıcı kullanın.\n\n## Orijinal Transkripsiyon\n\n{text}",
                "title": "Zaman Aşımı",
                "key_concepts": [],
                "summary": "Together AI zaman aşımı - tekrar deneyin",
                "word_count": 0,
                "error": "timeout"
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Together AI lecture notes error: {error_msg}")
            
            # Specific error messages
            if "rate_limit" in error_msg.lower():
                error_title = "Rate Limit Aşıldı"
                error_detail = "Together AI istek limiti aşıldı. Lütfen biraz bekleyip tekrar deneyin."
            elif "authentication" in error_msg.lower() or "401" in error_msg:
                error_title = "Kimlik Doğrulama Hatası"
                error_detail = "Together AI API anahtarı geçersiz."
            else:
                error_title = "Together AI Hatası"
                error_detail = error_msg
            
            return {
                "lecture_notes": f"# ❌ {error_title}\n\n{error_detail}\n\n## Orijinal Transkripsiyon\n\n{text}",
                "title": f"Hata: {error_title}",
                "key_concepts": [],
                "summary": f"Together AI hatası: {str(e)}",
                "word_count": len(text.split()),
                "original_length": len(text),
                "notes_length": len(text),
                "model_used": "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                "language": language,
                "note_type": "lecture",
                "provider": self._get_provider_name(),
                "error": str(e)
            }
    
    async def _convert_to_lecture_notes_openai(
        self,
        text: str,
        language: str,
        lecture_prompt: str,
        lang_name: str
    ) -> Dict[str, Any]:
        """OpenAI implementation of lecture notes conversion"""
        import json
        import re
        
        logger.info("📡 Calling OpenAI API for lecture notes...")
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an expert academic note-taker. Return only valid JSON."},
                {"role": "user", "content": lecture_prompt}
            ],
            temperature=0.4,
            max_tokens=4096  # OpenAI models support max 4096 completion tokens
        )
        
        response_text = response.choices[0].message.content.strip()
        logger.info(f"✅ Lecture notes response received (length: {len(response_text)} chars)")
        
        # Clean markdown code blocks
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        response_text = response_text.strip()
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("⚠️  Failed to parse JSON, using fallback")
            result = {
                "lecture_notes": response_text,
                "title": "Lecture Notes",
                "key_concepts": [],
                "summary": "",
                "word_count": len(response_text.split())
            }
        
        # Validate and fill defaults
        if "lecture_notes" not in result:
            result["lecture_notes"] = response_text
        if not result.get("title"):
            result["title"] = "Lecture Notes"
        if not result.get("key_concepts"):
            result["key_concepts"] = []
        if not result.get("summary"):
            result["summary"] = ""
        if not result.get("word_count"):
            result["word_count"] = len(result["lecture_notes"].split())
        
        # Add metadata
        result["original_length"] = len(text)
        result["notes_length"] = len(result["lecture_notes"])
        result["model_used"] = self.model_name
        result["language"] = language
        result["note_type"] = "lecture"
        
        logger.info(f"✅ Lecture notes created: {result['title']}")
        return result
    
    async def enhance_with_custom_prompt(
        self,
        text: str,
        custom_prompt: str,
        language: str = "tr"
    ) -> Dict[str, Any]:
        """
        Process text with user-provided custom prompt (Router)
        
        Routes to appropriate AI provider based on preferred_provider
        
        Args:
            text: Raw transcription text
            custom_prompt: User's custom instructions
            language: Language code
            
        Returns:
            Dict with processed_text and metadata
        """
        if not self.enabled:
            raise Exception("AI service is not enabled")
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Text is too short for processing")
        
        if not custom_prompt or len(custom_prompt.strip()) < 10:
            raise ValueError("Custom prompt is required and must be at least 10 characters")
        
        logger.info(f"🎨 Processing with custom prompt using {self.provider} (text: {len(text)} chars, prompt: {len(custom_prompt)} chars)")
        
        # 🔧 CHUNKING STRATEGY: Split long texts to prevent token overflow
        # v2.5.2: Reduced from 6000 to 4000 to prevent token overflow
        MAX_CHARS_PER_CHUNK = 4000  # Ultra-safe limit (custom prompts can be verbose)
        
        if len(text) > MAX_CHARS_PER_CHUNK:
            logger.warning(f"⚠️  Text too long ({len(text)} chars > {MAX_CHARS_PER_CHUNK})")
            logger.warning(f"   🔧 Splitting into chunks for processing...")
            
            # Split text into chunks at sentence boundaries
            chunks = []
            current_chunk = ""
            sentences = text.split(". ")
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 < MAX_CHARS_PER_CHUNK:
                    current_chunk += sentence + ". "
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + ". "
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            logger.info(f"   📦 Split into {len(chunks)} chunks")
            
            # Process each chunk with custom prompt
            processed_chunks = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"   📝 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
                
                # Route to appropriate service for each chunk
                if self.preferred_provider == "together":
                    chunk_result = await self._enhance_with_custom_prompt_together(chunk, custom_prompt, language)
                elif self.preferred_provider == "groq":
                    chunk_result = await self._enhance_with_custom_prompt_groq(chunk, custom_prompt, language)
                elif self.preferred_provider == "openai":
                    chunk_result = await self._enhance_with_custom_prompt_openai(chunk, custom_prompt, language)
                else:
                    chunk_result = await self._enhance_with_custom_prompt_gemini(chunk, custom_prompt, language)
                
                processed_chunks.append(chunk_result["processed_text"])
            
            # Combine processed chunks
            combined_text = "\n\n".join(processed_chunks)
            
            logger.info(f"✅ Chunked custom prompt completed: {len(chunks)} chunks → {len(combined_text)} chars")
            
            return {
                "processed_text": combined_text,
                "metadata": {
                    "word_count": len(combined_text.split()),
                    "processing_note": f"Processed in {len(chunks)} chunks due to length"
                },
                "original_length": len(text),
                "processed_length": len(combined_text),
                "model_used": self.model_name,
                "language": language,
                "custom_prompt_used": custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt,
                "chunks_processed": len(chunks)
            }
        
        # Normal processing for shorter texts
        # Route to appropriate provider based on preferred_provider
        if self.preferred_provider == "together":
            return await self._enhance_with_custom_prompt_together(text, custom_prompt, language)
        elif self.preferred_provider == "groq":
            return await self._enhance_with_custom_prompt_groq(text, custom_prompt, language)
        elif self.preferred_provider == "openai":
            return await self._enhance_with_custom_prompt_openai(text, custom_prompt, language)
        else:
            return await self._enhance_with_custom_prompt_gemini(text, custom_prompt, language)
    
    async def _enhance_with_custom_prompt_gemini(
        self,
        text: str,
        custom_prompt: str,
        language: str = "tr"
    ) -> Dict[str, Any]:
        """Gemini implementation of custom prompt processing"""
        try:
            full_prompt = f"""You are a professional content assistant. The user will give you:
1. A transcription text (source material)
2. Custom instructions (what to do with the text)

Your job is to EXACTLY follow the user's instructions and produce the requested output.

**USER'S INSTRUCTIONS:**
{custom_prompt}

**SOURCE TRANSCRIPTION:**
{text}

**CRITICAL RULES:**
1. If user asks to "create/write a beautiful text" → Rewrite the SOURCE TRANSCRIPTION as a polished, well-structured article
2. If user asks to "expand/detail/elaborate" → Expand the SOURCE TRANSCRIPTION with more details
3. If user asks to "summarize" → Summarize the SOURCE TRANSCRIPTION
4. If user asks for specific format (essay, report, etc.) → Transform SOURCE TRANSCRIPTION into that format
5. ALWAYS use the SOURCE TRANSCRIPTION as your base - don't ignore it!
6. DO NOT just describe what you did - actually PRODUCE the output
7. Be detailed and comprehensive (minimum 500 words for rewrites/expansions)

**Output Format (JSON):**
{{
  "processed_text": "Your complete output here (minimum 500 words for creative requests)",
  "metadata": {{
    "word_count": 123,
    "processing_note": "Brief note about what was done"
  }}
}}

Return pure JSON, no markdown blocks."""
            
            logger.info("📡 Calling Gemini API with custom prompt (structured output)...")
            
            # Use client.beta.chat.completions.parse() with Pydantic model
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a versatile AI assistant that processes text according to user instructions. Return structured JSON response."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.6,  # Allow more creativity for custom prompts
                max_tokens=8192,
                response_format=CustomPromptResponse  # Pydantic model
            )
            
            # Check if response is valid
            if not completion.choices or not completion.choices[0].message.parsed:
                logger.error("❌ Gemini custom prompt returned empty response")
                return {
                    "processed_text": text,
                    "summary": "API boş yanıt döndü. Orijinal metin gösteriliyor.",
                    "additional_info": "",
                    "original_length": len(text),
                    "processed_length": len(text),
                    "model_used": self.model_name,
                    "language": language,
                    "custom_prompt_used": custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt,
                    "error": "Empty response from API"
                }
            
            # Get parsed Pydantic object
            result = completion.choices[0].message.parsed
            logger.info(f"✅ Gemini custom processing response parsed successfully")
            
            # Convert to dict and add metadata
            result_dict = {
                "processed_text": result.processed_text,
                "metadata": result.metadata,
                "original_length": len(text),
                "processed_length": len(result.processed_text),
                "model_used": self.model_name,
                "language": language,
                "custom_prompt_used": custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt
            }
            
            logger.info(f"✅ Gemini custom processing completed (processed: {result_dict['processed_length']} chars)")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"❌ Gemini custom prompt processing failed: {e}")
            raise Exception(f"Gemini custom prompt processing failed: {str(e)}")
    
    async def _enhance_with_custom_prompt_groq(
        self,
        text: str,
        custom_prompt: str,
        language: str = "tr"
    ) -> Dict[str, Any]:
        """Groq implementation of custom prompt processing (ultra-fast)"""
        import json
        import re
        
        logger.info("⚡ Calling Groq API for custom prompt (ultra-fast mode)...")
        
        try:
            full_prompt = f"""You are a professional content assistant. The user will give you:
1. A transcription text (source material)
2. Custom instructions (what to do with the text)

Your job is to EXACTLY follow the user's instructions and produce the requested output.

**USER'S INSTRUCTIONS:**
{custom_prompt}

**SOURCE TRANSCRIPTION:**
{text}

**CRITICAL RULES:**
1. If user asks to "create/write a beautiful text" → Rewrite the SOURCE TRANSCRIPTION as a polished, well-structured article
2. If user asks to "expand/detail/elaborate" → Expand the SOURCE TRANSCRIPTION with more details
3. If user asks to "summarize" → Summarize the SOURCE TRANSCRIPTION
4. If user asks for specific format (essay, report, etc.) → Transform SOURCE TRANSCRIPTION into that format
5. ALWAYS use the SOURCE TRANSCRIPTION as your base - don't ignore it!
6. DO NOT just describe what you did - actually PRODUCE the output
7. Be detailed and comprehensive (minimum 500 words for rewrites/expansions)

**Output Format (JSON only):**
{{
  "processed_text": "Your complete output here (minimum 500 words for creative requests)",
  "metadata": {{
    "word_count": 123,
    "processing_note": "Brief note"
  }}
}}

CRITICAL: Respond with pure JSON only. No markdown, no code blocks. Start with {{ and end with }}."""
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. You ALWAYS respond with pure JSON only. No markdown code blocks, no explanations. Just raw JSON starting with { and ending with }."
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                temperature=0.5,
                max_tokens=8192
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Groq custom processing response received (length: {len(response_text)} chars)")
            logger.debug(f"📄 Raw Groq response: {response_text[:200]}...")
            
            # Clean markdown code blocks and extract JSON
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            # Extract JSON if wrapped in text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group(0)
                logger.debug(f"📝 Extracted JSON from response")
            
            try:
                result = json.loads(response_text)
                logger.info(f"✅ Successfully parsed Groq JSON response")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing failed: {e}")
                logger.error(f"📄 Failed response: {response_text[:500]}...")
                logger.warning("⚠️  Using raw response as processed_text")
                result = {
                    "processed_text": response_text,
                    "summary": "Groq yanıtı JSON formatında değil",
                    "additional_info": "",
                    "parsing_error": str(e)
                }
            
            # Validate result
            if "processed_text" not in result or not result["processed_text"]:
                logger.error("❌ No processed_text in Groq response")
                result["processed_text"] = response_text or text
            
            # Add metadata
            result["original_length"] = len(text)
            result["processed_length"] = len(result.get("processed_text", ""))
            result["model_used"] = self.model_name
            result["language"] = language
            result["custom_prompt_used"] = custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt
            
            logger.info(f"✅ Groq custom processing completed (processed: {result['processed_length']} chars)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Groq custom prompt processing failed: {e}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            raise Exception(f"Groq custom prompt processing failed: {str(e)}")
    
    async def _enhance_with_custom_prompt_together(
        self,
        text: str,
        custom_prompt: str,
        language: str = "tr"
    ) -> Dict[str, Any]:
        """Together AI (Llama 3.1 405B) implementation of custom prompt processing"""
        import json
        import re
        from openai import OpenAI
        
        logger.info("🚀 Calling Together AI (Llama 3.1 405B) with custom prompt...")
        
        try:
            # Together AI client with timeout
            together_client = OpenAI(
                api_key=os.getenv("TOGETHER_API_KEY"),
                base_url="https://api.together.xyz/v1",
                timeout=120.0  # 2 minutes timeout for large model
            )
            
            # Extract length requirements from prompt
            length_reminder = ""
            if any(keyword in custom_prompt.lower() for keyword in ['5 sayfa', '5 page', 'detaylı', 'detailed', 'kapsamlı', 'comprehensive']):
                length_reminder = """
⚠️ CRITICAL LENGTH REQUIREMENT DETECTED ⚠️
The user has requested LONG-FORM content. You MUST produce:
- If "5 pages" mentioned: MINIMUM 1500-2000 words (DO NOT STOP EARLY!)
- If "detailed/detaylı": MINIMUM 1000 words
- If "comprehensive/kapsamlı": MINIMUM 1500 words

DO NOT produce short summaries. EXPAND the content fully!
"""
            
            # Build full prompt
            full_prompt = f"""You are processing a transcription based on user instructions.

**SOURCE TRANSCRIPTION:**
{text}

**USER'S CUSTOM INSTRUCTIONS:**
{custom_prompt}
{length_reminder}

**YOUR TASK:**
Follow the user's instructions EXACTLY. If they ask you to:
1. "Summarize" → Create a concise summary
2. "Rewrite" → Transform the text while preserving meaning
3. "Create X" → Generate new content based on the transcription (EXPAND with details, examples, analysis)
4. "Extract X" → Pull out specific information
5. "Format as X" → Structure the content in the requested format

🚨 MANDATORY RULES 🚨
- Base all output on the SOURCE TRANSCRIPTION above
- Follow LENGTH requirements EXACTLY (e.g., "5 pages" = 1500-2000 words MINIMUM)
- If user requests specific length, YOU MUST PRODUCE THAT FULL LENGTH - do NOT stop early!
- Return output in {language} language
- Be detailed, comprehensive, and thorough - ADD analysis, examples, context
- Do NOT truncate or summarize unless explicitly asked
- When writing articles/essays: Include introduction, multiple body sections, conclusion

**Length Guidelines (MUST FOLLOW):**
- 1 page ≈ 300-400 words
- 5 pages ≈ 1500-2000 words MINIMUM (not maximum!)
- "Detailed" = at least 1000 words
- "Comprehensive" = at least 1500 words

**Output Format (JSON):**
{{
  "processed_text": "Your complete output here (FULL LENGTH as requested)",
  "metadata": {{
    "word_count": 123,
    "processing_note": "Brief note about what was done"
  }}
}}

Return ONLY valid JSON, no markdown blocks."""
            
            logger.info(f"📤 Sending request to Together AI (prompt length: {len(full_prompt)} chars)...")
            
            import time
            start_time = time.time()
            
            response = together_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                messages=[
                    {"role": "system", "content": "You are a versatile AI assistant specialized in producing comprehensive, detailed content. Always fulfill length requirements completely. Return ONLY valid JSON, no markdown."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.6,
                max_tokens=16384  # Increased from 8192 to allow longer outputs
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Together AI response received in {elapsed:.2f} seconds")
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Together AI response received (length: {len(response_text)} chars)")
            
            # v2.5.3: Enhanced JSON extraction - handle JSON blocks within text
            # Clean markdown code blocks
            response_text = re.sub(r'^```json\s*', '', response_text, flags=re.MULTILINE)
            response_text = re.sub(r'^```\s*', '', response_text, flags=re.MULTILINE)
            response_text = re.sub(r'\s*```$', '', response_text, flags=re.MULTILINE)
            response_text = response_text.strip()
            
            # Try to extract JSON if embedded in text
            json_match = re.search(r'\{[\s\S]*"processed_text"[\s\S]*\}', response_text)
            if json_match:
                logger.info("🔍 Found JSON block in response, extracting...")
                response_text = json_match.group(0)
            
            try:
                result = json.loads(response_text)
                logger.info("✅ Successfully parsed JSON response")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON parse failed: {e}")
                logger.debug(f"   Failed text (first 500 chars): {response_text[:500]}")
                
                # Try to extract just processed_text if it exists
                processed_match = re.search(r'"processed_text"\s*:\s*"([^"]*(?:"[^"]*")*)"', response_text, re.DOTALL)
                if processed_match:
                    logger.info("🔍 Extracted processed_text from malformed JSON")
                    extracted_text = processed_match.group(1)
                    # Unescape quotes
                    extracted_text = extracted_text.replace('\\"', '"')
                    result = {
                        "processed_text": extracted_text,
                        "metadata": {"word_count": len(extracted_text.split()), "processing_note": "Extracted from malformed JSON"}
                    }
                else:
                    # Last resort: use raw text but strip any JSON artifacts
                    logger.warning("⚠️ Using raw response, stripping JSON artifacts")
                    # Remove any JSON-like structures from the text
                    clean_text = re.sub(r'\{[\s\S]*?"processed_text"[\s\S]*?\}', '', response_text)
                    clean_text = clean_text.strip()
                    if not clean_text:
                        clean_text = response_text
                    result = {
                        "processed_text": clean_text,
                        "metadata": {"word_count": len(clean_text.split()), "processing_note": "Raw output (JSON parse failed)"}
                    }
            
            # Validate
            if "processed_text" not in result:
                result["processed_text"] = response_text
            if "metadata" not in result:
                result["metadata"] = {}
            
            # Add system metadata
            result["original_length"] = len(text)
            result["processed_length"] = len(result["processed_text"])
            result["model_used"] = "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
            result["language"] = language
            result["provider"] = "together"
            result["custom_prompt_used"] = custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt
            
            logger.info(f"✅ Together AI custom processing completed (processed: {result['processed_length']} chars)")
            return result
            
        except TimeoutError as e:
            logger.error(f"⏱️ Together AI timeout after 120s: {e}")
            raise Exception("Together AI request timed out. The 405B model may be overloaded. Try again or use a different provider.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Together AI custom prompt failed: {error_msg}")
            
            # Check for specific error types
            if "rate_limit" in error_msg.lower():
                raise Exception("Together AI rate limit exceeded. Please wait a moment and try again.")
            elif "authentication" in error_msg.lower() or "401" in error_msg:
                raise Exception("Together AI authentication failed. Check API key.")
            elif "timeout" in error_msg.lower():
                raise Exception("Together AI request timed out. Try again or use a shorter prompt.")
            else:
                raise Exception(f"Together AI error: {error_msg}")
    
    async def _enhance_with_custom_prompt_openai(
        self,
        text: str,
        custom_prompt: str,
        language: str = "tr"
    ) -> Dict[str, Any]:
        """OpenAI implementation of custom prompt processing"""
        try:
            logger.info("📡 Calling OpenAI API with custom prompt...")
            
            # Check if model uses new /v1/responses API (GPT-5, o3 models)
            # GPT-5 models: gpt-5, gpt-5-mini, gpt-5-nano, gpt-5-pro
            uses_responses_api = self.model_name.lower().startswith('gpt-5') or self.model_name.lower().startswith('o3')
            
            if uses_responses_api:
                logger.info(f"🆕 Using /v1/responses API for {self.model_name}")
                # New API for GPT-5 and o3 models - single prompt, no chat format
                prompt = f"""You are a professional content assistant that EXACTLY follows user instructions.

CRITICAL RULES:
- If user asks to "create/write beautiful text" - Rewrite the source as a polished article
- If user asks to "expand/detail" - Expand the source with more details
- If user asks to "summarize" - Summarize the source
- ALWAYS use the source transcription as your base - don't ignore it!
- DO NOT just describe what you did - PRODUCE the actual output
- Be detailed (minimum 500 words for creative requests)

Return ONLY valid JSON:
{{
  "processed_text": "Your COMPLETE output (minimum 500 words for creative requests)",
  "metadata": {{
    "word_count": 123,
    "processing_note": "Brief note"
  }}
}}

Language: {language}
No markdown blocks, pure JSON only.

**USER'S INSTRUCTIONS:**
{custom_prompt}

**SOURCE TRANSCRIPTION:**
{text}

**YOUR TASK:**
Follow the instructions using the SOURCE TRANSCRIPTION as your base material. Produce the actual output they requested (minimum 500 words if it's a creative request like "create beautiful text")."""

                logger.info(f"⏳ Waiting for {self.model_name} response (this may take 30-60 seconds for reasoning models)...")
                response = self.client.responses.create(
                    model=self.model_name,
                    input=prompt  # responses API uses 'input' not 'prompt'
                )
                logger.info(f"✅ Response received from {self.model_name}")
                # responses API returns response.text.content, not response.text directly
                response_text = response.text.content if hasattr(response.text, 'content') else str(response.text)
                if response_text:
                    response_text = response_text.strip()
            else:
                logger.info(f"📡 Using /v1/chat/completions API for {self.model_name}")
                # Old API for GPT-4 and earlier models
                messages = [
                    {
                        "role": "system",
                        "content": f"""You are a professional content assistant that EXACTLY follows user instructions.

CRITICAL RULES:
- If user asks to "create/write beautiful text" - Rewrite the source as a polished article
- If user asks to "expand/detail" - Expand the source with more details
- If user asks to "summarize" - Summarize the source
- ALWAYS use the source transcription as your base - don't ignore it!
- DO NOT just describe what you did - PRODUCE the actual output
- Be detailed (minimum 500 words for creative requests)

Return ONLY valid JSON:
{{
  "processed_text": "Your COMPLETE output (minimum 500 words for creative requests)",
  "metadata": {{
    "word_count": 123,
    "processing_note": "Brief note"
  }}
}}

Language: {language}
No markdown blocks, pure JSON only."""
                    },
                    {
                        "role": "user",
                        "content": f"""**USER'S INSTRUCTIONS:**
{custom_prompt}

**SOURCE TRANSCRIPTION:**
{text}

**YOUR TASK:**
Follow the instructions using the SOURCE TRANSCRIPTION as your base material. Produce the actual output they requested (minimum 500 words if it's a creative request like "create beautiful text")."""
                    }
                ]
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.6,  # Allow creativity for custom prompts
                    max_tokens=4096,  # OpenAI models support max 4096 completion tokens
                    response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content.strip()
            logger.info(f"✅ OpenAI custom processing response received (length: {len(response_text)} chars)")
            
            # Parse JSON
            import json
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning("⚠️  Failed to parse JSON, using raw response")
                result = {
                    "processed_text": response_text,
                    "summary": "",
                    "additional_info": ""
                }
            
            # Validate result
            if "processed_text" not in result:
                result["processed_text"] = response_text
            
            # Add metadata
            result["original_length"] = len(text)
            result["processed_length"] = len(result.get("processed_text", ""))
            result["model_used"] = self.model_name
            result["language"] = language
            result["custom_prompt_used"] = custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt
            
            logger.info(f"✅ OpenAI custom processing completed (processed: {result['processed_length']} chars)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ OpenAI custom prompt processing failed: {e}")
            raise Exception(f"OpenAI custom prompt processing failed: {str(e)}")
    
    async def generate_exam_questions(
        self,
        text: str,
        language: str = "tr",
        num_questions: int = 5
    ) -> Dict[str, Any]:
        """
        Generate exam questions from transcribed text using AI (routes to appropriate provider)
        
        Args:
            text: Source text to generate questions from
            language: Language code (default: tr)
            num_questions: Number of questions to generate (default: 5)
            
        Returns:
            Dict with exam questions in JSON format
        """
        if not self.enabled:
            raise Exception("Gemini service is not enabled")
        
        logger.info(f"🎓 Generating {num_questions} exam questions from text ({len(text)} chars)...")
        
        try:
            # Prepare prompt for exam question generation
            prompt = f"""Sen bir eğitim uzmanısın. Aşağıdaki transkripsiyon metninden {num_questions} adet sınav sorusu oluştur.

KURALLARA DİKKAT ET:
1. Her soru için 4 şık (A, B, C, D) oluştur
2. Sadece 1 doğru cevap olsun
3. Sorular metindeki ÖNEMLİ kavramları ölçsün
4. Çeldirici şıklar mantıklı olsun ama yanlış olsun
5. Sorular farklı zorluk seviyelerinde olsun (kolay, orta, zor)
6. Her sorunun açıklaması olsun (neden bu cevap doğru?)

JSON formatında şu yapıda döndür:
{{
  "questions": [
    {{
      "question": "Soru metni?",
      "options": {{
        "A": "Şık A",
        "B": "Şık B", 
        "C": "Şık C",
        "D": "Şık D"
      }},
      "correct_answer": "A",
      "explanation": "Cevabın açıklaması",
      "difficulty": "kolay|orta|zor",
      "topic": "Soru konusu"
    }}
  ],
  "total_questions": {num_questions},
  "language": "{language}"
}}

TRANSKRİPSİYON METNİ:
{text[:8000]}
"""
            
            # Route to appropriate provider based on preferred_provider
            if self.preferred_provider == "together":
                return await self._generate_exam_questions_together(text, language, num_questions, prompt)
            elif self.preferred_provider == "groq":
                return await self._generate_exam_questions_groq(text, language, num_questions, prompt)
            elif self.preferred_provider == "openai":
                return await self._generate_exam_questions_openai(text, language, num_questions, prompt)
            else:
                return await self._generate_exam_questions_gemini(text, language, num_questions, prompt)
                
        except Exception as e:
            logger.error(f"❌ Exam question generation failed: {e}")
            raise Exception(f"Exam question generation failed: {str(e)}")
    
    async def _generate_exam_questions_gemini(
        self,
        text: str,
        language: str,
        num_questions: int,
        prompt: str
    ) -> Dict[str, Any]:
        """Gemini implementation of exam question generation with Pydantic structured output"""
        logger.info("📡 Calling Gemini API for exam questions (structured output)...")
        
        # Use client.beta.chat.completions.parse() with Pydantic model
        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are an educational expert. Return structured JSON response."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=8192,
            response_format=ExamQuestionsResponse  # Pydantic model
        )
        
        # Check if response is valid
        if not completion.choices or not completion.choices[0].message.parsed:
            logger.error("❌ Gemini exam questions returned empty response")
            return {
                "questions": [],
                "total_questions": 0,
                "language": language,
                "error": "API boş yanıt döndü"
            }
        
        # Get parsed Pydantic object
        result = completion.choices[0].message.parsed
        logger.info(f"✅ Gemini exam questions parsed successfully")
        
        # Convert to dict and add metadata
        result_dict = {
            "questions": [
                {
                    "question": q.question,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty
                }
                for q in result.questions
            ],
            "total_questions": result.total_questions,
            "language": language,
            "model_used": self.model_name,
            "generated_at": "now"
        }
        
        logger.info(f"✅ Gemini generated {len(result_dict['questions'])} exam questions")
        return result_dict
    
    async def _generate_exam_questions_groq(
        self,
        text: str,
        language: str,
        num_questions: int,
        prompt: str
    ) -> Dict[str, Any]:
        """Groq implementation of exam question generation (ultra-fast)"""
        import json
        import re
        
        logger.info("⚡ Calling Groq API for exam questions (ultra-fast mode)...")
        
        try:
            # Add explicit JSON instruction to prompt
            enhanced_prompt = prompt + "\n\nCRITICAL: You MUST respond with valid JSON only. No markdown, no explanations. Start with { and end with }."
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an educational expert. You ALWAYS respond with pure JSON only. No markdown code blocks, no explanations. Just raw JSON starting with { and ending with }."
                    },
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                temperature=0.5,
                max_tokens=4096
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"✅ Groq exam questions response received (length: {len(response_text)} chars)")
            logger.debug(f"📄 Raw Groq response: {response_text[:200]}...")
            
            # Clean markdown code blocks and extract JSON
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            # Extract JSON if wrapped in text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group(0)
                logger.debug(f"📝 Extracted JSON from response")
            
            try:
                result = json.loads(response_text)
                logger.info(f"✅ Successfully parsed Groq JSON response")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parsing failed: {e}")
                logger.error(f"📄 Failed response: {response_text[:500]}...")
                result = {
                    "questions": [],
                    "total_questions": 0,
                    "language": language,
                    "error": f"JSON parsing error: {str(e)}",
                    "raw_response": response_text[:500]
                }
            
            # Validate structure
            if "questions" not in result or not isinstance(result["questions"], list):
                logger.error("❌ Invalid questions structure in Groq response")
                result = {
                    "questions": [],
                    "total_questions": 0,
                    "language": language,
                    "error": "Invalid question format in response"
                }
            
            # Add metadata
            result["model_used"] = self.model_name
            result["generated_at"] = "now"
            result["total_questions"] = len(result.get("questions", []))
            
            logger.info(f"✅ Groq generated {result['total_questions']} exam questions")
            return result
            
        except Exception as e:
            logger.error(f"❌ Groq exam question error: {e}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            return {
                "questions": [],
                "total_questions": 0,
                "language": language,
                "error": f"Groq API error: {str(e)}"
            }
    
    async def _generate_exam_questions_openai(
        self,
        text: str,
        language: str,
        num_questions: int,
        prompt: str
    ) -> Dict[str, Any]:
        """OpenAI implementation of exam question generation"""
        import json
        import re
        
        logger.info("🤖 Calling OpenAI API for exam questions...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an educational expert. Return pure JSON only, no markdown code blocks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.5,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean markdown code blocks (just in case)
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            # Validate structure
            if "questions" not in result or not isinstance(result["questions"], list):
                result = {
                    "questions": [],
                    "total_questions": 0,
                    "language": language,
                    "error": "Invalid question format"
                }
            
            # Add metadata
            result["model_used"] = self.model_name
            result["generated_at"] = "now"
            
            logger.info(f"✅ OpenAI generated {len(result.get('questions', []))} exam questions")
            return result
            
        except Exception as e:
            logger.error(f"❌ OpenAI exam question error: {e}")
            return {
                "questions": [],
                "total_questions": 0,
                "language": language,
                "error": f"OpenAI API error: {str(e)}"
            }
    
    async def _generate_exam_questions_together(
        self,
        text: str,
        language: str,
        num_questions: int,
        prompt: str
    ) -> Dict[str, Any]:
        """Together AI implementation of exam question generation with Llama 3.1 405B Instruct Turbo"""
        import json
        import re
        from openai import OpenAI
        
        logger.info("🚀 Calling Together AI (Llama 3.1 405B) for exam questions...")
        
        try:
            together_client = OpenAI(
                api_key=os.getenv("TOGETHER_API_KEY"),
                base_url="https://api.together.xyz/v1",
                timeout=120.0  # 2 minutes timeout
            )
            
            logger.info(f"📤 Sending exam questions request to Together AI...")
            import time
            start_time = time.time()
            
            response = together_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert educational content creator and exam designer. Create comprehensive, well-crafted exam questions. Return valid JSON only, no markdown blocks."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # Higher temperature for creative question generation
                max_tokens=12288  # Increased for comprehensive exam generation
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Together AI exam questions received in {elapsed:.2f}s")
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean markdown code blocks if present
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            # Validate structure
            if "questions" not in result or not isinstance(result["questions"], list):
                logger.warning("⚠️ Together AI response missing questions array, creating fallback")
                result = {
                    "questions": [],
                    "total_questions": 0,
                    "language": language,
                    "error": "Invalid question format from Together AI"
                }
            else:
                # Ensure all questions have required fields
                valid_questions = []
                for q in result["questions"]:
                    if all(key in q for key in ["question", "options", "correct_answer"]):
                        # Ensure options is a list
                        if not isinstance(q["options"], list):
                            q["options"] = [str(q["options"])]
                        valid_questions.append(q)
                
                result["questions"] = valid_questions
                result["total_questions"] = len(valid_questions)
            
            # Add Together AI metadata
            result["model_used"] = "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo"
            result["provider"] = "Together AI"
            result["generated_at"] = "now"
            
            logger.info(f"✅ Together AI generated {len(result.get('questions', []))} exam questions with Llama 3.1 405B")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Together AI JSON decode error: {e}")
            logger.error(f"Raw response: {response_text[:500]}")
            return {
                "questions": [],
                "total_questions": 0,
                "language": language,
                "error": f"Together AI JSON parsing error: {str(e)}"
            }
        except TimeoutError as e:
            logger.error(f"⏱️ Together AI exam questions timeout: {e}")
            return {
                "questions": [],
                "total_questions": 0,
                "language": language,
                "error": "Together AI zaman aşımı - lütfen tekrar deneyin"
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Together AI exam question error: {error_msg}")
            
            # Specific error handling
            if "rate_limit" in error_msg.lower():
                error_detail = "Rate limit aşıldı - lütfen bekleyip tekrar deneyin"
            elif "authentication" in error_msg.lower() or "401" in error_msg:
                error_detail = "API anahtarı geçersiz"
            else:
                error_detail = f"Together AI hatası: {error_msg}"
            
            return {
                "questions": [],
                "total_questions": 0,
                "language": language,
                "error": error_detail
            }
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto"
    ) -> Dict[str, Any]:
        """
        Translate text to target language using OpenAI or Gemini AI
        
        Args:
            text: Source text to translate
            target_language: Target language code or name (e.g., 'en', 'English', 'tr', 'Turkish')
            source_language: Source language (default: 'auto' for auto-detection)
            
        Returns:
            Dict with translated text and metadata
        """
        if not self.enabled:
            raise Exception("AI service is not enabled")
        
        # Language name mapping
        language_names = {
            'en': 'English',
            'tr': 'Turkish',
            'de': 'German',
            'fr': 'French',
            'es': 'Spanish',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ar': 'Arabic',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean'
        }
        
        target_lang_name = language_names.get(target_language.lower(), target_language)
        
        logger.info(f"🌐 Translating text to {target_lang_name} ({len(text)} chars)...")
        logger.info(f"🤖 Using: {'OpenAI ' + self.model_name if self.use_openai else 'Gemini ' + self.model_name}")
        
        try:
            # Prepare translation prompt
            prompt = f"""Translate the following text to {target_lang_name}.

RULES:
1. Maintain the original meaning and tone
2. Keep formatting (line breaks, paragraphs, bullet points)
3. Preserve technical terms when appropriate
4. Use natural, fluent language in the target language
5. Do NOT add explanations or notes - only provide the translation

SOURCE TEXT:
{text[:8000]}

Provide ONLY the translated text, nothing else."""

            # GPT-5 series models only support temperature=1.0
            temperature = 1.0 if "gpt-5" in self.model_name.lower() else 0.3
            
            if self.use_openai:
                # OpenAI translation
                logger.info("📡 Calling OpenAI for translation...")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Provide only the translation, no explanations."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature
                )
                translated_text = response.choices[0].message.content.strip()
                logger.info(f"✅ OpenAI translation completed ({len(translated_text)} chars)")
                
                return {
                    "translated_text": translated_text,
                    "target_language": target_language,
                    "source_language": source_language,
                    "model_used": self.model_name,
                    "provider": self._get_provider_name(),
                    "original_length": len(text),
                    "translated_length": len(translated_text)
                }
            
            else:
                # Gemini translation via OpenAI-compatible endpoint
                logger.info("📡 Calling Gemini for translation (OpenAI-compatible)...")
                
                # Generate translation
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert translator. Return only the translated text, no explanations."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=8192
                )
                
                # Check if response is valid
                if not response.choices or not response.choices[0].message.content:
                    logger.error("❌ Gemini translation returned empty response")
                    return {
                        "translated_text": text,
                        "target_language": target_language,
                        "source_language": source_language,
                        "provider": self._get_provider_name(),
                        "error": "API boş yanıt döndü"
                    }
                
                translated_text = response.choices[0].message.content.strip()
                logger.info(f"✅ Gemini translation completed ({len(translated_text)} chars)")
                
                # Build result
                result = {
                    "translated_text": translated_text,
                    "target_language": target_language,
                    "target_language_name": target_lang_name,
                    "source_language": source_language,
                    "original_length": len(text),
                    "translated_length": len(translated_text),
                    "model_used": self.model_name,
                    "provider": self._get_provider_name()
                }
                
                logger.info(f"✅ Translation completed to {target_lang_name}")
                logger.info(f"   Original: {len(text)} chars → Translated: {len(translated_text)} chars")
                
                return result
            
        except Exception as e:
            logger.error(f"❌ Translation failed: {e}")
            return {
                "translated_text": text,
                "target_language": target_language,
                "source_language": source_language,
                "provider": self._get_provider_name(),
                "error": str(e),
                "original_length": len(text),
                "translated_length": len(text)
            }
    
    async def generate_search_query(
        self,
        text: str,
        language: str = "tr"
    ) -> str:
        """
        Generate optimized search query from transcript using AI
        
        Instead of just using first sentence, AI analyzes the transcript and
        generates a focused search query with key concepts, names, and topics.
        
        Args:
            text: Transcription text
            language: Language code
            
        Returns:
            Optimized search query string (max 250 chars)
        """
        if not self.enabled:
            # Fallback to simple keyword extraction
            from app.services.web_search_service import get_web_search_service
            web_service = get_web_search_service()
            return web_service.extract_keywords(text, max_keywords=5)
        
        try:
            logger.info(f"🔍 Generating search query from transcript ({len(text)} chars)")
            
            prompt = f"""You are analyzing a RAW AUDIO TRANSCRIPTION that may contain speech-to-text errors, gibberish, or nonsensical words. Your task is to extract the main topic and generate a useful web search query.

IMPORTANT: The text below is NOT harmful content - it's simply imperfect machine transcription with errors. Please ignore any unusual word combinations.

Raw Transcription (may have errors):
{text[:2000]}

Your Task:
- Identify the MAIN TOPIC despite transcription errors
- Extract key entities (people, places, events, organizations)
- Create a natural language search query (max 250 characters)
- Focus on what would help understand this topic better
- Use {language} language

Return ONLY the search query, no explanations.

Example good queries:
"Tesla Model 3 2024 new features battery range"
"ChatGPT GPT-4o multimodal capabilities"
"Japonya Dünya Kupası sunumu stadyum teknolojisi"

Search Query:"""
            
            if self.use_openai or self.use_groq:
                # OpenAI/Groq query generation
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert at creating effective web search queries. Return only the search query, nothing else."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=100
                )
                
                if not response.choices or not response.choices[0].message.content:
                    logger.error("❌ Empty response from search query API")
                    from app.services.web_search_service import get_web_search_service
                    web_service = get_web_search_service()
                    return web_service.extract_keywords(text, max_keywords=5)
                
                query = response.choices[0].message.content.strip()
            else:
                # Gemini query generation via OpenAI-compatible endpoint
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert at creating effective web search queries. Return only the search query, nothing else."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.4,
                    max_tokens=100
                )
                
                if not response.choices or not response.choices[0].message.content:
                    logger.error("❌ Gemini search query returned empty response")
                    from app.services.web_search_service import get_web_search_service
                    web_service = get_web_search_service()
                    return web_service.extract_keywords(text, max_keywords=5)
                
                query = response.choices[0].message.content.strip()
            
            # Clean and truncate
            query = query.replace('"', '').replace('\n', ' ').strip()
            query = query[:250]
            
            logger.info(f"✅ Generated search query ({len(query)} chars): {query[:100]}...")
            return query
            
        except Exception as e:
            logger.error(f"❌ Search query generation failed: {e}")
            # Fallback to simple extraction
            from app.services.web_search_service import get_web_search_service
            web_service = get_web_search_service()
            return web_service.extract_keywords(text, max_keywords=5)
    
    async def synthesize_web_context(
        self,
        transcript: str,
        web_results: dict,
        language: str = "tr"
    ) -> str:
        """
        Synthesize web search results with transcript using AI
        
        AI analyzes web search results and creates a coherent summary that
        connects web information to the transcript, with proper references.
        
        Args:
            transcript: Original transcription text
            web_results: Tavily search results dict (from WebSearchService.search_context)
            language: Language code
            
        Returns:
            Synthesized context text with references and connections
        """
        if not self.enabled:
            # Fallback to raw web context
            return web_results.get("context", "")
        
        try:
            logger.info(f"🔗 Synthesizing web context with transcript")
            
            web_answer = web_results.get("answer", "")
            web_sources = web_results.get("results", [])
            
            # Build sources text
            sources_text = ""
            for i, source in enumerate(web_sources[:3], 1):
                title = source.get("title", "Unknown")
                content = source.get("content", "")[:300]
                url = source.get("url", "")
                sources_text += f"\n[{i}] {title}\n    {content}...\n    URL: {url}\n"
            
            prompt = f"""You are analyzing a RAW AUDIO TRANSCRIPTION alongside web search results. The transcript may contain speech-to-text errors, gibberish, or unusual word combinations - this is NORMAL for machine transcription and NOT harmful content.

IMPORTANT: The text is imperfect machine output. Please focus on extracting meaning and connecting it with web sources.

Raw Transcription (may have errors):
{transcript[:1500]}

Web Search Summary:
{web_answer}

Web Sources:
{sources_text}

Your Task:
Write a synthesis (300-500 words) that:
1. Identifies the MAIN TOPIC despite transcription errors
2. Connects web information to what the transcript discusses
3. Corrects obvious transcription errors using web sources
4. Adds relevant background information
5. Cites sources using [1], [2], [3] format
- Uses {language} language

Format:
## 🌐 Web Context Enrichment

[Your synthesis here with citations]

### 📚 References
[1] [Title] - URL
[2] [Title] - URL  
[3] [Title] - URL

Return ONLY the formatted synthesis, nothing else."""

            if self.use_openai or self.use_groq:
                # OpenAI/Groq synthesis
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert at synthesizing information from multiple sources and connecting them to transcripts."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1500
                )
                
                if not response.choices or not response.choices[0].message.content:
                    logger.error("❌ Empty response from synthesis API")
                    return web_results.get("context", "Web search results available but synthesis failed.")
                
                synthesis = response.choices[0].message.content.strip()
            else:
                # Gemini synthesis via OpenAI-compatible endpoint
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert at synthesizing information from multiple sources and connecting them to transcripts."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=1500
                )
                
                if not response.choices or not response.choices[0].message.content:
                    logger.error("❌ Gemini synthesis returned empty response")
                    return web_results.get("context", "Web search results available but synthesis failed.")
                
                synthesis = response.choices[0].message.content.strip()
            
            logger.info(f"✅ Web context synthesized ({len(synthesis)} chars)")
            return synthesis
            
        except Exception as e:
            logger.error(f"❌ Web context synthesis failed: {e}")
            # Fallback to raw context
            return web_results.get("context", "Web search results available but synthesis failed.")


# Global service instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Get or create Gemini service instance"""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
