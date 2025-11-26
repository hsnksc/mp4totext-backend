"""
Speech Understanding Results Parser
AssemblyAI audio intelligence sonuçlarını işle
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class SpeakerInfo:
    """Speaker bilgisi"""
    id: str
    label: str


@dataclass
class Utterance:
    """Konuşma segmenti (speaker-based)"""
    speaker: str
    start: float
    end: float
    text: str
    confidence: float


@dataclass
class SentimentResult:
    """Cümle bazında duygu analizi"""
    text: str
    sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    confidence: float
    start: float
    end: float


@dataclass
class Chapter:
    """Otomatik bölüm"""
    gist: str  # Kısa özet
    headline: str  # Başlık
    summary: str  # Detaylı özet
    start: float
    end: float


@dataclass
class Entity:
    """Tespit edilen varlık"""
    entity_type: str  # person_name, location, date, etc.
    text: str
    start: float
    end: float


@dataclass
class Topic:
    """Tespit edilen konu (IAB Category)"""
    text: str
    labels: List[Dict[str, Any]]  # [{"label": "Business>Marketing", "relevance": 0.85}]
    timestamp: Dict[str, float]  # {"start": 0, "end": 100}


@dataclass
class ContentSafetyResult:
    """İçerik güvenliği"""
    text: str
    labels: List[Dict[str, Any]]  # [{"label": "violence", "confidence": 0.95}]
    timestamp: Dict[str, float]
    severity_score_summary: Dict[str, float]  # {"low": 0.1, "medium": 0.3, "high": 0.6}


@dataclass
class Highlight:
    """Anahtar kelime"""
    text: str
    count: int
    rank: float
    timestamps: List[Dict[str, float]]


class SpeechUnderstandingParser:
    """AssemblyAI Speech Understanding sonuçlarını parse eder"""
    
    @staticmethod
    def parse_speakers(transcript) -> List[SpeakerInfo]:
        """Speaker listesi oluştur"""
        if not hasattr(transcript, 'utterances') or not transcript.utterances:
            return []
        
        speakers = {}
        for utt in transcript.utterances:
            if utt.speaker not in speakers:
                speakers[utt.speaker] = SpeakerInfo(
                    id=utt.speaker,
                    label=utt.speaker
                )
        
        return list(speakers.values())
    
    @staticmethod
    def parse_utterances(transcript) -> List[Utterance]:
        """Utterance'ları parse et"""
        if not hasattr(transcript, 'utterances') or not transcript.utterances:
            return []
        
        utterances = []
        for utt in transcript.utterances:
            utterances.append(Utterance(
                speaker=utt.speaker,
                start=utt.start / 1000.0,
                end=utt.end / 1000.0,
                text=utt.text,
                confidence=utt.confidence
            ))
        
        return utterances
    
    @staticmethod
    def parse_sentiment(transcript) -> Optional[List[SentimentResult]]:
        """Sentiment analysis sonuçları"""
        # ✅ CORRECT PROPERTY NAME: 'sentiment_analysis' (per official docs)
        if not hasattr(transcript, 'sentiment_analysis'):
            logger.info("❌ transcript has no 'sentiment_analysis' attribute")
            return None
        
        # If None or empty, return None instead of empty list
        if not transcript.sentiment_analysis:
            logger.info("❌ transcript.sentiment_analysis is None or empty")
            return None
        
        logger.info(f"✅ Found {len(transcript.sentiment_analysis)} sentiment results")
        
        results = []
        for i, sent in enumerate(transcript.sentiment_analysis):
            # Sentiment object has: text, start, end, confidence, speaker, sentiment
            sentiment_value = sent.sentiment.value if hasattr(sent.sentiment, 'value') else str(sent.sentiment)
            
            if i == 0:  # Log first item for debugging
                logger.info(f"   First sentiment: text='{sent.text[:50]}...', sentiment={sentiment_value}, confidence={sent.confidence}")
            
            results.append(SentimentResult(
                text=sent.text,
                sentiment=sentiment_value,
                confidence=sent.confidence,
                start=sent.start / 1000.0,
                end=sent.end / 1000.0
            ))
        
        logger.info(f"✅ Parsed {len(results)} sentiment results successfully")
        return results if results else None
    
    @staticmethod
    def parse_chapters(transcript) -> Optional[List[Chapter]]:
        """Auto chapters sonuçları"""
        if not hasattr(transcript, 'chapters') or not transcript.chapters:
            return None
        
        chapters = []
        for ch in transcript.chapters:
            chapters.append(Chapter(
                gist=ch.gist,
                headline=ch.headline,
                summary=ch.summary,
                start=ch.start / 1000.0,
                end=ch.end / 1000.0
            ))
        
        return chapters
    
    @staticmethod
    def parse_entities(transcript) -> Optional[List[Entity]]:
        """Entity detection sonuçları"""
        if not hasattr(transcript, 'entities') or not transcript.entities:
            return None
        
        entities = []
        for ent in transcript.entities:
            entities.append(Entity(
                entity_type=ent.entity_type,
                text=ent.text,
                start=ent.start / 1000.0,
                end=ent.end / 1000.0
            ))
        
        return entities
    
    @staticmethod
    def parse_topics(transcript) -> List[Topic]:
        """IAB categories (topics) parse et"""
        # Property name: iab_categories
        if not hasattr(transcript, 'iab_categories') or not transcript.iab_categories:
            return []
        
        topics = []
        results = getattr(transcript.iab_categories, 'results', None)
        if not results:
            return []
            
        for result in results:
            labels = [
                {
                    "label": label.label,
                    "relevance": label.relevance
                }
                for label in (result.labels or [])
            ]
            
            topics.append(Topic(
                text=result.text,
                labels=labels,
                timestamp={
                    "start": result.timestamp.start / 1000.0,
                    "end": result.timestamp.end / 1000.0
                }
            ))
        
        return topics
    
    @staticmethod
    def parse_content_safety(transcript) -> Optional[List[ContentSafetyResult]]:
        """Content moderation sonuçları"""
        if not hasattr(transcript, 'content_safety_labels') or not transcript.content_safety_labels:
            return None  # Return None instead of empty list for null DB value
        
        results = []
        safety_results = getattr(transcript.content_safety_labels, 'results', None)
        if not safety_results:
            return None  # Return None instead of empty list
            
        for item in safety_results:
            labels = [
                {
                    "label": label.label,
                    "confidence": label.confidence,
                    "severity": getattr(label, 'severity', None)
                }
                for label in (item.labels or [])
            ]
            
            results.append(ContentSafetyResult(
                text=item.text,
                labels=labels,
                timestamp={
                    "start": item.timestamp.start / 1000.0,
                    "end": item.timestamp.end / 1000.0
                },
                severity_score_summary=getattr(item, 'severity_score_summary', {}) or {}
            ))
        
        return results
    
    @staticmethod
    def parse_highlights(transcript) -> Optional[List[Highlight]]:
        """Auto highlights sonuçları"""
        if not hasattr(transcript, 'auto_highlights') or not transcript.auto_highlights:
            return None
        
        highlights = []
        highlight_results = getattr(transcript.auto_highlights, 'results', None)
        if not highlight_results:
            return []
            
        for hl in highlight_results:
            timestamps = [
                {
                    "start": ts.start / 1000.0,
                    "end": ts.end / 1000.0
                }
                for ts in (hl.timestamps or [])
            ]
            
            highlights.append(Highlight(
                text=hl.text,
                count=hl.count,
                rank=hl.rank,
                timestamps=timestamps
            ))
        
        return highlights
    
    @staticmethod
    def parse_all(transcript) -> Dict[str, Any]:
        """Tüm Speech Understanding sonuçlarını parse et"""
        logger.info("📊 Parsing Speech Understanding results...")
        
        results = {
            "speakers": SpeechUnderstandingParser.parse_speakers(transcript),
            "utterances": SpeechUnderstandingParser.parse_utterances(transcript),
            "sentiment": SpeechUnderstandingParser.parse_sentiment(transcript),
            "chapters": SpeechUnderstandingParser.parse_chapters(transcript),
            "entities": SpeechUnderstandingParser.parse_entities(transcript),
            "topics": SpeechUnderstandingParser.parse_topics(transcript),
            "content_safety": SpeechUnderstandingParser.parse_content_safety(transcript),
            "highlights": SpeechUnderstandingParser.parse_highlights(transcript)
        }
        
        # Stats (handle None values)
        logger.info(f"   Speakers: {len(results['speakers']) if results['speakers'] else 0}")
        logger.info(f"   Utterances: {len(results['utterances']) if results['utterances'] else 0}")
        logger.info(f"   Sentiment results: {len(results['sentiment']) if results['sentiment'] else 0}")
        logger.info(f"   Chapters: {len(results['chapters']) if results['chapters'] else 0}")
        logger.info(f"   Entities: {len(results['entities']) if results['entities'] else 0}")
        logger.info(f"   Topics: {len(results['topics']) if results['topics'] else 0}")
        logger.info(f"   Content safety results: {len(results['content_safety']) if results['content_safety'] else 0}")
        logger.info(f"   Highlights: {len(results['highlights']) if results['highlights'] else 0}")
        
        # Convert to dict for JSON serialization (handle None values)
        return {
            "speakers": [asdict(s) for s in results["speakers"]],
            "utterances": [asdict(u) for u in results["utterances"]],
            "sentiment_analysis": [asdict(s) for s in results["sentiment"]] if results["sentiment"] else None,
            "chapters": [asdict(c) for c in results["chapters"]] if results["chapters"] else None,
            "entities": [asdict(e) for e in results["entities"]] if results["entities"] else None,
            "topics": [asdict(t) for t in results["topics"]] if results["topics"] else None,
            "content_safety": [asdict(cs) for cs in results["content_safety"]] if results["content_safety"] else None,
            "highlights": [asdict(h) for h in results["highlights"]] if results["highlights"] else None
        }
