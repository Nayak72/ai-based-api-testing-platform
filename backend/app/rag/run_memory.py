"""Run memory — stores confirmed bugs and false positives in the vector store after each run."""

from __future__ import annotations

import hashlib

import structlog

logger = structlog.get_logger()


async def save_run_memory(
    spec_id: str,
    run_id: str,
    confirmed_bugs: list[dict],
    false_positives: list[dict],
    vector_store,
    embedder,
) -> None:
    """
    Embed and persist run outcome summaries into the 'run_memory' collection.
    Called after triage completes; used by PlannerAgent and TriageAgent on future runs.
    """
    entries = []

    for bug in confirmed_bugs:
        text = (
            f"Confirmed bug in spec {spec_id}: "
            f"endpoint={bug.get('endpoint_id', '?')} "
            f"category={bug.get('category', '?')} "
            f"owasp={bug.get('owasp_category', '?')} "
            f"description={bug.get('description', '')}"
        )
        entries.append(
            {
                "text": text,
                "metadata": {
                    "kind": "confirmed_bug",
                    "spec_id": spec_id,
                    "run_id": run_id,
                    "endpoint_id": bug.get("endpoint_id", ""),
                    "category": bug.get("category", ""),
                    "owasp_category": bug.get("owasp_category", ""),
                },
            }
        )

    for fp in false_positives:
        text = (
            f"False positive in spec {spec_id}: "
            f"endpoint={fp.get('endpoint_id', '?')} "
            f"category={fp.get('category', '?')} "
            f"reason={fp.get('reason', '')}"
        )
        entries.append(
            {
                "text": text,
                "metadata": {
                    "kind": "false_positive",
                    "spec_id": spec_id,
                    "run_id": run_id,
                    "endpoint_id": fp.get("endpoint_id", ""),
                    "category": fp.get("category", ""),
                },
            }
        )

    for entry in entries:
        try:
            embedding = await embedder.embed_one(entry["text"])
            chunk_id = hashlib.sha256(f"{run_id}:{entry['text'][:80]}".encode()).hexdigest()[:20]
            await vector_store.upsert(
                "run_memory",
                ids=[chunk_id],
                texts=[entry["text"]],
                embeddings=[embedding],
                metadatas=[entry["metadata"]],
            )
        except Exception as e:
            logger.warning("Failed to save run memory entry", error=str(e))

    if entries:
        logger.info("Run memory saved", spec_id=spec_id, run_id=run_id, entries=len(entries))
