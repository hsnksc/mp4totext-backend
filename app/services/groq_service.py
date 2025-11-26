"""
Groq AI Service - Ultra-fast LLM inference
Supports: Llama 3.3 70B, Llama 3.1 8B, Gemma2 9B
Speed: 10x faster than OpenAI, 5x faster than Gemini
"""

import logging
from typing import Dict, Any, Optional, List
from app.settings import settings

logger = logging.getLogger(__name__)

# Global Groq client instance
_groq_client = None


def get_groq_service():
    """Get or create Groq service instance (singleton)"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqService()
    return _groq_client


class GroqService:
    """
    Groq AI service for ultra-fast text enhancement and summarization
    """
    
    def __init__(self):
        self.enabled = False
        self.client = None
        self.model_name = settings.GROQ_MODEL
        
        # Initialize Groq client
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "dummy-key":
            try:
                from groq import Groq
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                self.enabled = True
                logger.info(f"✅ Groq service initialized with model: {self.model_name}")
                logger.info(f"⚡ Groq is 10x faster than OpenAI, 5x faster than Gemini!")
            except ImportError:
                logger.error("❌ Groq package not installed. Run: pip install groq")
                self.enabled = False
            except Exception as e:
                logger.error(f"❌ Groq initialization failed: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️  Groq API key not configured - service disabled")
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """Check if Groq service is enabled"""
        return self.enabled
    
    async def enhance_text(
        self,
        text: str,
        language: str = "tr",
        include_summary: bool = True,
        web_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enhance transcribed text using Groq (ultra-fast)
        
        Args:
            text: Raw transcription text
            language: Language code (tr, en, etc.)
            include_summary: Whether to include summary
            web_context: Optional web search context for factual corrections
            
        Returns:
            Dict with enhanced_text, summary, improvements, word_count
        """
        if not self.enabled:
            logger.warning("⚠️  Groq service not enabled - returning original text")
            return {
                "enhanced_text": text,
                "summary": "Groq service not configured.",
                "improvements": [],
                "word_count": len(text.split())
            }
        
        try:
            logger.info("🚀 Starting Groq ultra-fast text enhancement...")
            logger.info(f"⚡ Model: {self.model_name}")
            
            # Build enhancement prompt with detailed rules
            lang_name = "Turkish" if language == "tr" else "English"
            
            web_context_section = ""
            if web_context:
                web_context_section = f"""
9. **CONTEXTUAL INFORMATION FROM WEB SEARCH**
{web_context}

Use this context to:
- Correct misspelled proper nouns, brand names, technical terms
- Verify dates, numbers, facts mentioned in transcription
- Add missing context where appropriate (but don't fabricate)
"""
            
            enhancement_prompt = f"""You are a professional transcription editor for {lang_name} text.

CRITICAL ENHANCEMENT RULES:

1. **SPELLING CORRECTIONS**
   - Fix ALL misspelled words and speech recognition errors
   - Turkish-specific: Fix "ı/i", "ş/s", "ğ/g", "ü/u", "ö/o", "ç/c" confusion
   - Examples: "İAA forı" → "IAA fuarı", "Tevon Fei" → "Togg CEO'su"

2. **PUNCTUATION & STRUCTURE**
   - Add proper punctuation: periods, commas, question marks, exclamation points
   - Break long run-on sentences into readable segments
   - Add paragraph breaks where topics change

3. **CAPITALIZATION**
   - Capitalize: proper nouns, brand names, places, people, acronyms
   - Examples: "togg" → "Togg", "iaa" → "IAA", "mercedes" → "Mercedes"

4. **GRAMMAR & SYNTAX**
   - Fix subject-verb agreement
   - Ensure tense consistency
   - Correct word order issues

5. **REMOVE FILLER WORDS & HESITATIONS**
   - Delete: "um", "uh", "like", "you know" (English)
   - Delete: "yani", "işte", "hani", "şey", "ee", "ııı" (Turkish)

6. **PRESERVE ORIGINAL MEANING**
   - **NEVER add information not in the original transcription**
   - **NEVER change numbers, dates, or facts**
   - **NEVER translate text to another language**
   - Keep the speaker's intent and message intact

7. **NATURAL FLOW & READABILITY**
   - Ensure smooth transitions between sentences
   - Add connecting words where appropriate ("however", "therefore", "because")
   - Maintain conversational tone if original is conversational

8. **TRANSCRIPTION AWARENESS**
   - Expect speech recognition errors (homophones, similar-sounding words)
   - Use context to disambiguate unclear words
   - Fix obvious misrecognitions (e.g., "their" vs "there")

{web_context_section}

ORIGINAL TRANSCRIPTION:
{text}

Return your response as JSON with these exact fields:
{{
  "enhanced_text": "corrected and polished text here",
  "summary": "brief 2-3 sentence summary" {"if requested" if include_summary else "(leave empty)"},
  "improvements": ["list of key improvements made"],
  "word_count": 123
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

            # Call Groq API (ultra-fast inference)
            logger.info("📡 Calling Groq API (ultra-fast inference)...")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": enhancement_prompt}
                ],
                temperature=0.3,  # Lower for more consistent corrections
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            import json
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            logger.info(f"✅ Groq ultra-fast enhancement completed:")
            logger.info(f"   Original: {len(text)} chars")
            logger.info(f"   Enhanced: {len(result.get('enhanced_text', ''))} chars")
            logger.info(f"   Improvements: {len(result.get('improvements', []))}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Groq enhancement failed: {e}")
            return {
                "enhanced_text": text,
                "summary": f"Enhancement failed: {str(e)}",
                "improvements": [],
                "word_count": len(text.split())
            }
    
    async def convert_to_notes(
        self,
        text: str,
        language: str = "tr",
        web_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert transcription to structured lecture notes using Groq (ultra-fast)
        
        Args:
            text: Enhanced transcription text
            language: Language code
            web_context: Optional web search context
            
        Returns:
            Dict with lecture_notes (markdown formatted)
        """
        if not self.enabled:
            return {
                "lecture_notes": "Groq service not configured.",
                "topics": []
            }
        
        try:
            logger.info("📝 Converting to lecture notes with Groq...")
            
            lang_name = "Turkish" if language == "tr" else "English"
            
            web_context_section = ""
            if web_context:
                web_context_section = f"\n\nADDITIONAL CONTEXT FROM WEB:\n{web_context}"
            
            notes_prompt = f"""You are an expert at creating structured lecture notes from {lang_name} transcriptions.

Convert the following transcription into well-organized lecture notes in MARKDOWN format.

STRUCTURE REQUIREMENTS:
- # Main Topic (single H1 heading)
- ## Key Concepts (H2 headings for major sections)
- ### Subtopics (H3 headings for details)
- Bullet points for lists
- **Bold** for important terms
- > Blockquotes for key quotes or definitions

CONTENT REQUIREMENTS:
- Extract main ideas and organize them logically
- Highlight key terms, definitions, and concepts
- Create clear hierarchy of information
- Remove redundancy and filler content
- Preserve important examples and explanations

{web_context_section}

TRANSCRIPTION:
{text}

Return JSON with:
{{
  "lecture_notes": "markdown formatted notes here",
  "topics": ["list", "of", "main", "topics"]
}}"""

            logger.info("📡 Calling Groq API for lecture notes...")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": notes_prompt}
                ],
                temperature=0.5,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info("✅ Groq lecture notes conversion completed")
            logger.info(f"   Topics: {len(result.get('topics', []))}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Groq notes conversion failed: {e}")
            return {
                "lecture_notes": f"Conversion failed: {str(e)}",
                "topics": []
            }
    
    async def process_with_custom_prompt(
        self,
        text: str,
        custom_prompt: str,
        language: str = "tr",
        web_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process text with user's custom prompt using Groq (ultra-fast)
        
        Args:
            text: Transcription text
            custom_prompt: User-provided instruction
            language: Language code
            web_context: Optional web search context
            
        Returns:
            Dict with result and metadata
        """
        if not self.enabled:
            return {
                "result": "Groq service not configured.",
                "success": False
            }
        
        try:
            logger.info(f"🎯 Processing custom prompt with Groq: '{custom_prompt[:50]}...'")
            
            web_context_section = ""
            if web_context:
                web_context_section = f"\n\nADDITIONAL CONTEXT:\n{web_context}"
            
            full_prompt = f"""INSTRUCTION: {custom_prompt}

TEXT TO PROCESS:
{text}
{web_context_section}

Process the text according to the instruction above."""

            logger.info("📡 Calling Groq API for custom processing...")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            
            result_text = response.choices[0].message.content
            
            logger.info("✅ Groq custom prompt processing completed")
            
            return {
                "result": result_text,
                "success": True,
                "prompt": custom_prompt
            }
            
        except Exception as e:
            logger.error(f"❌ Groq custom processing failed: {e}")
            return {
                "result": f"Processing failed: {str(e)}",
                "success": False,
                "prompt": custom_prompt
            }
    
    async def generate_search_query(
        self,
        text: str,
        language: str = "tr"
    ) -> str:
        """
        Generate optimized web search query from transcription using Groq (ultra-fast)
        
        Args:
            text: Transcription text
            language: Language code
            
        Returns:
            Optimized search query string
        """
        if not self.enabled:
            logger.warning("⚠️  Groq not enabled, using fallback extraction")
            return ""
        
        try:
            logger.info("🔍 Generating search query with Groq (ultra-fast)...")
            
            lang_name = "Turkish" if language == "tr" else "English"
            
            query_prompt = f"""Analyze this {lang_name} transcription and create an OPTIMAL search query for web search.

RULES:
1. Identify the MAIN TOPIC of the transcription
2. Extract KEY ENTITIES: brands, people, places, products, events
3. Include relevant CONTEXT words
4. Prioritize SPECIFICITY over generality
5. Remove filler words and hesitations
6. Optimal length: 5-15 words (max 150 characters)
7. Use search-friendly terms (nouns, proper nouns, specific phrases)

EXAMPLES:
- "Togg'un yeni T8X modeli hakkında konuşuyor" → "Togg T8X elektrikli araç özellikleri fiyat"
- "Mercedes'in IAA fuarındaki yeni EQE SUV" → "Mercedes EQE SUV 2024 IAA fuarı özellikleri"
- "Yapay zeka ve etik konuları tartışılıyor" → "yapay zeka etik sorunları 2024 tartışma"

TRANSCRIPTION (first 500 chars):
{text[:500]}

Return ONLY the search query text, nothing else. No quotes, no explanation."""

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Use fastest model for queries
                messages=[
                    {"role": "user", "content": query_prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            search_query = response.choices[0].message.content.strip()
            
            # Clean up query
            search_query = search_query.strip('"').strip("'").strip()
            
            # Limit length
            if len(search_query) > 150:
                search_query = search_query[:147] + "..."
            
            logger.info(f"✅ Groq generated search query: '{search_query}'")
            
            return search_query
            
        except Exception as e:
            logger.error(f"❌ Groq search query generation failed: {e}")
            return ""
