"""Knowledge-Base routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from app.api.deps import CurrentUserId
from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


class KBStatus(BaseModel):
    owasp_count: int
    http_kb_count: int
    spec_chunks_count: int
    total: int


@router.get("/status", response_model=KBStatus)
async def kb_status(_user_id: CurrentUserId):
    """Return document counts per collection."""
    try:
        from app.rag.store import ChromaStore

        settings = get_settings()
        store = ChromaStore(path=settings.vector_dir)
        owasp = await store.count("owasp_kb")
        http_kb = await store.count("http_kb")
        spec_chunks = await store.count("spec_chunks")
        return KBStatus(
            owasp_count=owasp,
            http_kb_count=http_kb,
            spec_chunks_count=spec_chunks,
            total=owasp + http_kb + spec_chunks,
        )
    except Exception as e:
        logger.warning("KB status check failed", error=str(e))
        return KBStatus(owasp_count=0, http_kb_count=0, spec_chunks_count=0, total=0)


@router.post("/reindex")
async def reindex_kb(background_tasks: BackgroundTasks, _user_id: CurrentUserId):
    """Trigger a full KB re-index in the background."""

    async def _run():
        try:
            from app.rag.ingest_kb import ingest_kb

            await ingest_kb(get_settings().vector_dir)
            logger.info("KB re-index complete")
        except Exception as e:
            logger.error("KB re-index failed", error=str(e))

    background_tasks.add_task(_run)
    return {"status": "reindex_started"}


@router.get("/search")
async def search_kb(
    q: str = Query(..., min_length=1),
    spec_id: str | None = Query(None),
    limit: int = Query(5, ge=1, le=20),
    _user_id: CurrentUserId = None,
):
    """Search the knowledge base."""
    try:
        from app.rag.embeddings import SentenceTransformerEmbedder
        from app.rag.retriever import Retriever
        from app.rag.store import ChromaStore

        settings = get_settings()
        if not settings.embedding_model:
            raise ValueError("EMBEDDING_MODEL must be configured to search the knowledge base")
        retriever = Retriever(
            store=ChromaStore(path=settings.vector_dir),
            embedder=SentenceTransformerEmbedder(settings.embedding_model),
        )
        chunks = await retriever.retrieve(
            query=q,
            collections=["owasp_kb", "http_kb", "spec_chunks"],
            filters={"spec_id": spec_id} if spec_id else None,
            k=limit,
        )
        results = [
            {
                "id": c.id,
                "collection": c.collection,
                "text": c.text,
                "score": c.score,
                "metadata": c.metadata,
            }
            for c in chunks
        ]
        return {"results": results, "query": q}
    except Exception as e:
        logger.warning("KB search failed", error=str(e))
        return {"results": [], "query": q, "error": str(e)}
