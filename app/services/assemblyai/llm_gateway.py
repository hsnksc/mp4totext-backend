"""
LLM Gateway Service Wrapper
Direct REST API calls (Python SDK v0.46.0 doesn't have LLM Gateway yet)
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import httpx
from app.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

@dataclass
class LLMSummary:
    """LLM Gateway summary result"""
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMAnswer:
    """LLM Gateway Q&A answer"""
    question: str
    answer: str


@dataclass
class LLMActionItems:
    """LLM Gateway action items"""
    items: List[str]


# ============================================================================
# LLM GATEWAY SERVICE (via Lemur API)
# ============================================================================

class LLMGatewayService:
    """
    LLM Gateway operations service
    Direct REST API implementation (SDK not available yet)
    """
    
    BASE_URL = "https://llm-gateway.assemblyai.com/v1"
    
    def __init__(self, config):
        """
        Args:
            config: LLMGatewayConfig instance
        """
        self.config = config
        self.api_key = settings.ASSEMBLYAI_API_KEY
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        logger.info("🤖 LLM Gateway initialized (Direct REST API)")
        logger.info(f"   Model: {self.config.model.value}")
        logger.info(f"   Temperature: {self.config.temperature}")
        logger.info(f"   Max tokens: {self.config.max_tokens}")
    
    def _call_api(self, prompt: str, transcript_text: str) -> Dict[str, Any]:
        """Call LLM Gateway REST API with basic retry handling"""
        attempts = self.config.max_retries
        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": self.config.model.value,
                            "messages": [
                                {
                                    "role": "user",
                                    "content": f"{prompt}\n\nTranscript:\n{transcript_text}"
                                }
                            ],
                            "max_tokens": self.config.max_tokens,
                            "temperature": self.config.temperature
                        }
                    )
                if response.status_code == 429 and attempt < attempts:
                    wait_time = self.config.retry_backoff_seconds * attempt
                    logger.warning(f"⚠️ LLM Gateway rate limited (attempt {attempt}/{attempts}). Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as http_error:
                if http_error.response.status_code == 429 and attempt < attempts:
                    wait_time = self.config.retry_backoff_seconds * attempt
                    logger.warning(f"⚠️ LLM Gateway 429 response (attempt {attempt}/{attempts}). Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"LLM Gateway HTTP error: {http_error}")
                raise
            except Exception as e:
                logger.error(f"LLM Gateway API error: {e}")
                raise
        raise RuntimeError("LLM Gateway API retry limit exceeded")
    
    def generate_summary(
        self, 
        transcript_text: str,
        context: Optional[str] = None
    ) -> Optional[LLMSummary]:
        """Generate transcript summary via LLM Gateway REST API"""
        if not self.config.enabled or not self.config.generate_summary:
            return None
        
        logger.info("📝 Generating summary via LLM Gateway...")
        
        try:
            prompt = self.config.summary_prompt
            if context:
                prompt = f"Context: {context}\n\n{prompt}"
            
            response = self._call_api(prompt, transcript_text)
            
            content = response["choices"][0]["message"]["content"]
            usage = response.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            result = LLMSummary(
                text=content,
                model=self.config.model.value,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
            
            logger.info(f"✅ Summary generated ({len(result.text)} chars)")
            logger.info(f"   Tokens: {result.total_tokens or 'n/a'}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Summary error: {e}")
            return None
    
    def ask_questions(
        self, 
        transcript_text: str,
        questions: Optional[List[str]] = None
    ) -> List[LLMAnswer]:
        """Ask questions about transcript via LLM Gateway REST API"""
        if not self.config.enabled or not self.config.enable_qa:
            return []
        
        final_questions = questions or self.config.questions
        if not final_questions:
            return []
        
        logger.info(f"❓ Asking {len(final_questions)} questions...")
        
        answers = []
        try:
            for q in final_questions:
                response = self._call_api(
                    f"Answer this question based on the transcript: {q}",
                    transcript_text
                )
                answer = LLMAnswer(
                    question=q,
                    answer=response["choices"][0]["message"]["content"]
                )
                answers.append(answer)
            
            logger.info(f"✅ {len(answers)} questions answered")
            return answers
            
        except Exception as e:
            logger.error(f"❌ Q&A error: {e}")
            return answers
    
    def extract_action_items(
        self, 
        transcript_text: str
    ) -> Optional[LLMActionItems]:
        """Extract action items via LLM Gateway REST API"""
        if not self.config.enabled or not self.config.extract_action_items:
            return None
        
        logger.info("📋 Extracting action items...")
        
        try:
            response = self._call_api(
                self.config.action_items_prompt,
                transcript_text
            )
            
            text = response["choices"][0]["message"]["content"].strip()
            
            if "no action items" in text.lower():
                items = []
            else:
                items = [line.strip() for line in text.split('\n') if line.strip()]
            
            result = LLMActionItems(items=items)
            logger.info(f"✅ Extracted {len(result.items)} action items")
            return result
            
        except Exception as e:
            logger.error(f"❌ Action items error: {e}")
            return None
    
    def run_custom_tasks(
        self, 
        transcript_text: str,
        prompts: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """Run custom prompts via LLM Gateway REST API"""
        if not self.config.enabled:
            return []
        
        final_prompts = prompts or self.config.custom_prompts
        if not final_prompts:
            return []
        
        logger.info(f"🔧 Running {len(final_prompts)} custom tasks...")
        
        results = []
        try:
            for prompt in final_prompts:
                response = self._call_api(prompt, transcript_text)
                results.append({
                    "prompt": prompt,
                    "response": response["choices"][0]["message"]["content"]
                })
            
            logger.info(f"✅ {len(results)} custom tasks completed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Custom tasks error: {e}")
            return results
    
    def process_all(
        self, 
        transcript_text: str,
        custom_context: Optional[str] = None,
        custom_questions: Optional[List[str]] = None,
        custom_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run all LLM Gateway operations
        
        Args:
            transcript_text: Full transcript text
            custom_context: Custom context for summary
            custom_questions: Custom questions
            custom_prompts: Custom prompts
        
        Returns:
            All LLM Gateway results
        """
        logger.info("=" * 80)
        logger.info("🧠 LLM GATEWAY PROCESSING")
        logger.info("=" * 80)
        
        results = {}
        
        # Summary
        summary = self.generate_summary(transcript_text, custom_context)
        if summary:
            results["summary"] = asdict(summary)
        
        # Q&A
        qa_results = self.ask_questions(transcript_text, custom_questions)
        if qa_results:
            results["questions_and_answers"] = [asdict(qa) for qa in qa_results]
        
        # Action Items
        action_items = self.extract_action_items(transcript_text)
        if action_items:
            results["action_items"] = asdict(action_items)
        
        # Custom Tasks
        custom_results = self.run_custom_tasks(transcript_text, custom_prompts)
        if custom_results:
            results["custom_tasks"] = custom_results
        
        logger.info("=" * 80)
        
        return results
