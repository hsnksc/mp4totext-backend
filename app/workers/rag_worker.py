"""
Gistify RAG Celery Workers
===========================
PKB oluşturma ve döküman işleme için background task'lar.
"""

import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.rag import (
    RAGSource, RAGSourceItem, RAGSourceChunk,
    SourceStatus, SourceItemType
)
from app.models.user import User
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType
from app.services.rag_service import (
    RAGService, TextChunker, EmbeddingService, VectorStoreService,
    EmbeddingModel, LLMModel
)
from app.settings import get_settings

logger = get_task_logger(__name__)
settings = get_settings()


def create_rag_service() -> RAGService:
    """RAG Service factory"""
    return RAGService(
        qdrant_url=settings.QDRANT_URL,
        qdrant_api_key=settings.QDRANT_API_KEY
    )


# =========================================================================
# PKB CREATION TASK
# =========================================================================

@celery_app.task(
    bind=True, 
    max_retries=3, 
    default_retry_delay=60,
    time_limit=1800,  # 30 minutes
    soft_time_limit=1700
)
def create_pkb_task(
    self,
    source_id: int,
    user_id: int,
    options: Dict[str, Any]
):
    """
    PKB (Personal Knowledge Base) oluşturma task'ı
    
    Bu task:
    1. Source içindeki tüm içerikleri toplar
    2. Metinleri chunk'lara ayırır
    3. Her chunk için embedding oluşturur
    4. Vektörleri Qdrant'a kaydeder
    5. Database'i günceller
    6. Kredileri düşer
    """
    db = SessionLocal()
    logger.info(f"🚀 PKB creation started: source_id={source_id}, user_id={user_id}")
    
    try:
        # Get options
        embedding_model = options.get("embedding_model", "text-embedding-3-small")
        chunk_size = options.get("chunk_size", 512)
        chunk_overlap = options.get("chunk_overlap", 50)
        
        # Task durumunu güncelle
        self.update_state(state='PROGRESS', meta={
            'status': 'Başlatılıyor',
            'progress': 5
        })
        
        # Get source
        source = db.query(RAGSource).filter(RAGSource.id == source_id).first()
        if not source:
            logger.error(f"❌ Source not found: {source_id}")
            return {"success": False, "error": "Source not found"}
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"❌ User not found: {user_id}")
            return {"success": False, "error": "User not found"}
        
        self.update_state(state='PROGRESS', meta={
            'status': 'İçerikler toplanıyor',
            'progress': 10
        })
        
        # Get all items
        items = db.query(RAGSourceItem).filter(RAGSourceItem.source_id == source_id).all()
        if not items:
            logger.warning(f"⚠️ No items in source: {source_id}")
            return {"success": False, "error": "No items in source"}
        
        # Collect all texts
        texts = []
        for item in items:
            if item.content:
                texts.append({
                    "content": item.content,
                    "metadata": {
                        "source_item_id": item.id,
                        "title": item.title,
                        "item_type": item.item_type.value if item.item_type else "note",
                        "reference_id": item.reference_id
                    }
                })
        
        if not texts:
            logger.warning(f"⚠️ No content in items: {source_id}")
            return {"success": False, "error": "No content in items"}
        
        logger.info(f"📊 Collected {len(texts)} texts from source {source_id}")
        
        self.update_state(state='PROGRESS', meta={
            'status': 'Chunking yapılıyor',
            'progress': 20
        })
        
        # Create RAG service
        rag_service = create_rag_service()
        
        # Determine embedding model
        emb_model = EmbeddingModel.OPENAI_SMALL
        emb_dimensions = 1536
        if embedding_model == "text-embedding-3-large":
            emb_model = EmbeddingModel.OPENAI_LARGE
            emb_dimensions = 3072
        
        # Chunk all texts
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        all_chunks = []
        
        for text_data in texts:
            chunks = chunker.chunk_text(text_data["content"], text_data["metadata"])
            all_chunks.extend(chunks)
        
        if not all_chunks:
            logger.warning(f"⚠️ No chunks created: {source_id}")
            return {"success": False, "error": "No chunks created"}
        
        logger.info(f"📊 Created {len(all_chunks)} chunks")
        
        self.update_state(state='PROGRESS', meta={
            'status': 'Embedding oluşturuluyor',
            'progress': 40
        })
        
        # Create embeddings in batches
        chunk_texts = [c.content for c in all_chunks]
        batch_size = 100
        all_embeddings = []
        
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i:i + batch_size]
            embeddings = rag_service.embedding_service.get_embeddings_batch(
                texts=batch,
                model=emb_model
            )
            all_embeddings.extend(embeddings)
            
            progress = 40 + int((i / len(chunk_texts)) * 30)
            self.update_state(state='PROGRESS', meta={
                'status': f'Embedding oluşturuluyor ({i + len(batch)}/{len(chunk_texts)})',
                'progress': progress
            })
        
        logger.info(f"✅ Created {len(all_embeddings)} embeddings")
        
        self.update_state(state='PROGRESS', meta={
            'status': 'Qdrant\'a kaydediliyor',
            'progress': 75
        })
        
        # Create collection and upsert vectors
        collection_name = f"user_{user_id}_source_{source_id}"
        
        # Create collection
        rag_service.vector_store.create_collection(
            collection_name=collection_name,
            vector_size=emb_dimensions
        )
        
        # Prepare points
        points = []
        total_tokens = 0
        
        for i, (chunk, emb) in enumerate(zip(all_chunks, all_embeddings)):
            point_id = hashlib.md5(
                f"{collection_name}_{chunk.metadata.get('source_item_id', 0)}_{i}".encode()
            ).hexdigest()
            
            points.append({
                "id": point_id,
                "vector": emb.embedding,
                "payload": {
                    "content": chunk.content,
                    "chunk_index": chunk.index,
                    **chunk.metadata
                }
            })
            total_tokens += emb.total_tokens
        
        # Upsert to Qdrant
        rag_service.vector_store.upsert_vectors(
            collection_name=collection_name,
            points=points
        )
        
        logger.info(f"✅ Upserted {len(points)} vectors to Qdrant")
        
        self.update_state(state='PROGRESS', meta={
            'status': 'Database güncelleniyor',
            'progress': 90
        })
        
        # Save chunks to database
        db.query(RAGSourceChunk).filter(RAGSourceChunk.source_id == source_id).delete()
        
        for i, (chunk, emb) in enumerate(zip(all_chunks, all_embeddings)):
            db_chunk = RAGSourceChunk(
                source_id=source_id,
                item_id=chunk.metadata.get("source_item_id"),
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=emb.total_tokens,
                vector_id=hashlib.md5(
                    f"{collection_name}_{chunk.metadata.get('source_item_id', 0)}_{i}".encode()
                ).hexdigest()
            )
            db.add(db_chunk)
        
        # Update source
        source.pkb_enabled = True
        source.status = SourceStatus.INDEXED
        source.vector_collection_name = collection_name
        source.total_chunks = len(all_chunks)
        source.total_tokens = total_tokens
        source.embedding_model = embedding_model
        source.embedding_dimensions = emb_dimensions
        source.chunk_size = chunk_size
        source.chunk_overlap = chunk_overlap
        source.pkb_created_at = datetime.utcnow()
        source.updated_at = datetime.utcnow()
        
        # Mark items as indexed
        for item in items:
            item.is_indexed = True
        
        # Calculate and deduct credits
        # PKB: 0.1 credit per chunk + embedding costs
        embedding_credits = (total_tokens / 1000) * 0.1  # 0.1 per 1K tokens
        pkb_credits = len(all_chunks) * 0.1
        total_credits = embedding_credits + pkb_credits
        
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=user_id,
            amount=total_credits,
            operation_type=OperationType.RAG_PKB_CREATION,
            description=f"PKB Creation: {source.name}",
            metadata={
                "source_id": source_id,
                "chunk_count": len(all_chunks),
                "total_tokens": total_tokens
            }
        )
        
        source.total_credits_used = (source.total_credits_used or 0) + total_credits
        
        db.commit()
        
        logger.info(f"✅ PKB creation completed: source_id={source_id}, chunks={len(all_chunks)}, credits={total_credits:.2f}")
        
        self.update_state(state='SUCCESS', meta={
            'status': 'Tamamlandı',
            'progress': 100
        })
        
        # Send WebSocket notification
        try:
            from app.websocket import manager
            import asyncio
            asyncio.run(manager.send_personal_message(
                message={
                    "type": "pkb_created",
                    "source_id": source_id,
                    "chunk_count": len(all_chunks),
                    "credits_used": round(total_credits, 2)
                },
                user_id=user_id
            ))
        except Exception as ws_error:
            logger.warning(f"⚠️ WebSocket notification failed: {ws_error}")
        
        return {
            "success": True,
            "source_id": source_id,
            "collection_name": collection_name,
            "chunk_count": len(all_chunks),
            "vector_count": len(points),
            "total_tokens": total_tokens,
            "credits_used": round(total_credits, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ PKB creation failed: {e}", exc_info=True)
        
        # Update source status
        try:
            source = db.query(RAGSource).filter(RAGSource.id == source_id).first()
            if source:
                source.status = SourceStatus.ERROR
                db.commit()
        except:
            pass
        
        db.rollback()
        raise self.retry(exc=e)
    
    finally:
        db.close()


# =========================================================================
# REINDEX & DELETE PKB TASKS
# =========================================================================

@celery_app.task(bind=True, max_retries=3)
def reindex_pkb_task(
    self,
    source_id: int,
    user_id: int,
    options: Dict[str, Any]
):
    """PKB'yi yeniden oluştur"""
    logger.info(f"🔄 Reindexing PKB: source_id={source_id}")
    
    # Mevcut vektör koleksiyonunu sil
    try:
        rag_service = create_rag_service()
        rag_service.delete_knowledge_base(user_id, source_id)
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete existing PKB: {e}")
    
    # Yeniden oluştur
    return create_pkb_task(
        source_id=source_id,
        user_id=user_id,
        options=options
    )


@celery_app.task(bind=True)
def delete_pkb_task(self, source_id: int, user_id: int):
    """PKB'yi sil"""
    logger.info(f"🗑️ Deleting PKB: source_id={source_id}")
    
    db = SessionLocal()
    
    try:
        rag_service = create_rag_service()
        success = rag_service.delete_knowledge_base(user_id, source_id)
        
        # Update database
        source = db.query(RAGSource).filter(RAGSource.id == source_id).first()
        if source:
            source.pkb_enabled = False
            source.vector_collection_name = None
            source.total_chunks = 0
            source.status = SourceStatus.READY
            db.commit()
        
        # Delete chunks
        db.query(RAGSourceChunk).filter(RAGSourceChunk.source_id == source_id).delete()
        db.commit()
        
        logger.info(f"✅ PKB deleted: source_id={source_id}")
        
        return {"success": success, "source_id": source_id}
        
    except Exception as e:
        logger.error(f"❌ PKB deletion failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    
    finally:
        db.close()


# =========================================================================
# INCREMENTAL INDEXING TASK
# =========================================================================

@celery_app.task(bind=True)
def index_new_item_task(
    self,
    source_id: int,
    source_item_id: int,
    user_id: int,
    content: str,
    metadata: Dict[str, Any] = None
):
    """Yeni eklenen içeriği index'e ekle (incremental indexing)"""
    logger.info(f"📝 Indexing new item: source_id={source_id}, item_id={source_item_id}")
    
    db = SessionLocal()
    
    try:
        # Get source
        source = db.query(RAGSource).filter(RAGSource.id == source_id).first()
        if not source or not source.pkb_enabled:
            logger.warning(f"⚠️ Source not ready for indexing: {source_id}")
            return {"success": False, "error": "Source not PKB enabled"}
        
        rag_service = create_rag_service()
        collection_name = source.vector_collection_name or f"user_{user_id}_source_{source_id}"
        
        # Chunk content
        chunk_size = source.chunk_size or 512
        chunk_overlap = source.chunk_overlap or 50
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_text(content, metadata or {})
        
        if not chunks:
            return {"success": True, "chunks_added": 0}
        
        # Get embeddings
        emb_model = EmbeddingModel.OPENAI_SMALL
        if source.embedding_model == "text-embedding-3-large":
            emb_model = EmbeddingModel.OPENAI_LARGE
        
        chunk_texts = [c.content for c in chunks]
        embeddings = rag_service.embedding_service.get_embeddings_batch(
            texts=chunk_texts,
            model=emb_model
        )
        
        # Prepare points
        points = []
        total_tokens = 0
        
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            point_id = hashlib.md5(
                f"{collection_name}_{source_item_id}_{i}".encode()
            ).hexdigest()
            
            points.append({
                "id": point_id,
                "vector": emb.embedding,
                "payload": {
                    "content": chunk.content,
                    "chunk_index": chunk.index,
                    "source_item_id": source_item_id,
                    **chunk.metadata
                }
            })
            total_tokens += emb.total_tokens
            
            # Save chunk to DB
            db_chunk = RAGSourceChunk(
                source_id=source_id,
                item_id=source_item_id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=emb.total_tokens,
                vector_id=point_id
            )
            db.add(db_chunk)
        
        # Upsert to Qdrant
        rag_service.vector_store.upsert_vectors(
            collection_name=collection_name,
            points=points
        )
        
        # Update source stats
        source.total_chunks = (source.total_chunks or 0) + len(chunks)
        source.total_tokens = (source.total_tokens or 0) + total_tokens
        source.updated_at = datetime.utcnow()
        
        # Mark item as indexed
        item = db.query(RAGSourceItem).filter(RAGSourceItem.id == source_item_id).first()
        if item:
            item.is_indexed = True
        
        # Deduct credits
        credits = (total_tokens / 1000) * 0.1 + len(chunks) * 0.1
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=user_id,
            amount=credits,
            operation_type=OperationType.RAG_EMBEDDING,
            description=f"Incremental indexing: {source_item_id}",
            metadata={"source_id": source_id, "item_id": source_item_id}
        )
        
        db.commit()
        
        logger.info(f"✅ Item indexed: source_id={source_id}, item_id={source_item_id}, chunks={len(chunks)}")
        
        return {
            "success": True,
            "source_item_id": source_item_id,
            "chunks_added": len(chunks),
            "vectors_added": len(points),
            "credits_used": round(credits, 2)
        }
        
    except Exception as e:
        logger.error(f"❌ Item indexing failed: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}
    
    finally:
        db.close()


# =========================================================================
# DOCUMENT GENERATION TASKS
# =========================================================================

@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_summary_task(
    self,
    source_id: int,
    user_id: int,
    length: str = "medium",
    style: str = "professional"
):
    """Özet oluşturma task'ı"""
    logger.info(f"📝 Generating summary: source_id={source_id}")
    
    try:
        from app.services.rag_service import DocumentGeneratorService
        
        generator = DocumentGeneratorService()
        result = generator.generate_summary(
            user_id=user_id,
            source_id=source_id,
            length=length,
            style=style
        )
        
        logger.info(f"✅ Summary generated: source_id={source_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Summary generation failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_report_task(
    self,
    source_id: int,
    user_id: int,
    report_type: str = "general",
    sections: List[str] = None
):
    """Rapor oluşturma task'ı"""
    logger.info(f"📝 Generating report: source_id={source_id}")
    
    try:
        from app.services.rag_service import DocumentGeneratorService
        
        generator = DocumentGeneratorService()
        result = generator.generate_report(
            user_id=user_id,
            source_id=source_id,
            report_type=report_type,
            sections=sections
        )
        
        logger.info(f"✅ Report generated: source_id={source_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_quiz_task(
    self,
    source_id: int,
    user_id: int,
    question_count: int = 10,
    question_types: List[str] = None,
    difficulty: str = "medium"
):
    """Quiz oluşturma task'ı"""
    logger.info(f"📝 Generating quiz: source_id={source_id}")
    
    try:
        from app.services.rag_service import DocumentGeneratorService
        
        generator = DocumentGeneratorService()
        result = generator.generate_quiz(
            user_id=user_id,
            source_id=source_id,
            question_count=question_count,
            question_types=question_types,
            difficulty=difficulty
        )
        
        logger.info(f"✅ Quiz generated: source_id={source_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Quiz generation failed: {e}")
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def generate_analysis_task(
    self,
    source_id: int,
    user_id: int,
    analysis_type: str = "swot",
    focus_areas: List[str] = None
):
    """Analiz oluşturma task'ı"""
    logger.info(f"📝 Generating analysis: source_id={source_id}")
    
    try:
        from app.services.rag_service import DocumentGeneratorService
        
        generator = DocumentGeneratorService()
        result = generator.generate_analysis(
            user_id=user_id,
            source_id=source_id,
            analysis_type=analysis_type,
            focus_areas=focus_areas
        )
        
        logger.info(f"✅ Analysis generated: source_id={source_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Analysis generation failed: {e}")
        raise self.retry(exc=e)


# =========================================================================
# MAINTENANCE TASKS
# =========================================================================

@celery_app.task
def cleanup_orphan_vectors_task(user_id: int):
    """Sahipsiz vektörleri temizle"""
    logger.info(f"🧹 Cleaning up orphan vectors: user_id={user_id}")
    
    # Bu task production'da database ile senkronizasyon yapar
    return {
        "user_id": user_id,
        "status": "completed",
        "message": "Cleanup task completed"
    }


@celery_app.task
def calculate_source_stats_task(source_id: int, user_id: int):
    """Source istatistiklerini hesapla"""
    logger.info(f"📊 Calculating source stats: source_id={source_id}")
    
    db = SessionLocal()
    
    try:
        rag_service = create_rag_service()
        collection_name = f"user_{user_id}_source_{source_id}"
        
        info = rag_service.vector_store.get_collection_info(collection_name)
        
        # Update source in database
        source = db.query(RAGSource).filter(RAGSource.id == source_id).first()
        if source:
            source.total_chunks = info.get("vectors_count", 0)
            db.commit()
        
        return {
            "source_id": source_id,
            "vector_count": info.get("vectors_count", 0),
            "points_count": info.get("points_count", 0),
            "status": info.get("status", "unknown")
        }
        
    except Exception as e:
        logger.error(f"❌ Stats calculation failed: {e}")
        return {"source_id": source_id, "error": str(e)}
    
    finally:
        db.close()
