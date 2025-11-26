"""
OpenAI Transcript Cleaning Service
Alternative to Together AI - uses GPT-4o-mini for transcript cleaning
More stable but slightly more expensive
"""

import os
import logging
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAICleanerService:
    """OpenAI service for transcript cleaning with GPT-4o-mini"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 4000
    ):
        """
        Initialize OpenAI cleaning service
        
        Args:
            api_key: OpenAI API key (from .env if not provided)
            model: Model to use (default: gpt-4o-mini)
            temperature: Temperature for generation (lower = more conservative)
            max_tokens: Maximum tokens for completion
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configure OpenAI client
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"✅ OpenAI cleaning service initialized with model: {self.model}")
        else:
            self.client = None
            logger.warning("⚠️ OPENAI_API_KEY not found - service disabled")
    
    def is_enabled(self) -> bool:
        """Check if service is enabled (has API key)"""
        return bool(self.client)
    
    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def clean_transcript(self, raw_text: str, language: str = "auto") -> Dict[str, Any]:
        """
        Clean transcript by removing fillers and fixing grammar
        
        Args:
            raw_text: Raw transcript from Whisper
            language: Language code (tr, en, etc.) - auto-detect if not specified
            
        Returns:
            Dict with cleaned_text, original_length, cleaned_length, changes_made
        """
        if not self.is_enabled():
            logger.warning("⚠️ OpenAI cleaning disabled - returning original text")
            return {
                "cleaned_text": raw_text,
                "original_length": len(raw_text),
                "cleaned_length": len(raw_text),
                "changes_made": False,
                "error": "OpenAI cleaning service not configured"
            }
        
        if not raw_text or not raw_text.strip():
            logger.warning("⚠️ Empty transcript - nothing to clean")
            return {
                "cleaned_text": "",
                "original_length": 0,
                "cleaned_length": 0,
                "changes_made": False
            }
        
        try:
            logger.info(f"🧹 Cleaning transcript with OpenAI ({len(raw_text)} chars, language: {language})")
            
            # Language-specific instructions
            lang_instructions = self._get_language_instructions(language)
            
            # Build prompt
            prompt = self._build_cleaning_prompt(raw_text, lang_instructions)
            
            # Call OpenAI API
            logger.info(f"📡 Calling OpenAI API with {self.model}...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.9,
                stream=False
            )
            
            # Check if response is valid
            if not response.choices or not response.choices[0].message.content:
                logger.error("❌ OpenAI returned empty response")
                return {
                    "cleaned_text": raw_text,
                    "original_length": len(raw_text),
                    "cleaned_length": len(raw_text),
                    "changes_made": False,
                    "error": "Empty response from API"
                }
            
            # Extract cleaned text
            cleaned_text = response.choices[0].message.content.strip()
            
            # Calculate stats
            original_length = len(raw_text)
            cleaned_length = len(cleaned_text)
            changes_made = cleaned_text != raw_text
            
            # Log usage
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                total_tokens = usage.prompt_tokens + usage.completion_tokens
                # GPT-4o-mini: $0.150/1M input, $0.600/1M output
                cost_input = usage.prompt_tokens * 0.00000015
                cost_output = usage.completion_tokens * 0.0000006
                cost_total = cost_input + cost_output
                logger.info(f"💰 Tokens: {total_tokens} (in:{usage.prompt_tokens}, out:{usage.completion_tokens})")
                logger.info(f"💵 Cost: ${cost_total:.6f}")
            
            logger.info(f"✅ Transcript cleaned successfully with OpenAI")
            logger.info(f"   Original: {original_length} chars")
            logger.info(f"   Cleaned: {cleaned_length} chars")
            logger.info(f"   Changes: {'Yes' if changes_made else 'No'}")
            
            return {
                "cleaned_text": cleaned_text,
                "original_length": original_length,
                "cleaned_length": cleaned_length,
                "changes_made": changes_made,
                "model": self.model,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"❌ OpenAI transcript cleaning failed: {e}")
            # Return original text on error (graceful degradation)
            return {
                "cleaned_text": raw_text,
                "original_length": len(raw_text),
                "cleaned_length": len(raw_text),
                "changes_made": False,
                "error": str(e)
            }
    
    def _get_language_instructions(self, language: str) -> str:
        """Get language-specific filler words and instructions"""
        language = language.lower() if language else "auto"
        
        if language == "tr" or language == "turkish":
            return """
Language: Turkish (Türkçe)
Common Turkish filler words to remove: işte, yani, şey, hani, falan, filan, ee, aa, ıı, hı, öyle, böyle, gibi, mesela
Keep Turkish grammar rules and sentence structure.
"""
        elif language == "en" or language == "english":
            return """
Language: English
Common English filler words to remove: uh, um, like, you know, sort of, kind of, I mean, actually, basically, literally
Keep English grammar rules and sentence structure.
"""
        else:
            return """
Language: Auto-detect
Remove common filler words in the detected language.
Keep the original language - DO NOT translate.
"""
    
    def _build_cleaning_prompt(self, raw_text: str, lang_instructions: str) -> str:
        """Build the cleaning prompt (simple and functional)"""
        return f"""You are an advanced transcription-cleaning assistant.
The user will give you a transcript in any language.
Your job is to:
1. Remove all filler words (uh, like, you know, işte, yani, şey, ee, aa, etc.).
2. Fix grammar, punctuation, capitalization, and spelling.
3. Keep every original word in exactly the same order. → DO NOT rearrange, translate or paraphrase.
4. Preserve the original language of the text.

Below is the transcript. Return only the cleaned text, nothing else.

Original Transcript:
{raw_text}"""


# Singleton instance
_openai_cleaner: Optional[OpenAICleanerService] = None


def get_openai_cleaner() -> OpenAICleanerService:
    """Get or create singleton OpenAI cleaner service instance"""
    global _openai_cleaner
    if _openai_cleaner is None:
        _openai_cleaner = OpenAICleanerService()
    return _openai_cleaner
