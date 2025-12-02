"""
Vision API Service
Provides document analysis using Gemini Vision API (and OpenAI GPT-4V as fallback)

Supports:
- PDF documents (multi-page)
- Images (PNG, JPG, WEBP, GIF)
- Scanned documents (OCR)
- Handwritten notes
- Diagrams and charts

Features:
- Text extraction (OCR)
- Content analysis
- Key points extraction
- Summary generation
- Combined analysis with transcription
"""

import os
import io
import base64
import logging
import json
import time
import tempfile
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path

import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF for PDF handling

from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============================================================================
# VISION API PROMPTS
# ============================================================================

DOCUMENT_ANALYSIS_PROMPT = """You are an expert document analyst. Analyze this document image and extract all relevant information.

## Your Tasks:
1. **Text Extraction**: Extract ALL text content from the document accurately
2. **Structure Analysis**: Identify document structure (headers, sections, lists, tables)
3. **Key Points**: Extract the main points and important information
4. **Summary**: Provide a concise summary of the document content

## Output Format (JSON):
{
    "extracted_text": "Full text content from the document...",
    "document_type": "lecture_notes|article|presentation|form|handwritten|diagram|other",
    "language": "detected language code (tr, en, de, etc.)",
    "structure": {
        "has_headers": true/false,
        "has_lists": true/false,
        "has_tables": true/false,
        "has_diagrams": true/false,
        "has_images": true/false
    },
    "key_points": [
        "Key point 1",
        "Key point 2"
    ],
    "summary": "Brief summary of the document content",
    "topics": ["Topic 1", "Topic 2"],
    "entities": {
        "people": ["Name 1", "Name 2"],
        "organizations": ["Org 1"],
        "dates": ["Date 1"],
        "locations": ["Location 1"]
    },
    "confidence": 0.95,
    "page_number": 1,
    "total_pages": 1
}

IMPORTANT:
- Extract ALL text, don't skip any content
- Preserve formatting and structure where possible
- If text is unclear or low quality, note it in confidence score
- For handwritten content, do your best to decipher
- Return valid JSON only, no markdown blocks"""


COMBINED_ANALYSIS_PROMPT = """You are an expert at synthesizing information from multiple sources. You have been given:

1. **AUDIO TRANSCRIPTION**: Text from an audio/video recording
2. **DOCUMENT CONTENT**: Text and analysis from a related document

Your task is to create a unified analysis that connects insights from both sources.

## Your Tasks:
1. **Cross-Reference**: Find connections and overlaps between the sources
2. **Identify Gaps**: Note what's in one source but not the other
3. **Unified Summary**: Create a comprehensive summary combining both sources
4. **Key Insights**: Extract the most important takeaways
5. **Study Guide**: If educational content, create study notes

## Output Format (JSON):
{
    "combined_summary": "Comprehensive summary combining both sources...",
    "key_insights": [
        "Insight 1 (combining both sources)",
        "Insight 2"
    ],
    "connections": [
        {
            "audio_reference": "What was said in audio",
            "document_reference": "Related content in document",
            "connection_type": "confirms|expands|contradicts|example"
        }
    ],
    "unique_to_audio": ["Points only mentioned in audio"],
    "unique_to_document": ["Points only in document"],
    "study_guide": {
        "main_topics": ["Topic 1", "Topic 2"],
        "definitions": [{"term": "...", "definition": "..."}],
        "key_facts": ["Fact 1", "Fact 2"],
        "review_questions": ["Question 1?", "Question 2?"]
    },
    "recommended_actions": ["Action 1", "Action 2"]
}

AUDIO TRANSCRIPTION:
{audio_text}

DOCUMENT CONTENT:
{document_text}

DOCUMENT ANALYSIS:
{document_analysis}

---
Analyze and return valid JSON only."""


# ============================================================================
# VISION SERVICE CLASS
# ============================================================================

