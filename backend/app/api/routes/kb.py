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
        store = ChromaStore(persist_directory=settings.vector_dir)
        owasp = store.get_or_create("owasp_kb").count()
        http_kb = store.get_or_create("http_kb").count()
        spec_chunks = store.get_or_create("spec_chunks").count()
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

            await ingest_kb()
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
        from app.rag.retriever import Retriever

        settings = get_settings()
        retriever = Retriever(
            vector_dir=settings.vector_dir,
            embedding_provider=settings.embedding_provider,
            embedding_model=settings.embedding_model,
        )
        results = await retriever.retrieve(
            query=q,
            spec_id=spec_id,
            top_k=limit,
        )
        return {"results": results, "query": q}
    except Exception as e:
        logger.warning("KB search failed", error=str(e))
        return {"results": [], "query": q, "error": str(e)}
