"""
Web Search Service using Tavily AI
Enriches AI prompts with relevant web content for better accuracy
"""

import logging
from typing import Dict, Any, List, Optional
from tavily import TavilyClient
from app.settings import get_settings

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for web search to enrich AI prompts with context"""
    
    def __init__(self):
        """Initialize Tavily web search client"""
        settings = get_settings()
        self.api_key = settings.TAVILY_API_KEY
        self.enabled = settings.ENABLE_WEB_SEARCH and bool(self.api_key)
        self.max_results = settings.WEB_SEARCH_MAX_RESULTS
        
        if self.enabled:
            try:
                self.client = TavilyClient(api_key=self.api_key)
                logger.info(f"✅ Tavily web search initialized (max {self.max_results} results)")
            except Exception as e:
                logger.error(f"❌ Tavily initialization failed: {e}")
                self.enabled = False
        else:
            logger.info("⚠️  Web search disabled (no API key or ENABLE_WEB_SEARCH=false)")
    
    def is_enabled(self) -> bool:
        """Check if web search is enabled"""
        return self.enabled
    
    async def search_context(
        self,
        query: str,
        language: str = "tr",
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search web for relevant context to enrich AI prompts
        
        Args:
            query: Search query (extracted keywords from transcription)
            language: Language code (tr, en, etc.)
            max_results: Number of results (defaults to config value)
            
        Returns:
            Dict with search results and formatted context string
        """
        if not self.enabled:
            logger.warning("⚠️  Web search is disabled")
            return {
                "success": False,
                "results": [],
                "context": "",
                "error": "Web search not enabled"
            }
        
        if not query or len(query.strip()) < 5:
            logger.warning("⚠️  Query too short for web search")
            return {
                "success": False,
                "results": [],
                "context": "",
                "error": "Query too short"
            }
        
        try:
            num_results = max_results or self.max_results
            logger.info(f"🔍 Searching web: '{query}' (language: {language}, max: {num_results})")
            
            # Tavily search with language filter
            response = self.client.search(
                query=query,
                search_depth="basic",  # "basic" or "advanced"
                max_results=num_results,
                include_answer=True,  # Get AI-generated answer
                include_raw_content=False,  # Don't need full HTML
                include_images=False
            )
            
            results = response.get("results", [])
            answer = response.get("answer", "")
            
            if not results:
                logger.warning(f"⚠️  No search results for: {query}")
                return {
                    "success": False,
                    "results": [],
                    "context": "",
                    "error": "No results found"
                }
            
            # Format context for AI prompt
            context_parts = []
            
            # Add Tavily's AI-generated answer if available
            if answer:
                context_parts.append(f"**Web Summary:**\n{answer}\n")
            
            # Add top results
            context_parts.append("**Relevant Sources:**")
            for i, result in enumerate(results[:num_results], 1):
                title = result.get("title", "Untitled")
                content = result.get("content", "")
                url = result.get("url", "")
                
                # Truncate content to ~200 chars
                content_preview = content[:200] + "..." if len(content) > 200 else content
                
                context_parts.append(f"{i}. **{title}**")
                context_parts.append(f"   {content_preview}")
                context_parts.append(f"   Source: {url}\n")
            
            formatted_context = "\n".join(context_parts)
            
            logger.info(f"✅ Found {len(results)} web results")
            logger.info(f"   AI Answer: {'Yes' if answer else 'No'}")
            logger.info(f"   Context length: {len(formatted_context)} chars")
            
            return {
                "success": True,
                "results": results,
                "answer": answer,
                "context": formatted_context,
                "num_results": len(results),
                "query_used": query
            }
            
        except Exception as e:
            logger.error(f"❌ Web search failed: {e}")
            return {
                "success": False,
                "results": [],
                "context": "",
                "error": str(e)
            }
    
    async def generate_search_query_with_ai(self, text: str, language: str = "tr") -> str:
        """
        Generate intelligent search query using AI (Gemini/OpenAI)
        
        AI analyzes transcription and creates focused search query for Tavily
        
        Args:
            text: Transcription text
            language: Language code
            
        Returns:
            AI-generated search query optimized for web search
        """
        try:
            from app.services.gemini_service import get_gemini_service
            ai_service = get_gemini_service()
            
            if not ai_service.is_enabled():
                logger.warning("⚠️  AI service not available, falling back to regex extraction")
                return self.extract_keywords(text, max_keywords=5)
            
            lang_name = {"tr": "Turkish", "en": "English", "de": "German", "fr": "French"}.get(language, "Turkish")
            
            # AI prompt for search query generation
            query_prompt = f"""Analyze this {lang_name} transcription and create an OPTIMAL search query for Tavily web search.

GOAL: Extract the main topic, key entities, and important context to find relevant information online.

RULES:
1. **Identify Main Topic**: What is this text primarily about?
2. **Extract Key Entities**: Proper nouns, brand names, people, places, products, events
3. **Include Context**: Important terms that clarify the topic
4. **Prioritize Specificity**: Specific terms (brand names, model numbers) over generic words
5. **Remove Filler**: No "um", "uh", filler words, hesitations
6. **Optimal Length**: 5-15 words, max 150 characters
7. **Search-Friendly**: Use terms people would Google to find this information

EXAMPLES:
- Transcription: "Togg'un yeni elektrikli aracı T8X modelinin özellikleri ve fiyatı açıklandı"
  → Query: "Togg T8X elektrikli araç özellikleri fiyat"

- Transcription: "2024 IAA fuarında Mercedes-Benz'in yeni EQE SUV'u tanıtıldı"
  → Query: "Mercedes EQE SUV 2024 IAA fuarı"

- Transcription: "Elon Musk'ın SpaceX şirketi Starship roketini başarıyla fırlattı"
  → Query: "SpaceX Starship rocket test launch"

TRANSCRIPTION TEXT:
---
{text[:500]}
---

Return ONLY the search query (plain text, no JSON, no explanation, just the query):"""
            
            logger.info("🤖 Generating search query with AI...")
            
            # Both OpenAI and Gemini now use OpenAI SDK format (unified interface)
            response = ai_service.client.chat.completions.create(
                model=ai_service.model_name,
                messages=[
                    {"role": "system", "content": "You are a search query expert. Return only the optimized search query, nothing else."},
                    {"role": "user", "content": query_prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            # Check for empty response (safety block or error)
            if not response.choices or not response.choices[0].message.content:
                logger.warning(f"⚠️  AI returned empty response, using fallback")
                return self.extract_keywords(text, max_keywords=5)
            
            # Extract search query from response
            search_query = response.choices[0].message.content.strip()
            
            # Clean up query
            search_query = search_query.replace('"', '').replace("'", '').strip()
            
            # Validate query
            if not search_query or len(search_query) < 10:
                logger.warning(f"⚠️  AI query too short: '{search_query}', using fallback")
                return self.extract_keywords(text, max_keywords=5)
            
            # Truncate if too long
            if len(search_query) > 200:
                search_query = search_query[:200].rsplit(' ', 1)[0]
            
            logger.info(f"✅ AI generated search query ({len(search_query)} chars): {search_query}")
            return search_query
            
        except Exception as e:
            logger.error(f"❌ AI query generation failed: {e}")
            logger.info("📝 Falling back to keyword extraction")
            return self.extract_keywords(text, max_keywords=5)
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> str:
        """
        Fallback: Extract key topics from transcription using regex
        
        Used when AI service is unavailable
        
        Args:
            text: Transcription text
            max_keywords: Maximum keywords to extract
            
        Returns:
            Search query string
        """
        import re
        from collections import Counter
        
        # Clean text
        text = text.strip()
        
        # Strategy 1: Extract important terms FIRST (proper nouns, brands, acronyms)
        filler_words = {
            "yani", "işte", "hani", "şey", "filan", "vb", "vs", "gibi",
            "bir", "bu", "şu", "o", "ve", "veya", "ile", "için", "daha",
            "çok", "az", "var", "yok", "mı", "mi", "mu", "mü", "de", "da",
            "ardından", "içinde", "modeli", "uygun", "yeni", "fiyatlı",
            "tanıtılmasının", "açıklamalarda", "bulunan", "duyurdu",
            "bakar", "mısınız", "kayanın", "güzellığına"
        }
        
        # Extract capitalized words (proper nouns, brands, names)
        capitalized = re.findall(r'\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]+\b', text)
        
        # Extract ALL CAPS (acronyms like IAA, CEO, T8X)
        acronyms = re.findall(r'\b[A-ZÇĞİÖŞÜ]{2,}\b', text)
        
        # Extract alphanumeric model names (T8X, T10F, etc.)
        model_names = re.findall(r'\b[A-Z]\d+[A-Z]?\b', text)
        
        # Extract words with 5+ chars (meaningful content words)
        content_words = re.findall(r'\b[a-zçğıöşüA-ZÇĞİÖŞÜ]{5,}\b', text)
        content_words = [w for w in content_words if w.lower() not in filler_words]
        
        # Combine important terms
        important_terms = list(set(capitalized + acronyms + model_names))
        important_terms = [w for w in important_terms if w.lower() not in filler_words]
        
        # Strategy 2: Build query from important terms + content words
        if important_terms:
            # We have proper nouns/brands - prioritize them
            query_parts = important_terms[:5]  # Top 5 important terms
            
            # Add meaningful content words for context
            for word in content_words[:5]:
                if word not in query_parts and len(" ".join(query_parts + [word])) <= 200:
                    query_parts.append(word)
            
            query = " ".join(query_parts)
        else:
            # No proper nouns found - use content words
            word_counts = Counter(content_words)
            top_words = [word for word, count in word_counts.most_common(8)]
            query = " ".join(top_words)
        
        # Strategy 3: If query too short, get first meaningful sentence
        if not query or len(query) < 20:
            sentences = re.split(r'[.!?]+', text)
            for sent in sentences[:3]:  # Check first 3 sentences
                sent = sent.strip()
                if len(sent) >= 30:  # At least 30 chars
                    query = sent
                    break
        
        # Final fallback: Take first 150 chars
        if not query or len(query) < 10:
            query = text[:150].strip()
        
        # Trim to reasonable length (Tavily works best with focused queries)
        if len(query) > 200:
            query = query[:200].rsplit(' ', 1)[0]  # Cut at last word boundary
        
        logger.info(f"🔑 Extracted search query ({len(query)} chars): {query[:100]}...")
        return query


# Singleton instance
_instance = None

def get_web_search_service() -> WebSearchService:
    """Get or create singleton WebSearchService instance"""
    global _instance
    if _instance is None:
        _instance = WebSearchService()
    return _instance
