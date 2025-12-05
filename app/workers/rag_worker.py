"""
Gistify PKB Celery Workers
===========================
PKB (Personal Knowledge Base) oluşturma için background task'lar.

NOT: Bu worker Source modeli ile çalışır. 
Source.content alanındaki metni chunk'lara ayırır, embedding oluşturur ve Qdrant'a kaydeder.
"""

import hashlib
import uuid
from typing import Dict, Any
from datetime import datetime
from celery.utils.log import get_task_logger

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.source import Source
from app.models.rag import PKBChunk
from app.models.user import User
from app.services.credit_service import get_credit_service
from app.models.credit_transaction import OperationType
from app.services.rag_service import (
    RAGService, TextChunker, EmbeddingModel
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
    1. Source.content'i alır
    2. Metni chunk'lara ayırır
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
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.error(f"❌ Source not found: {source_id}")
            return {"success": False, "error": "Source not found"}
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"❌ User not found: {user_id}")
            return {"success": False, "error": "User not found"}
        
        # Update source status
        source.pkb_status = "processing"
        db.commit()
        
        self.update_state(state='PROGRESS', meta={
            'status': 'İçerik hazırlanıyor',
            'progress': 10
        })
        
        # Check content
        if not source.content or len(source.content.strip()) < 100:
            logger.warning(f"⚠️ Source content too short: {source_id}")
            source.pkb_status = "error"
            source.pkb_error_message = "İçerik çok kısa (min 100 karakter)"
            db.commit()
            return {"success": False, "error": "Content too short"}
        
        logger.info(f"📊 Source content length: {len(source.content)} chars")
        
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
        
        # Chunk the content
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk_text(source.content, metadata={
            "source_id": source_id,
            "title": source.title
        })
        
        if not chunks:
            logger.warning(f"⚠️ No chunks created: {source_id}")
            source.pkb_status = "error"
            source.pkb_error_message = "Chunk oluşturulamadı"
            db.commit()
            return {"success": False, "error": "No chunks created"}
        
        logger.info(f"📊 Created {len(chunks)} chunks")
        
        self.update_state(state='PROGRESS', meta={
            'status': 'Embedding oluşturuluyor',
            'progress': 40
        })
        
        # Create embeddings in batches
        chunk_texts = [c.content for c in chunks]
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
        
        # Create collection name
        collection_name = f"gistify_source_{source_id}"
        
        # Create collection
        rag_service.vector_store.create_collection(
            collection_name=collection_name,
            vector_size=emb_dimensions
        )
        
        # Delete old chunks from database
        db.query(PKBChunk).filter(PKBChunk.source_id == source_id).delete()
        db.commit()
        
        # Prepare points for Qdrant and save to database
        points = []
        total_tokens = 0
        
        for i, (chunk, emb) in enumerate(zip(chunks, all_embeddings)):
            point_id = str(uuid.uuid4())
            chunk_id = f"source_{source_id}_chunk_{i}"
            
            points.append({
                "id": point_id,
                "vector": emb,
                "payload": {
                    "source_id": source_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "content": chunk.content,
                    "title": source.title,
                    "metadata": chunk.metadata
                }
            })
            
            # Save chunk to database
            db_chunk = PKBChunk(
                source_id=source_id,
                user_id=user_id,
                chunk_id=chunk_id,
                chunk_index=i,
                content=chunk.content,
                content_hash=hashlib.md5(chunk.content.encode()).hexdigest(),
                token_count=chunk.token_count,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                embedding_model=embedding_model,
                embedding_dimensions=emb_dimensions,
                is_embedded=True,
                embedded_at=datetime.utcnow(),
                vector_collection=collection_name,
                vector_point_id=point_id,
                chunk_metadata=chunk.metadata
            )
            db.add(db_chunk)
            total_tokens += chunk.token_count
        
        db.commit()
        
        # Upsert to Qdrant
        rag_service.vector_store.upsert_vectors(
            collection_name=collection_name,
            points=points
        )
        
        logger.info(f"✅ Saved {len(points)} vectors to Qdrant")
        
        self.update_state(state='PROGRESS', meta={
            'status': 'Tamamlanıyor',
            'progress': 90
        })
        
        # Calculate credits
        # 1 credit per 1000 tokens for embedding
        credits_used = round(total_tokens / 1000, 2)
        
        # Deduct credits
        credit_service = get_credit_service(db)
        credit_service.deduct_credits(
            user_id=user_id,
            amount=credits_used,
            operation_type=OperationType.RAG_PKB_CREATION,
            description=f"PKB oluşturma: {source.title[:50]}",
            metadata={
                "source_id": source_id,
                "chunks": len(chunks),
                "tokens": total_tokens,
                "embedding_model": embedding_model
            }
        )
        
        # Update source
        source.pkb_enabled = True
        source.pkb_status = "ready"
        source.pkb_collection_name = collection_name
        source.pkb_chunk_count = len(chunks)
        source.pkb_embedding_model = embedding_model
        source.pkb_chunk_size = chunk_size
        source.pkb_chunk_overlap = chunk_overlap
        source.pkb_created_at = datetime.utcnow()
        source.pkb_credits_used = credits_used
        source.pkb_error_message = None
        db.commit()
        
        logger.info(f"✅ PKB creation completed: source_id={source_id}, chunks={len(chunks)}, credits={credits_used}")
        
        return {
            "success": True,
            "source_id": source_id,
            "chunks": len(chunks),
            "tokens": total_tokens,
            "credits_used": credits_used,
            "collection_name": collection_name
        }
        
    except Exception as e:
        logger.error(f"❌ PKB creation failed: {e}", exc_info=True)
        
        # Update source status
        try:
            source = db.query(Source).filter(Source.id == source_id).first()
            if source:
                source.pkb_status = "error"
                source.pkb_error_message = str(e)[:500]
                db.commit()
        except:
            pass
        
        raise self.retry(exc=e)
        
    finally:
        db.close()


