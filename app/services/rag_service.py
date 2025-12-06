"""
Gistify RAG Service
====================
Retrieval Augmented Generation için ana servis.
Embedding, vector search ve LLM entegrasyonu.
"""

import os
import json
import hashlib
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Lazy imports - these may not be installed in all environments
tiktoken = None
OpenAI = None
AsyncOpenAI = None

def _ensure_tiktoken():
    global tiktoken
    if tiktoken is None:
        import tiktoken as _tiktoken
        tiktoken = _tiktoken
    return tiktoken

def _ensure_openai():
    global OpenAI, AsyncOpenAI
    if OpenAI is None:
        from openai import OpenAI as _OpenAI, AsyncOpenAI as _AsyncOpenAI
        OpenAI = _OpenAI
        AsyncOpenAI = _AsyncOpenAI
    return OpenAI, AsyncOpenAI

# Lazy settings import - settings are loaded on first access, not at import time
_settings_cache = None

def _get_settings():
    """Lazily load settings to avoid import-time errors"""
    global _settings_cache
    if _settings_cache is None:
        from app.settings import get_settings
        _settings_cache = get_settings()
    return _settings_cache

logger = logging.getLogger(__name__)


# =========================================================================
# ENUMS & DATA CLASSES
# =========================================================================

class EmbeddingModel(str, Enum):
    """Desteklenen embedding modelleri"""
    OPENAI_SMALL = "text-embedding-3-small"
    OPENAI_LARGE = "text-embedding-3-large"


class LLMModel(str, Enum):
    """Desteklenen LLM modelleri"""
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GPT4_TURBO = "gpt-4-turbo"
    GEMINI_PRO = "gemini-2.5-pro"
    GEMINI_FLASH = "gemini-2.5-flash"


@dataclass
class EmbeddingResult:
    """Embedding sonucu"""
    text: str
    embedding: List[float]
    model: str
    token_count: int
    dimensions: int


