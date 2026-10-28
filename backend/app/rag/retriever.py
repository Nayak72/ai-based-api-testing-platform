"""Retriever — embeds a query and fetches top-k chunks from VectorStore."""

from __future__ import annotations

import structlog

from app.rag.embeddings import Embedder
from app.rag.store import RetrievedChunk, VectorStore

logger = structlog.get_logger()


class Retriever:
    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self.store = store
        self.embedder = embedder

    async def retrieve(
        self,
        query: str,
        collections: list[str],
        filters: dict | None = None,
        k: int = 6,
    ) -> list[RetrievedChunk]:
        """Embed query, fetch from each collection, merge, return top-k."""
        try:
            query_embedding = await self.embedder.embed_one(query)
        except Exception as e:
            logger.warning("Embedder unavailable — skipping RAG retrieval", error=str(e))
            return []

        all_chunks: list[RetrievedChunk] = []
        for collection in collections:
            try:
                chunks = await self.store.query(collection, query_embedding, k=k, filters=filters)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning("Vector store query failed", collection=collection, error=str(e))

        all_chunks.sort(key=lambda c: c.score, reverse=True)
        return all_chunks[:k]
