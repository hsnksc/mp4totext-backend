"""
Gemini AI Enhancement Service
"""

import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiEnhancement:
    """
    Gemini AI text enhancement service
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Gemini enhancement service
        
        Args:
            api_key: Google Gemini API key
            model_name: Gemini model name (default: gemini-2.5-flash)
        """
        if not api_key:
            raise ValueError("Gemini API key is required")
        
        self.api_key = api_key
        self.model_name = model_name
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        logger.info(f"Gemini enhancement initialized with model: {model_name}")
    
    def enhance_transcription(self, text: str, language: str = "tr") -> Dict[str, Any]:
        """
        Enhance transcription text using Gemini AI
        
        Args:
            text: Original transcription text
            language: Language code (default: tr for Turkish)
        
        Returns:
            Dict with enhanced_text, improvements, and metadata
        """
        try:
            # Create enhancement prompt
            prompt = self._create_enhancement_prompt(text, language)
            
            # Generate enhanced text
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error("Gemini API returned empty response")
                return {
                    "enhanced_text": text,
                    "improvements": [],
                    "status": "failed",
                    "error": "Empty response from Gemini API"
                }
            
            enhanced_text = response.text.strip()
            
            # Analyze improvements
            improvements = self._analyze_improvements(text, enhanced_text)
            
            return {
                "enhanced_text": enhanced_text,
                "improvements": improvements,
                "status": "completed",
                "model": self.model_name,
                "metadata": {
                    "original_length": len(text),
                    "enhanced_length": len(enhanced_text),
                    "language": language
                }
            }
            
        except Exception as e:
            logger.error(f"Gemini enhancement failed: {e}", exc_info=True)
            return {
                "enhanced_text": text,
                "improvements": [],
                "status": "failed",
                "error": str(e)
            }
    
    def generate_summary(self, text: str, language: str = "tr") -> Optional[str]:
        """
        Generate summary of transcription
        
        Args:
            text: Transcription text
            language: Language code
        
        Returns:
            Summary text or None if failed
        """
        try:
            prompt = self._create_summary_prompt(text, language)
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            return None
    
    def _create_enhancement_prompt(self, text: str, language: str) -> str:
        """Create prompt for text enhancement"""
        
        if language == "tr":
            return f"""Aşağıdaki ses kaydından elde edilen transkripsiyon metnini iyileştir:

- Noktalama işaretlerini düzelt ve ekle
- Yazım hatalarını düzelt
- Cümle yapısını iyileştir
- Paragrafları düzenle
- Anlaşılırlığı artır

Sadece düzeltilmiş metni döndür, açıklama ekleme.

Orijinal metin:
{text}
"""
        else:
            return f"""Improve the following transcription text:

- Fix and add punctuation
- Correct spelling errors
- Improve sentence structure
- Organize paragraphs
- Enhance readability

Return only the corrected text, no explanations.

Original text:
{text}
"""
    
    def _create_summary_prompt(self, text: str, language: str) -> str:
        """Create prompt for summary generation"""
        
        if language == "tr":
            return f"""Aşağıdaki transkripsiyon metninin kısa bir özetini çıkar:

{text}

Özet (maksimum 3-5 cümle):
"""
        else:
            return f"""Create a brief summary of the following transcription:

{text}

Summary (maximum 3-5 sentences):
"""
    
    def _analyze_improvements(self, original: str, enhanced: str) -> List[str]:
        """Analyze what improvements were made"""
        improvements = []
        
        # Count punctuation additions
        original_punct = sum(1 for c in original if c in '.,!?;:')
        enhanced_punct = sum(1 for c in enhanced if c in '.,!?;:')
        if enhanced_punct > original_punct:
            improvements.append(f"Added {enhanced_punct - original_punct} punctuation marks")
        
        # Count paragraph breaks
        original_paras = original.count('\n\n')
        enhanced_paras = enhanced.count('\n\n')
        if enhanced_paras > original_paras:
            improvements.append(f"Added {enhanced_paras - original_paras} paragraph breaks")
        
        # Length changes
        length_diff = len(enhanced) - len(original)
        if abs(length_diff) > 50:
            if length_diff > 0:
                improvements.append(f"Expanded text by {length_diff} characters")
            else:
                improvements.append(f"Condensed text by {abs(length_diff)} characters")
        
        return improvements if improvements else ["Text enhanced"]


def create_gemini_service(api_key: Optional[str], model_name: str = "gemini-1.5-flash") -> Optional[GeminiEnhancement]:
    """
    Create Gemini enhancement service instance
    
    Args:
        api_key: Gemini API key
        model_name: Model name
    
    Returns:
        GeminiEnhancement instance or None if API key not provided
    """
    if not api_key:
        logger.warning("Gemini API key not provided, enhancement disabled")
        return None
    
    try:
        return GeminiEnhancement(api_key, model_name)
    except Exception as e:
        logger.error(f"Failed to create Gemini service: {e}", exc_info=True)
        return None
