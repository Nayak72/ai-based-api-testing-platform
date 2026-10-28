"""
KB ingestion CLI — embeds all OWASP and HTTP knowledge base markdown files into ChromaDB.

Usage:
    python -m app.rag.ingest_kb
    python -m app.rag.ingest_kb --vector-dir ./data/chroma

Idempotent: uses content hash as chunk ID, so re-running only updates changed files.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

import structlog

logger = structlog.get_logger()

KB_DIR = Path(__file__).parent / "kb"

COLLECTION_MAP = {
    "owasp_api_top10_2023": "owasp_kb",
    "http_kb": "http_kb",
}


async def ingest_kb(vector_dir: str = "./data/chroma") -> None:
    """Ingest all KB markdown files into ChromaDB. Idempotent."""
    try:
        from app.rag.embeddings import SentenceTransformerEmbedder
        from app.rag.store import ChromaStore
    except ImportError as e:
        logger.error("Missing dependency for RAG ingest", error=str(e))
        sys.exit(1)

    store = ChromaStore(path=vector_dir)
    embedder = SentenceTransformerEmbedder()

    ingested = skipped = 0

    for folder, collection in COLLECTION_MAP.items():
        folder_path = KB_DIR / folder
        if not folder_path.exists():
            logger.warning("KB folder not found", folder=folder)
            continue

        for md_file in sorted(folder_path.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
            chunk_id = f"kb:{folder}:{md_file.stem}:{content_hash}"

            metadata = {
                "file": md_file.name,
                "kind": "kb",
                "folder": folder,
                "hash": content_hash,
            }

            try:
                embedding = await embedder.embed_one(text[:4000])  # cap at ~4k chars
                await store.upsert(
                    collection,
                    ids=[chunk_id],
                    texts=[text[:4000]],
                    embeddings=[embedding],
                    metadatas=[metadata],
                )
                logger.info("Ingested", file=md_file.name, collection=collection)
                ingested += 1
            except Exception as e:
                logger.error("Ingest failed for file", file=md_file.name, error=str(e))

    logger.info("KB ingestion complete", ingested=ingested, skipped=skipped)


if __name__ == "__main__":
    import os

    vector_dir = os.environ.get("VECTOR_DIR", "./data/chroma")

    # Parse --vector-dir argument
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith("--vector-dir="):
            vector_dir = arg.split("=", 1)[1]
        elif arg == "--vector-dir" and i + 1 < len(sys.argv):
            vector_dir = sys.argv[i + 1]

    asyncio.run(ingest_kb(vector_dir))
