"""
LeMUR Service Wrapper
AssemblyAI LeMUR (LLM for speech) işlemleri
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class LemurSummary:
    """LeMUR özet sonucu"""
    text: str
    model: str
    usage: Dict[str, int]  # {"input_tokens": 1000, "output_tokens": 200}


@dataclass
class LemurAnswer:
    """LeMUR Q&A cevabı"""
    question: str
    answer: str


@dataclass
class LemurActionItems:
    """LeMUR action items"""
    items: List[str]


class LemurService:
    """LeMUR işlemleri için servis sınıfı"""
    
    def __init__(self, config):
        """
        Args:
            config: LemurConfig instance
        """
        self.config = config
    
    def generate_summary(
        self, 
        transcript, 
        context: Optional[str] = None
    ) -> Optional[LemurSummary]:
        """
        Transkript özeti oluştur
        
        Args:
            transcript: AssemblyAI transcript object
            context: Ek bağlam bilgisi
        
        Returns:
            LemurSummary veya None
        """
        if not self.config.enabled or not self.config.generate_summary:
            return None
        
        logger.info("📝 Generating LeMUR summary...")
        
        try:
            # Context hazırla
            final_context = context or self.config.summary_context or ""
            
            # Summary type'a göre format
            answer_format = None
            if self.config.summary_type.value == "bullets":
                answer_format = "Concise bullet points"
            elif self.config.summary_type.value == "paragraph":
                answer_format = "A comprehensive paragraph"
            elif self.config.summary_type.value == "headline":
                answer_format = "A single headline sentence"
            
            # LeMUR summary endpoint
            summary_response = transcript.lemur.summarize(
                context=final_context,
                answer_format=answer_format,
                final_model=self.config.model.value
            )
            
            result = LemurSummary(
                text=summary_response.response,
                model=getattr(summary_response, 'model', 'unknown'),
                usage=getattr(summary_response, 'usage', {})
            )
            
            logger.info(f"✅ Summary generated ({len(result.text)} chars)")
            return result
            
        except Exception as e:
            logger.error(f"❌ LeMUR summary error: {e}")
            return None
    
    def ask_questions(
        self, 
        transcript,
        questions: Optional[List[str]] = None
    ) -> List[LemurAnswer]:
        """
        Transkript hakkında sorular sor
        
        Args:
            transcript: AssemblyAI transcript object
            questions: Soru listesi (None ise default sorular)
        
        Returns:
            LemurAnswer listesi
        """
        if not self.config.enabled or not self.config.enable_qa:
            return []
        
        # Soruları hazırla
        final_questions = questions or self.config.default_questions
        
        if not final_questions:
            return []
        
        logger.info(f"❓ Asking {len(final_questions)} questions via LeMUR...")
        
        answers = []
        
        try:
            # Her soru için LeMUR question endpoint
            for question in final_questions:
                logger.info(f"   Q: {question}")
                
                response = transcript.lemur.question(
                    question,
                    final_model=self.config.model.value
                )
                
                answer = LemurAnswer(
                    question=question,
                    answer=response.response
                )
                
                answers.append(answer)
                logger.info(f"   A: {answer.answer[:100]}...")
            
            logger.info(f"✅ {len(answers)} questions answered")
            return answers
            
        except Exception as e:
            logger.error(f"❌ LeMUR Q&A error: {e}")
            return answers  # Return what we have so far
    
    def extract_action_items(self, transcript) -> Optional[LemurActionItems]:
        """
        Yapılacaklar listesi çıkar
        
        Args:
            transcript: AssemblyAI transcript object
        
        Returns:
            LemurActionItems veya None
        """
        if not self.config.enabled or not self.config.extract_action_items:
            return None
        
        logger.info("📋 Extracting action items via LeMUR...")
        
        try:
            prompt = """
            Extract all action items from this transcript.
            
            Rules:
            - Only extract clear, actionable tasks
            - Include who is responsible if mentioned
            - Include deadlines if mentioned
            - Format as a numbered list
            - Return ONLY the list, no preamble
            
            If there are no action items, respond with: "No action items found"
            """
            
            response = transcript.lemur.task(
                prompt=prompt,
                final_model=self.config.model.value
            )
            
            # Parse response
            text = response.response.strip()
            
            if "no action items" in text.lower():
                items = []
            else:
                # Split by lines and clean
                items = [
                    line.strip() 
                    for line in text.split('\n') 
                    if line.strip() and not line.strip().startswith('#')
                ]
            
            result = LemurActionItems(items=items)
            
            logger.info(f"✅ Extracted {len(result.items)} action items")
            return result
            
        except Exception as e:
            logger.error(f"❌ LeMUR action items error: {e}")
            return None
    
    def run_custom_tasks(
        self, 
        transcript,
        prompts: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        Özel promptlar çalıştır
        
        Args:
            transcript: AssemblyAI transcript object
            prompts: Custom prompt listesi
        
        Returns:
            [{"prompt": "...", "response": "..."}]
        """
        if not self.config.enabled:
            return []
        
        final_prompts = prompts or self.config.custom_prompts
        
        if not final_prompts:
            return []
        
        logger.info(f"🔧 Running {len(final_prompts)} custom LeMUR tasks...")
        
        results = []
        
        try:
            for i, prompt in enumerate(final_prompts, 1):
                logger.info(f"   Task {i}/{len(final_prompts)}: {prompt[:80]}...")
                
                response = transcript.lemur.task(
                    prompt=prompt,
                    final_model=self.config.model.value,
                    max_output_size=self.config.max_output_size,
                    temperature=self.config.temperature
                )
                
                results.append({
                    "prompt": prompt,
                    "response": response.response
                })
            
            logger.info(f"✅ {len(results)} custom tasks completed")
            return results
            
        except Exception as e:
            logger.error(f"❌ LeMUR custom tasks error: {e}")
            return results
    
    def process_all(
        self, 
        transcript,
        custom_context: Optional[str] = None,
        custom_questions: Optional[List[str]] = None,
        custom_prompts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Tüm LeMUR işlemlerini çalıştır
        
        Args:
            transcript: AssemblyAI transcript object
            custom_context: Özet için özel context
            custom_questions: Özel sorular
            custom_prompts: Özel promptlar
        
        Returns:
            Tüm LeMUR sonuçları
        """
        logger.info("=" * 80)
        logger.info("🧠 LEMUR PROCESSING")
        logger.info("=" * 80)
        
        results = {}
        
        # Summary
        summary = self.generate_summary(transcript, custom_context)
        if summary:
            results["summary"] = asdict(summary)
        
        # Q&A
        qa_results = self.ask_questions(transcript, custom_questions)
        if qa_results:
            results["questions_and_answers"] = [asdict(qa) for qa in qa_results]
        
        # Action Items
        action_items = self.extract_action_items(transcript)
        if action_items:
            results["action_items"] = asdict(action_items)
        
        # Custom Tasks
        custom_results = self.run_custom_tasks(transcript, custom_prompts)
        if custom_results:
            results["custom_tasks"] = custom_results
        
        logger.info("=" * 80)
        
        return results
