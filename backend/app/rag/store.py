"""VectorStore interface + ChromaDB persistent implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class RetrievedChunk:
    id: str
    collection: str
    text: str
    score: float
    metadata: dict


class VectorStore(ABC):
    @abstractmethod
    async def upsert(
        self,
        collection: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None: ...

    @abstractmethod
    async def query(
        self,
        collection: str,
        query_embedding: list[float],
        k: int = 6,
        filters: dict | None = None,
    ) -> list[RetrievedChunk]: ...

    @abstractmethod
    async def delete_by_filter(self, collection: str, filters: dict) -> None: ...

    @abstractmethod
    async def count(self, collection: str) -> int: ...


class ChromaStore(VectorStore):
    def __init__(self, path: str) -> None:
        self.path = path
        self._client = None

    def _client_instance(self):
        if self._client is None:
            import chromadb

            self._client = chromadb.PersistentClient(path=self.path)
        return self._client

    def _col(self, name: str):
        return self._client_instance().get_or_create_collection(name)

    async def upsert(
        self,
        collection: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        import asyncio

        col = self._col(collection)
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas),
        )

    async def query(
        self,
        collection: str,
        query_embedding: list[float],
        k: int = 6,
        filters: dict | None = None,
    ) -> list[RetrievedChunk]:
        import asyncio

        col = self._col(collection)
        n = min(k, await self.count(collection))
        if n == 0:
            return []

        kwargs: dict = {"query_embeddings": [query_embedding], "n_results": n}
        if filters:
            kwargs["where"] = filters

        results = await asyncio.get_event_loop().run_in_executor(None, lambda: col.query(**kwargs))

        chunks: list[RetrievedChunk] = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Chroma returns L2 distance; convert to similarity score
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = max(0.0, 1.0 - distance)
                chunks.append(
                    RetrievedChunk(
                        id=doc_id,
                        collection=collection,
                        text=results["documents"][0][i],
                        score=score,
                        metadata=(results["metadatas"][0][i] if results.get("metadatas") else {}),
                    )
                )
        return chunks

    async def delete_by_filter(self, collection: str, filters: dict) -> None:
        import asyncio

        col = self._col(collection)
        await asyncio.get_event_loop().run_in_executor(None, lambda: col.delete(where=filters))

    async def count(self, collection: str) -> int:
        import asyncio

        try:
            col = self._col(collection)
            return await asyncio.get_event_loop().run_in_executor(None, col.count)
        except Exception:
            return 0