@dataclass
class ChunkResult:
    """Chunk sonucu"""
    content: str
    index: int
    token_count: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Arama sonucu"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class RAGResponse:
    """RAG yanıtı"""
    answer: str
    sources: List[Dict[str, Any]]
    chunks_used: List[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    confidence_score: float
    processing_time_ms: int


# =========================================================================
# EMBEDDING MODEL CONFIGS
# =========================================================================

EMBEDDING_CONFIGS = {
    EmbeddingModel.OPENAI_SMALL: {
        "dimensions": 1536,
        "max_tokens": 8191,
        "cost_per_1m_tokens": 0.02,
        "provider": "openai"
    },
    EmbeddingModel.OPENAI_LARGE: {
        "dimensions": 3072,
        "max_tokens": 8191,
        "cost_per_1m_tokens": 0.13,
        "provider": "openai"
    }
}

LLM_CONFIGS = {
    LLMModel.GPT4O: {
        "input_cost_per_1m": 2.50,
        "output_cost_per_1m": 10.00,
        "max_tokens": 128000,
        "provider": "openai"
    },
    LLMModel.GPT4O_MINI: {
        "input_cost_per_1m": 0.15,
        "output_cost_per_1m": 0.60,
        "max_tokens": 128000,
        "provider": "openai"
    },
    LLMModel.GEMINI_PRO: {
        "input_cost_per_1m": 1.25,
        "output_cost_per_1m": 5.00,
        "max_tokens": 1000000,
        "provider": "google"
    },
    LLMModel.GEMINI_FLASH: {
        "input_cost_per_1m": 0.075,
        "output_cost_per_1m": 0.30,
        "max_tokens": 1000000,
        "provider": "google"
    }
}


# =========================================================================
# TEXT CHUNKING SERVICE
# =========================================================================

class TextChunker:
    """Metin parçalama servisi"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        model: str = "gpt-4o"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        try:
            tk = _ensure_tiktoken()
            self.tokenizer = tk.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            tk = _ensure_tiktoken()
            self.tokenizer = tk.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"⚠️ tiktoken not available, using simple tokenizer: {e}")
            self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """Token sayısını hesapla"""
        if self.tokenizer is None:
            # Simple fallback: estimate ~4 chars per token
            return len(text) // 4
        return len(self.tokenizer.encode(text))
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChunkResult]:
        """
        Metni semantic-aware chunks'lara böl
        
        Args:
            text: Bölünecek metin
            metadata: Chunk'lara eklenecek metadata
            
        Returns:
            ChunkResult listesi
        """
        if not text or not text.strip():
            return []
        
        # Paragraf bazlı bölme
        paragraphs = self._split_into_paragraphs(text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        start_char = 0
        
        for para in paragraphs:
            para_tokens = self.count_tokens(para)
            
            # Paragraf tek başına çok büyükse, cümlelere böl
            if para_tokens > self.chunk_size:
                # Mevcut chunk'ı kaydet
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, chunk_index, start_char, metadata
                    ))
                    chunk_index += 1
                
                # Büyük paragrafı cümlelere böl
                sentence_chunks = self._chunk_long_paragraph(para, start_char, chunk_index, metadata)
                chunks.extend(sentence_chunks)
                chunk_index += len(sentence_chunks)
                start_char += len(para) + 1
                current_chunk = ""
                current_tokens = 0
                continue
            
            # Chunk'a eklenebilir mi kontrol et
            if current_tokens + para_tokens <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_tokens += para_tokens
            else:
                # Mevcut chunk'ı kaydet
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, chunk_index, start_char, metadata
                    ))
                    chunk_index += 1
                    start_char += len(current_chunk) + 2
                
                # Overlap ile yeni chunk başlat
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + para if overlap_text else para
                current_tokens = self.count_tokens(current_chunk)
        
        # Son chunk'ı kaydet
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, chunk_index, start_char, metadata
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Metni paragraflara böl"""
        paragraphs = text.split("\n\n")
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _chunk_long_paragraph(
        self,
        text: str,
        start_char: int,
        start_index: int,
        metadata: Optional[Dict[str, Any]]
    ) -> List[ChunkResult]:
        """Uzun paragrafı cümlelere bölerek chunk'la"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = start_index
        current_start = start_char
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens <= self.chunk_size:
                current_chunk += (" " if current_chunk else "") + sentence
                current_tokens += sentence_tokens
            else:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        current_chunk, chunk_index, current_start, metadata
                    ))
                    chunk_index += 1
                    current_start += len(current_chunk) + 1
                
                current_chunk = sentence
                current_tokens = sentence_tokens
        
        if current_chunk:
            chunks.append(self._create_chunk(
                current_chunk, chunk_index, current_start, metadata
            ))
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Overlap için son kısmı al"""
        if not text or self.chunk_overlap <= 0:
            return ""
        
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= self.chunk_overlap:
            return text
        
        overlap_tokens = tokens[-self.chunk_overlap:]
        return self.tokenizer.decode(overlap_tokens)
    
    def _create_chunk(
        self,
        content: str,
        index: int,
        start_char: int,
        metadata: Optional[Dict[str, Any]]
    ) -> ChunkResult:
        """ChunkResult oluştur"""
        return ChunkResult(
            content=content.strip(),
            index=index,
            token_count=self.count_tokens(content),
            start_char=start_char,
            end_char=start_char + len(content),
            metadata=metadata or {}
        )


# =========================================================================
# EMBEDDING SERVICE
# =========================================================================

class EmbeddingService:
    """Embedding servisi - OpenAI desteği"""
    
    def __init__(self):
        self.openai_client = None
        settings = _get_settings()
        if settings.OPENAI_API_KEY:
            _ensure_openai()
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def get_embedding(
        self,
        text: str,
        model: EmbeddingModel = EmbeddingModel.OPENAI_SMALL
    ) -> EmbeddingResult:
        """
        Tek metin için embedding oluştur
        """
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        config = EMBEDDING_CONFIGS[model]
        return self._openai_embedding(text, model.value, config)
    
    def get_embeddings_batch(
        self,
        texts: List[str],
        model: EmbeddingModel = EmbeddingModel.OPENAI_SMALL,
        batch_size: int = 100
    ) -> List[EmbeddingResult]:
        """
        Toplu embedding oluştur
        """
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        config = EMBEDDING_CONFIGS[model]
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = self._openai_embeddings_batch(batch, model.value, config)
            results.extend(batch_results)
        
        return results
    
    def _openai_embedding(
        self,
        text: str,
        model: str,
        config: Dict
    ) -> EmbeddingResult:
        """OpenAI embedding"""
        response = self.openai_client.embeddings.create(
            input=text,
            model=model
        )
        
        embedding = response.data[0].embedding
        token_count = response.usage.total_tokens
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=model,
            token_count=token_count,
            dimensions=config["dimensions"]
        )
    
    def _openai_embeddings_batch(
        self,
        texts: List[str],
        model: str,
        config: Dict
    ) -> List[EmbeddingResult]:
        """OpenAI batch embedding"""
        response = self.openai_client.embeddings.create(
            input=texts,
            model=model
        )
        
        results = []
        for i, data in enumerate(response.data):
            results.append(EmbeddingResult(
                text=texts[i],
                embedding=data.embedding,
                model=model,
                token_count=response.usage.total_tokens // len(texts),
                dimensions=config["dimensions"]
            ))
        
        return results