# =========================================================================
# PKB DELETE TASK
# =========================================================================

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=30
)
def delete_pkb_task(self, source_id: int, user_id: int):
    """
    PKB silme task'ı
    
    1. Qdrant collection'ı siler
    2. Database'den chunk'ları siler
    3. Source'u günceller
    """
    db = SessionLocal()
    logger.info(f"🗑️ PKB deletion started: source_id={source_id}")
    
    try:
        # Get source
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            logger.warning(f"⚠️ Source not found: {source_id}")
            return {"success": False, "error": "Source not found"}
        
        # Delete from Qdrant
        if source.pkb_collection_name:
            try:
                rag_service = create_rag_service()
                rag_service.vector_store.delete_collection(source.pkb_collection_name)
                logger.info(f"✅ Deleted Qdrant collection: {source.pkb_collection_name}")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete Qdrant collection: {e}")
        
        # Delete chunks from database
        deleted_count = db.query(PKBChunk).filter(PKBChunk.source_id == source_id).delete()
        logger.info(f"✅ Deleted {deleted_count} chunks from database")
        
        # Update source
        source.pkb_enabled = False
        source.pkb_status = "not_created"
        source.pkb_collection_name = None
        source.pkb_chunk_count = 0
        source.pkb_embedding_model = None
        source.pkb_chunk_size = None
        source.pkb_chunk_overlap = None
        source.pkb_created_at = None
        source.pkb_error_message = None
        db.commit()
        
        logger.info(f"✅ PKB deletion completed: source_id={source_id}")
        
        return {"success": True, "deleted_chunks": deleted_count}
        
    except Exception as e:
        logger.error(f"❌ PKB deletion failed: {e}", exc_info=True)
        raise self.retry(exc=e)
        
    finally:
        db.close()


# =========================================================================
# PKB REINDEX TASK
# =========================================================================

@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60
)
def reindex_pkb_task(self, source_id: int, user_id: int, options: Dict[str, Any]):
    """
    PKB yeniden indexleme task'ı
    
    Mevcut PKB'yi silip yeniden oluşturur.
    """
    logger.info(f"🔄 PKB reindex started: source_id={source_id}")
    
    # First delete
    delete_result = delete_pkb_task(source_id, user_id)
    if not delete_result.get("success"):
        return {"success": False, "error": "Delete failed"}
    
    # Then recreate
    create_result = create_pkb_task(source_id, user_id, options)
    return create_result
