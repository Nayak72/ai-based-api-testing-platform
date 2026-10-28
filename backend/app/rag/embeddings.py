"""Embedder interface and implementations (OpenAI-compatible + SentenceTransformers)."""

from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

logger = structlog.get_logger()


class Embedder(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_one(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]


class OpenAICompatEmbedder(Embedder):
    """Uses /embeddings endpoint — Ollama nomic-embed-text, OpenAI, etc."""

    def __init__(self, base_url: str, api_key: str | None, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                json={"input": texts, "model": self.model},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]


class SentenceTransformerEmbedder(Embedder):
    """Local embedder — no external calls. Lazy-loads the model on first use."""

    def __init__(self, model: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model
        self._model = None

    def _load(self) -> None:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info("SentenceTransformer loaded", model=self.model_name)
            except ImportError:
                raise ImportError("sentence-transformers is not installed. Run: pip install sentence-transformers")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        self._load()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, lambda: self._model.encode(texts).tolist())
        return embeddings