# =========================================================================
# VECTOR STORE SERVICE (QDRANT)
# =========================================================================

class VectorStoreService:
    """Qdrant vector store servisi"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Qdrant client'ı başlat - REST API kullan"""
        try:
            settings = _get_settings()
            self.qdrant_url = settings.QDRANT_URL
            self.qdrant_api_key = settings.QDRANT_API_KEY
            
            # Test connection with httpx
            import httpx
            response = httpx.get(
                f"{self.qdrant_url}/collections",
                headers={"api-key": self.qdrant_api_key} if self.qdrant_api_key else {},
                timeout=30.0
            )
            if response.status_code == 200:
                self.client = True  # Mark as connected
                logger.info(f"✅ Qdrant connected via REST: {self.qdrant_url}")
            else:
                logger.error(f"❌ Qdrant connection failed: {response.status_code}")
                self.client = None
        except Exception as e:
            logger.error(f"❌ Qdrant connection failed: {e}")
            self.client = None
    
    def _make_request(self, method: str, endpoint: str, json_data: dict = None) -> dict:
        """Make HTTP request to Qdrant"""
        import httpx
        url = f"{self.qdrant_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.qdrant_api_key:
            headers["api-key"] = self.qdrant_api_key
        
        with httpx.Client(timeout=60.0) as client:
            if method == "GET":
                response = client.get(url, headers=headers)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=json_data)
            elif method == "POST":
                response = client.post(url, headers=headers, json=json_data)
            elif method == "DELETE":
                response = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            raise Exception(f"Qdrant API error: {response.status_code} - {response.text}")
        
        return response.json() if response.text else {}
    
    def create_collection(
        self,
        collection_name: str,
        dimensions: int = 1536,
        distance: str = "Cosine"
    ) -> bool:
        """Yeni koleksiyon oluştur - REST API"""
        if not self.client:
            return False
        
        try:
            # Check if collection already exists
            try:
                self._make_request("GET", f"/collections/{collection_name}")
                logger.info(f"ℹ️ Collection already exists: {collection_name}")
                return True
            except:
                pass  # Collection doesn't exist, create it
            
            self._make_request("PUT", f"/collections/{collection_name}", {
                "vectors": {
                    "size": dimensions,
                    "distance": distance
                }
            })
            logger.info(f"✅ Collection created: {collection_name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"ℹ️ Collection already exists: {collection_name}")
                return True
            logger.error(f"❌ Collection creation failed: {e}")
            raise e
    
    def delete_collection(self, collection_name: str) -> bool:
        """Koleksiyon sil - REST API"""
        if not self.client:
            return False
        
        try:
            self._make_request("DELETE", f"/collections/{collection_name}")
            logger.info(f"✅ Collection deleted: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Collection deletion failed: {e}")
            return False
    
    def upsert_vectors(
        self,
        collection_name: str,
        points: List[Dict[str, Any]]
    ) -> bool:
        """Vektörleri ekle/güncelle - REST API"""
        if not self.client:
            return False
        
        try:
            # Convert points to Qdrant format
            qdrant_points = [
                {
                    "id": p["id"],
                    "vector": p["vector"],
                    "payload": p.get("payload", {})
                }
                for p in points
            ]
            
            self._make_request("PUT", f"/collections/{collection_name}/points", {
                "points": qdrant_points
            })
            logger.info(f"✅ Upserted {len(points)} vectors to {collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Vector upsert failed: {e}")
            raise e
    
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict] = None
    ) -> List[SearchResult]:
        """Vektör araması yap - REST API"""
        if not self.client:
            return []
        
        try:
            search_body = {
                "vector": query_vector,
                "limit": top_k,
                "score_threshold": score_threshold,
                "with_payload": True
            }
            
            if filter_conditions:
                search_body["filter"] = {
                    "must": [
                        {"key": key, "match": {"value": value}}
                        for key, value in filter_conditions.items()
                    ]
                }
            
            response = self._make_request("POST", f"/collections/{collection_name}/points/search", search_body)
            
            results = response.get("result", [])
            return [
                SearchResult(
                    chunk_id=str(r["id"]),
                    content=r.get("payload", {}).get("text", r.get("payload", {}).get("content", "")),
                    score=r.get("score", 0.0),
                    metadata=r.get("payload", {})
                )
                for r in results
            ]
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            return []
    
    def delete_points(
        self,
        collection_name: str,
        point_ids: List[str]
    ) -> bool:
        """Point'leri sil - REST API"""
        if not self.client:
            return False
        
        try:
            self._make_request("POST", f"/collections/{collection_name}/points/delete", {
                "points": point_ids
            })
            return True
        except Exception as e:
            logger.error(f"❌ Points deletion failed: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Koleksiyon bilgilerini al - REST API"""
        if not self.client:
            return None
        
        try:
            response = self._make_request("GET", f"/collections/{collection_name}")
            result = response.get("result", {})
            return {
                "name": collection_name,
                "vectors_count": result.get("vectors_count", 0),
                "points_count": result.get("points_count", 0),
                "status": result.get("status", "unknown")
            }
        except Exception as e:
            logger.error(f"❌ Get collection info failed: {e}")
            return None


# =========================================================================
# LLM SERVICE
# =========================================================================

class LLMService:
    """LLM servisi - OpenAI ve Gemini desteği"""
    
    def __init__(self):
        self.openai_client = None
        settings = _get_settings()
        if settings.OPENAI_API_KEY:
            _ensure_openai()
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: LLMModel = LLMModel.GPT4O_MINI,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Tuple[str, int, int]:
        """
        LLM yanıtı oluştur
        """
        config = LLM_CONFIGS[model]
        
        if config["provider"] == "openai":
            return self._openai_generate(messages, model.value, temperature, max_tokens)
        elif config["provider"] == "google":
            return self._gemini_generate(messages, model.value, temperature, max_tokens)
        else:
            raise ValueError(f"Desteklenmeyen provider: {config['provider']}")
    
    def _openai_generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, int, int]:
        """OpenAI ile yanıt oluştur"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return (
            response.choices[0].message.content,
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )
    
    def _gemini_generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, int, int]:
        """Gemini ile yanıt oluştur"""
        try:
            import google.generativeai as genai
            
            settings = _get_settings()
            if not settings.GEMINI_API_KEY:
                raise ValueError("Gemini API key not configured")
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            gemini_model = genai.GenerativeModel(model)
            
            # Mesajları Gemini formatına dönüştür
            system_content = ""
            chat_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    chat_messages.append({
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [msg["content"]]
                    })
            
            # Chat oluştur
            chat = gemini_model.start_chat(history=chat_messages[:-1] if len(chat_messages) > 1 else [])
            
            # Son mesajı gönder
            last_message = chat_messages[-1]["parts"][0] if chat_messages else ""
            if system_content:
                last_message = f"{system_content}\n\n{last_message}"
            
            response = chat.send_message(
                last_message,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )
            
            # Token sayısını tahmin et (tiktoken optional)
            try:
                tk = _ensure_tiktoken()
                tokenizer = tk.get_encoding("cl100k_base")
                input_tokens = sum(len(tokenizer.encode(m.get("content", ""))) for m in messages)
                output_tokens = len(tokenizer.encode(response.text))
            except Exception:
                # Fallback: estimate tokens
                input_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
                output_tokens = len(response.text) // 4
            
            return response.text, input_tokens, output_tokens
        
        except ImportError:
            raise ValueError("google-generativeai package not installed")


# =========================================================================
# RAG SERVICE (ANA SERVİS)
# =========================================================================

class RAGService:
    """
    RAG (Retrieval Augmented Generation) Ana Servisi
    """
    
    def __init__(self):
        settings = _get_settings()
        self.chunker = TextChunker(
            chunk_size=settings.RAG_DEFAULT_CHUNK_SIZE,
            chunk_overlap=settings.RAG_DEFAULT_CHUNK_OVERLAP
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.llm_service = LLMService()
    
    def create_knowledge_base(
        self,
        user_id: int,
        source_id: int,
        texts: List[Dict[str, Any]],
        embedding_model: EmbeddingModel = EmbeddingModel.OPENAI_SMALL,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> Dict[str, Any]:
        """
        Bilgi tabanı oluştur
        """
        collection_name = f"gistify_user_{user_id}_source_{source_id}"
        config = EMBEDDING_CONFIGS[embedding_model]
        
        # Chunker'ı yapılandır
        self.chunker.chunk_size = chunk_size
        self.chunker.chunk_overlap = chunk_overlap
        
        # 1. Koleksiyonu oluştur
        self.vector_store.create_collection(
            collection_name=collection_name,
            dimensions=config["dimensions"]
        )
        
        # 2. Tüm metinleri chunk'la
        all_chunks = []
        for text_item in texts:
            chunks = self.chunker.chunk_text(
                text=text_item["content"],
                metadata=text_item.get("metadata", {})
            )
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return {
                "success": True,
                "collection_name": collection_name,
                "chunk_count": 0,
                "vector_count": 0
            }
        
        # 3. Embedding'leri oluştur
        chunk_texts = [c.content for c in all_chunks]
        embeddings = self.embedding_service.get_embeddings_batch(
            texts=chunk_texts,
            model=embedding_model
        )
        
        # 4. Vektörleri kaydet
        points = []
        for i, (chunk, emb) in enumerate(zip(all_chunks, embeddings)):
            point_id = hashlib.md5(f"{collection_name}_{i}".encode()).hexdigest()
            points.append({
                "id": point_id,
                "vector": emb.embedding,
                "payload": {
                    "content": chunk.content,
                    "chunk_index": chunk.index,
                    "token_count": chunk.token_count,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    **chunk.metadata
                }
            })
        
        self.vector_store.upsert_vectors(
            collection_name=collection_name,
            points=points
        )
        
        total_tokens = sum(e.token_count for e in embeddings)
        
        logger.info(f"✅ PKB created: {collection_name}, {len(all_chunks)} chunks, {total_tokens} tokens")
        
        return {
            "success": True,
            "collection_name": collection_name,
            "chunk_count": len(all_chunks),
            "vector_count": len(points),
            "total_tokens": total_tokens,
            "embedding_model": embedding_model.value,
            "dimensions": config["dimensions"]
        }
    
    def query(
        self,
        user_id: int,
        source_id: int,
        question: str,
        embedding_model: EmbeddingModel = EmbeddingModel.OPENAI_SMALL,
        llm_model: LLMModel = LLMModel.GPT4O_MINI,
        top_k: int = 5,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> RAGResponse:
        """
        RAG sorgusu yap
        """
        import time
        start_time = time.time()
        
        collection_name = f"gistify_user_{user_id}_source_{source_id}"
        
        # 1. Soru için embedding oluştur
        query_embedding = self.embedding_service.get_embedding(
            text=question,
            model=embedding_model
        )
        
        # 2. Benzer chunk'ları bul
        search_results = self.vector_store.search(
            collection_name=collection_name,
            query_vector=query_embedding.embedding,
            top_k=top_k
        )
        
        if not search_results:
            return RAGResponse(
                answer="Üzgünüm, bu soruyla ilgili bilgi tabanınızda yeterli bilgi bulamadım.",
                sources=[],
                chunks_used=[],
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                confidence_score=0.0,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 3. Context oluştur
        context_parts = []
        sources = []
        chunks_used = []
        
        for i, result in enumerate(search_results):
            context_parts.append(f"[{i+1}] {result.content}")
            sources.append({
                "index": i + 1,
                "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "score": result.score,
                "metadata": result.metadata
            })
            chunks_used.append(result.chunk_id)
        
        context = "\n\n".join(context_parts)
        
        # 4. Prompt oluştur
        if not system_prompt:
            system_prompt = """Sen kullanıcının kişisel bilgi tabanına dayalı bir AI asistanısın.
