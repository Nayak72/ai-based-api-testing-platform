"""IngestAgent — parse spec, build endpoint list, chunk + embed into spec_chunks."""

from __future__ import annotations

import structlog

from app.agents.base import BaseAgent
from app.agents.state import SessionState

logger = structlog.get_logger()


class IngestAgent(BaseAgent):
    def __init__(self):
        super().__init__("ingest")

    async def run(self, state: SessionState) -> SessionState:
        await self.emit(state, "ingest", "started", "Parsing spec and building index...")
        try:
            from bson import ObjectId
            from app.db.repositories import spec_repository

            spec_id = state.get("spec_id", "")
            user_id = state.get("user_id", "")

            spec = await spec_repository.get_by_id(ObjectId(spec_id), ObjectId(user_id))

            if not spec:
                state.setdefault("errors", []).append("Spec not found")
                await self.emit(state, "ingest", "failed", "Spec not found")
                return state

            # Self-healing: if raw_content is missing, check bundled specs by name
            if not spec.raw_content:
                from pathlib import Path
                modes_dir = Path(__file__).parent.parent / "modes" / "specs"
                spec_name_lower = spec.name.lower()
                for candidate in modes_dir.glob("*.json"):
                    if candidate.stem in spec_name_lower or ("vulnshop" in spec_name_lower and "vulnshop" in candidate.stem):
                        spec.raw_content = candidate.read_text(encoding="utf-8")
                        await spec_repository.collection.update_one(
                            {"_id": ObjectId(spec_id)},
                            {"$set": {"raw_content": spec.raw_content}},
                        )
                        break

            # Auto-parse if spec has raw_content but wasn't parsed yet
            if not spec.parsed_spec and spec.raw_content:
                await self.emit(state, "ingest", "progress", "Spec not yet parsed — auto-parsing now...")
                try:
                    from app.parsers import parse_openapi_spec, parse_postman_collection

                    await spec_repository.update_status(ObjectId(spec_id), "parsing")
                    if spec.source_type == "openapi":
                        parsed, eps, version, base_url = await parse_openapi_spec(spec.raw_content)
                    else:
                        parsed, eps, version, base_url = await parse_postman_collection(spec.raw_content)
                    await spec_repository.update_parsed(ObjectId(spec_id), parsed, len(eps), version, base_url)
                    # Reload spec
                    spec = await spec_repository.get_by_id(ObjectId(spec_id), ObjectId(user_id))
                except Exception as pe:
                    state.setdefault("errors", []).append(f"Auto-parse failed: {pe}")
                    await self.emit(state, "ingest", "failed", f"Spec auto-parse failed: {pe}")
                    return state

            if not spec or not spec.parsed_spec:
                state.setdefault("errors", []).append("Spec not parsed. Please upload raw content and re-parse.")
                await self.emit(state, "ingest", "failed", "Spec not parsed. Please upload raw content and re-parse.")
                return state

            # Extract endpoints
            from app.parsers import extract_endpoints

            endpoints = extract_endpoints(spec.parsed_spec)

            await self.emit(
                state, "ingest", "progress", f"Found {len(endpoints)} endpoints, embedding into vector store..."
            )

            # Try to chunk and embed (graceful degradation if RAG unavailable)
            try:
                from app.config import get_settings

                settings = get_settings()
                from app.rag.chunker import chunk_spec
                from app.rag.embeddings import SentenceTransformerEmbedder
                from app.rag.store import ChromaStore

                chunks = chunk_spec(spec.parsed_spec, spec_id)
                store = ChromaStore(path=getattr(settings, "vector_dir", "./data/chroma"))
                embedder = SentenceTransformerEmbedder(getattr(settings, "embedding_model", "all-MiniLM-L6-v2"))

                texts = [c["text"] for c in chunks]
                embeddings = await embedder.embed(texts)
                ids = [c["id"] for c in chunks]
                metadatas = [c["metadata"] for c in chunks]
                await store.upsert("spec_chunks", ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)
                await self.emit(
                    state, "ingest", "progress", f"Indexed {len(chunks)} chunks into vector store", rag_used=True
                )
            except Exception as e:
                logger.warning("RAG indexing failed (continuing without RAG)", error=str(e))
                await self.emit(
                    state,
                    "ingest",
                    "progress",
                    f"RAG indexing unavailable: {e}. Continuing without RAG.",
                    rag_used=False,
                )

            await self.emit(state, "ingest", "completed", f"Ingest complete: {len(endpoints)} endpoints")
            return state

        except Exception as e:
            logger.exception("IngestAgent failed", error=str(e))
            state.setdefault("errors", []).append(f"IngestAgent: {e}")
            await self.emit(state, "ingest", "failed", str(e))
            return state