class VisionService:
    """Service for document analysis using Vision APIs"""
    
    # Supported file types
    SUPPORTED_IMAGE_TYPES = {
        "image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"
    }
    SUPPORTED_DOCUMENT_TYPES = {
        "application/pdf"
    }
    SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_DOCUMENT_TYPES
    
    # Max file sizes
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB per image
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB for PDF
    MAX_PDF_PAGES = 50  # Max pages to process
    
    def __init__(self, provider: str = "gemini", model: str = None):
        """
        Initialize Vision Service
        
        Args:
            provider: Vision API provider ("gemini" or "openai")
            model: Specific model to use (defaults to best available)
        """
        self.provider = provider
        
        if provider == "gemini":
            self.model_name = model or "gemini-2.0-flash-exp"  # Best vision model
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"✅ Vision service initialized with Gemini: {self.model_name}")
        elif provider == "openai":
            self.model_name = model or "gpt-4o"
            # OpenAI client would be initialized here
            logger.info(f"✅ Vision service initialized with OpenAI: {self.model_name}")
        else:
            raise ValueError(f"Unsupported vision provider: {provider}")
    
    def validate_file(self, content_type: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate if file is supported
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if content_type not in self.SUPPORTED_TYPES:
            return False, f"Unsupported file type: {content_type}. Supported: PDF, PNG, JPG, WEBP, GIF"
        
        if content_type == "application/pdf":
            if file_size > self.MAX_PDF_SIZE:
                return False, f"PDF too large: {file_size / 1024 / 1024:.1f}MB. Max: 50MB"
        else:
            if file_size > self.MAX_IMAGE_SIZE:
                return False, f"Image too large: {file_size / 1024 / 1024:.1f}MB. Max: 20MB"
        
        return True, ""
    
    def _image_to_base64(self, image_data: bytes, content_type: str) -> str:
        """Convert image bytes to base64 string"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def _pdf_to_images(self, pdf_data: bytes, max_pages: int = None) -> List[Dict[str, Any]]:
        """
        Convert PDF pages to images for vision processing
        
        Args:
            pdf_data: PDF file bytes
            max_pages: Maximum pages to convert (None = all)
        
        Returns:
            List of dicts with page_number, image_data, dimensions
        """
        pages = []
        max_pages = max_pages or self.MAX_PDF_PAGES
        
        try:
            # Open PDF with PyMuPDF
            pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
            total_pages = len(pdf_doc)
            
            logger.info(f"📄 Processing PDF with {total_pages} pages (max: {max_pages})")
            
            for page_num in range(min(total_pages, max_pages)):
                page = pdf_doc[page_num]
                
                # Render page to image (300 DPI for good OCR quality)
                mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes
                img_data = pix.tobytes("png")
                
                pages.append({
                    "page_number": page_num + 1,
                    "total_pages": total_pages,
                    "image_data": img_data,
                    "width": pix.width,
                    "height": pix.height
                })
            
            pdf_doc.close()
            logger.info(f"✅ Converted {len(pages)} PDF pages to images")
            
        except Exception as e:
            logger.error(f"❌ PDF conversion error: {e}")
            raise
        
        return pages
    
    async def analyze_image(
        self, 
        image_data: bytes, 
        content_type: str,
        custom_prompt: str = None,
        page_info: Dict = None
    ) -> Dict[str, Any]:
        """
        Analyze a single image using Vision API
        
        Args:
            image_data: Image bytes
            content_type: MIME type
            custom_prompt: Optional custom analysis prompt
            page_info: Optional page number info for PDFs
        
        Returns:
            Analysis results dict
        """
        start_time = time.time()
        
        try:
            if self.provider == "gemini":
                # Create image part for Gemini
                image_part = {
                    "mime_type": content_type if content_type != "image/jpg" else "image/jpeg",
                    "data": image_data
                }
                
                # Build prompt
                prompt = custom_prompt or DOCUMENT_ANALYSIS_PROMPT
                if page_info:
                    prompt = prompt.replace(
                        '"page_number": 1',
                        f'"page_number": {page_info.get("page_number", 1)}'
                    ).replace(
                        '"total_pages": 1',
                        f'"total_pages": {page_info.get("total_pages", 1)}'
                    )
                
                # Generate response
                response = self.model.generate_content(
                    [prompt, image_part],
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,  # Low temperature for accurate extraction
                        max_output_tokens=8192
                    )
                )
                
                # Parse response
                response_text = response.text.strip()
                
                # Clean up JSON if wrapped in markdown
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                result = json.loads(response_text.strip())
                result["processing_time"] = time.time() - start_time
                result["provider"] = self.provider
                result["model"] = self.model_name
                
                return result
                
            elif self.provider == "openai":
                # OpenAI GPT-4V implementation
                # TODO: Implement OpenAI Vision
                raise NotImplementedError("OpenAI Vision not yet implemented")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse Vision API response: {e}")
            logger.debug(f"Raw response: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
            return {
                "error": "Failed to parse response",
                "raw_response": response_text if 'response_text' in locals() else None,
                "processing_time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"❌ Vision API error: {e}")
            return {
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def analyze_document(
        self,
        file_data: bytes,
        content_type: str,
        filename: str = None,
        custom_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Analyze a document (PDF or image)
        
        Args:
            file_data: File bytes
            content_type: MIME type
            filename: Original filename
            custom_prompt: Optional custom analysis prompt
        
        Returns:
            Complete analysis results
        """
        start_time = time.time()
        
        # Validate file
        is_valid, error_msg = self.validate_file(content_type, len(file_data))
        if not is_valid:
            return {"error": error_msg}
        
        logger.info(f"📄 Analyzing document: {filename or 'unknown'} ({content_type})")
        
        try:
            if content_type == "application/pdf":
                # Process PDF - convert pages to images and analyze each
                pages = self._pdf_to_images(file_data)
                
                all_text = []
                all_key_points = []
                page_analyses = []
                
                for page in pages:
                    page_result = await self.analyze_image(
                        page["image_data"],
                        "image/png",
                        custom_prompt,
                        page_info={
                            "page_number": page["page_number"],
                            "total_pages": page["total_pages"]
                        }
                    )
                    
                    if "error" not in page_result:
                        all_text.append(page_result.get("extracted_text", ""))
                        all_key_points.extend(page_result.get("key_points", []))
                        page_analyses.append({
                            "page": page["page_number"],
                            "summary": page_result.get("summary", ""),
                            "topics": page_result.get("topics", [])
                        })
                    else:
                        logger.warning(f"⚠️ Page {page['page_number']} analysis failed: {page_result.get('error')}")
                
                # Combine results
                result = {
                    "extracted_text": "\n\n---\n\n".join(all_text),
                    "document_type": "pdf",
                    "language": page_analyses[0].get("language", "unknown") if page_analyses else "unknown",
                    "page_count": len(pages),
                    "total_pages": pages[0]["total_pages"] if pages else 0,
                    "key_points": list(set(all_key_points))[:20],  # Deduplicate, limit to 20
                    "page_analyses": page_analyses,
                    "processing_time": time.time() - start_time,
                    "provider": self.provider,
                    "model": self.model_name
                }
                
                # Generate overall summary if multiple pages
                if len(pages) > 1:
                    result["summary"] = await self._generate_document_summary(result["extracted_text"])
                elif page_analyses:
                    result["summary"] = page_analyses[0].get("summary", "")
                
                return result
                
            else:
                # Single image analysis
                result = await self.analyze_image(file_data, content_type, custom_prompt)
                result["page_count"] = 1
                result["total_pages"] = 1
                return result
                
        except Exception as e:
            logger.error(f"❌ Document analysis error: {e}", exc_info=True)
            return {
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _generate_document_summary(self, full_text: str, max_length: int = 500) -> str:
        """Generate a summary of the full document text"""
        try:
            prompt = f"""Summarize the following document content in 2-3 paragraphs (max {max_length} words):

{full_text[:10000]}  # Limit input text

Provide a concise, informative summary that captures the main points."""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1024
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"❌ Summary generation error: {e}")
            return "Summary generation failed"
    
    async def create_combined_analysis(
        self,
        audio_text: str,
        document_text: str,
        document_analysis: Dict[str, Any],
        custom_instructions: str = None
    ) -> Dict[str, Any]:
        """
        Create a combined analysis of audio transcription and document content
        
        Args:
            audio_text: Transcription text from audio
            document_text: Extracted text from document
            document_analysis: Full document analysis results
            custom_instructions: Optional custom analysis instructions
        
        Returns:
            Combined analysis results
        """
        start_time = time.time()
        
        try:
            # Build prompt
            prompt = COMBINED_ANALYSIS_PROMPT.format(
                audio_text=audio_text[:8000],  # Limit length
                document_text=document_text[:8000],
                document_analysis=json.dumps(document_analysis, indent=2)[:3000]
            )
            
            if custom_instructions:
                prompt += f"\n\nAdditional Instructions: {custom_instructions}"
            
            # Generate combined analysis
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=8192
                )
            )
            
            response_text = response.text.strip()
            
            # Clean up JSON
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            result = json.loads(response_text.strip())
            result["processing_time"] = time.time() - start_time
            result["provider"] = self.provider
            result["model"] = self.model_name
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse combined analysis: {e}")
            return {
                "error": "Failed to parse response",
                "combined_summary": response_text if 'response_text' in locals() else None,
                "processing_time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"❌ Combined analysis error: {e}")
            return {
                "error": str(e),
                "processing_time": time.time() - start_time
            }


# ============================================================================
# SERVICE FACTORY
# ============================================================================

def get_vision_service(provider: str = "gemini", model: str = None) -> VisionService:
    """
    Factory function to get Vision Service instance
    
    Args:
        provider: "gemini" or "openai"
        model: Optional specific model name
    
    Returns:
        VisionService instance
    """
    return VisionService(provider=provider, model=model)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_supported_document_types() -> List[str]:
    """Get list of supported document MIME types"""
    return list(VisionService.SUPPORTED_TYPES)


def estimate_vision_credits(
    file_size: int,
    content_type: str,
    page_count: int = 1
) -> float:
    """
    Estimate credits needed for vision analysis
    
    Args:
        file_size: File size in bytes
        content_type: MIME type
        page_count: Number of pages (for PDFs)
    
    Returns:
        Estimated credits
    """
    # Base costs from pricing
    COST_PER_PAGE = 0.5
    COST_PER_IMAGE = 0.3
    
    if content_type == "application/pdf":
        return page_count * COST_PER_PAGE
    else:
        return COST_PER_IMAGE


async def quick_ocr(image_data: bytes, content_type: str) -> str:
    """
    Quick OCR - just extract text, no analysis
    
    Args:
        image_data: Image bytes
        content_type: MIME type
    
    Returns:
        Extracted text
    """
    service = get_vision_service()
    
    simple_prompt = """Extract ALL text from this image. Return ONLY the text content, nothing else.
If no text is visible, return "NO_TEXT_FOUND"."""
    
    try:
        image_part = {
            "mime_type": content_type,
            "data": image_data
        }
        
        response = service.model.generate_content(
            [simple_prompt, image_part],
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=4096
            )
        )
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"❌ Quick OCR error: {e}")
        return ""