Sadece sana verilen bağlam bilgilerini kullanarak yanıt ver.
Eğer bağlamda yeterli bilgi yoksa, bunu açıkça belirt.
Yanıtlarında hangi kaynaklardan (numaralı) yararlandığını belirt.
Türkçe yanıt ver."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Bağlam:
{context}

Soru: {question}

Lütfen yukarıdaki bağlama dayanarak soruyu yanıtla ve hangi kaynaklardan ([1], [2], vb.) yararlandığını belirt."""}
        ]
        
        # 5. LLM yanıtı al
        answer, input_tokens, output_tokens = self.llm_service.generate_response(
            messages=messages,
            model=llm_model,
            temperature=temperature
        )
        
        # 6. Güven skoru hesapla (ortalama benzerlik skoru)
        confidence_score = sum(r.score for r in search_results) / len(search_results)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            chunks_used=chunks_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            confidence_score=confidence_score,
            processing_time_ms=processing_time_ms
        )
    
    def delete_knowledge_base(
        self,
        user_id: int,
        source_id: int
    ) -> bool:
        """Bilgi tabanını sil"""
        collection_name = f"gistify_user_{user_id}_source_{source_id}"
        return self.vector_store.delete_collection(collection_name)


# =========================================================================
# DOCUMENT GENERATOR SERVICE
# =========================================================================

class DocumentGeneratorService:
    """AI ile döküman oluşturma servisi"""
    
    def __init__(self):
        self.rag_service = RAGService()
        self.llm_service = LLMService()
    
    def generate_summary(
        self,
        user_id: int,
        source_id: int,
        length: str = "medium",
        style: str = "professional"
    ) -> Dict[str, Any]:
        """Source'dan özet oluştur"""
        length_tokens = {
            "short": 200,
            "medium": 500,
            "long": 1000
        }
        
        style_instructions = {
            "professional": "Profesyonel ve resmi bir dil kullan.",
            "casual": "Samimi ve anlaşılır bir dil kullan.",
            "academic": "Akademik ve bilimsel bir dil kullan."
        }
        
        system_prompt = f"""Sen bir özetleme uzmanısın. 
{style_instructions.get(style, style_instructions['professional'])}
Özet yaklaşık {length_tokens.get(length, 500)} kelime olmalı.
Önemli noktaları vurgula ve ana fikirleri öne çıkar."""
        
        response = self.rag_service.query(
            user_id=user_id,
            source_id=source_id,
            question="Bu içeriğin kapsamlı bir özetini oluştur.",
            system_prompt=system_prompt,
            top_k=10
        )
        
        return {
            "title": "İçerik Özeti",
            "content": response.answer,
            "sources": response.sources,
            "tokens_used": response.total_tokens,
            "type": "summary"
        }
    
    def generate_report(
        self,
        user_id: int,
        source_id: int,
        report_type: str = "general",
        sections: List[str] = None
    ) -> Dict[str, Any]:
        """Source'dan rapor oluştur"""
        if not sections:
            sections = ["Yönetici Özeti", "Ana Bulgular", "Detaylı Analiz", "Sonuç ve Öneriler"]
        
        sections_text = "\n".join([f"- {s}" for s in sections])
        
        system_prompt = f"""Sen profesyonel bir rapor yazarısın.
Aşağıdaki bölümleri içeren kapsamlı bir rapor oluştur:
{sections_text}

Her bölüm için:
- Açık ve net başlıklar kullan
- Önemli noktaları madde işaretleriyle listele
- Veriye dayalı çıkarımlar yap
- Profesyonel bir ton kullan

Rapor formatı Markdown olmalı."""

        response = self.rag_service.query(
            user_id=user_id,
            source_id=source_id,
            question=f"Bu içerikten detaylı bir {report_type} raporu oluştur.",
            system_prompt=system_prompt,
            top_k=15,
            temperature=0.5
        )
        
        return {
            "title": f"{report_type.title()} Raporu",
            "content": response.answer,
            "sources": response.sources,
            "tokens_used": response.total_tokens,
            "type": "report"
        }
    
    def generate_quiz(
        self,
        user_id: int,
        source_id: int,
        question_count: int = 10,
        question_types: List[str] = None,
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """Source'dan quiz oluştur"""
        if not question_types:
            question_types = ["multiple_choice", "true_false"]
        
        type_instructions = {
            "multiple_choice": "Çoktan seçmeli sorular (4 seçenek, 1 doğru)",
            "true_false": "Doğru/Yanlış soruları",
            "open_ended": "Açık uçlu sorular"
        }
        
        types_text = "\n".join([f"- {type_instructions.get(t, t)}" for t in question_types])
        
        difficulty_instructions = {
            "easy": "Temel kavramları test eden kolay sorular",
            "medium": "Anlama ve uygulama gerektiren orta seviye sorular",
            "hard": "Analiz ve sentez gerektiren zor sorular"
        }
        
        system_prompt = f"""Sen bir eğitim uzmanısın ve quiz oluşturuyorsun.

Zorluk: {difficulty_instructions.get(difficulty, difficulty_instructions['medium'])}

Aşağıdaki soru tiplerinden {question_count} soru oluştur:
{types_text}

Her soru için:
1. Soruyu açık ve anlaşılır yaz
2. Doğru cevabı belirt
3. Kısa bir açıklama ekle

JSON formatında yanıt ver."""

        response = self.rag_service.query(
            user_id=user_id,
            source_id=source_id,
            question=f"Bu içerikten {question_count} soruluk bir quiz oluştur.",
            system_prompt=system_prompt,
            top_k=10,
            temperature=0.8
        )
        
        return {
            "title": f"Quiz - {question_count} Soru",
            "content": response.answer,
            "sources": response.sources,
            "tokens_used": response.total_tokens,
            "type": "quiz"
        }
    
    def generate_analysis(
        self,
        user_id: int,
        source_id: int,
        analysis_type: str = "swot",
        focus_areas: List[str] = None
    ) -> Dict[str, Any]:
        """Source'dan analiz oluştur"""
        analysis_prompts = {
            "swot": """SWOT analizi oluştur:
- Güçlü Yönler (Strengths)
- Zayıf Yönler (Weaknesses)
- Fırsatlar (Opportunities)
- Tehditler (Threats)""",
            
            "trend": """Trend analizi oluştur:
- Ana trendleri belirle
- Zaman içindeki değişimleri analiz et
- Gelecek projeksiyonları yap""",
            
            "theme": """Tema analizi oluştur:
- Ana temaları belirle
- Alt temaları kategorize et
- Temalar arası ilişkileri açıkla""",
            
            "sentiment": """Duygu analizi oluştur:
- Genel duygu tonunu belirle
- Pozitif/negatif ifadeleri kategorize et
- Önemli duygu kalıplarını vurgula"""
        }
        
        focus_text = ""
        if focus_areas:
            focus_text = f"\n\nÖzellikle şu alanlara odaklan: {', '.join(focus_areas)}"
        
        system_prompt = f"""Sen bir analiz uzmanısın.
{analysis_prompts.get(analysis_type, analysis_prompts['swot'])}
{focus_text}

Analizini yapılandırılmış bir şekilde sun ve somut örnekler ver."""

        response = self.rag_service.query(
            user_id=user_id,
            source_id=source_id,
            question=f"Bu içerik için {analysis_type} analizi yap.",
            system_prompt=system_prompt,
            top_k=15,
            temperature=0.6
        )
        
        return {
            "title": f"{analysis_type.upper()} Analizi",
            "content": response.answer,
            "sources": response.sources,
            "tokens_used": response.total_tokens,
            "type": "analysis"
        }


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_rag_service() -> RAGService:
    """RAG servis instance'ı oluştur"""
    return RAGService()


def create_document_generator() -> DocumentGeneratorService:
    """Document generator instance'ı oluştur"""
    return DocumentGeneratorService()
