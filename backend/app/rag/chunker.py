"""Spec → vector chunks. One chunk per endpoint, one per component schema."""

from __future__ import annotations

import hashlib
import json


def chunk_spec(spec: dict, spec_id: str) -> list[dict]:
    """
    Convert a parsed OpenAPI spec into embeddable text chunks.
    Returns list of {id, text, metadata}.
    """
    chunks: list[dict] = []

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue

            endpoint_id = f"{method.lower()}_{path.replace('/', '_').strip('_')}"

            parts = [
                f"Endpoint: {method.upper()} {path}",
                f"Summary: {operation.get('summary', '')}",
                f"Description: {operation.get('description', '')}",
            ]

            params = operation.get("parameters", [])
            if params:
                parts.append("Parameters: " + json.dumps(params, default=str)[:600])

            req_body = operation.get("requestBody", {})
            if req_body:
                parts.append("Request Body: " + json.dumps(req_body, default=str)[:600])

            responses = operation.get("responses", {})
            if responses:
                parts.append("Responses: " + json.dumps(responses, default=str)[:600])

            security = operation.get("security", [])
            if security:
                parts.append("Security: " + json.dumps(security))

            tags = operation.get("tags", [])

            text = "\n".join(p for p in parts if p.strip())
            chunk_id = hashlib.sha256(f"{spec_id}:{endpoint_id}".encode()).hexdigest()[:20]

            chunks.append(
                {
                    "id": chunk_id,
                    "text": text,
                    "metadata": {
                        "spec_id": spec_id,
                        "endpoint_id": endpoint_id,
                        "kind": "endpoint",
                        "path": path,
                        "method": method.upper(),
                        "tags": ",".join(tags),
                    },
                }
            )

    # Component schemas
    for schema_name, schema_def in spec.get("components", {}).get("schemas", {}).items():
        text = f"Schema: {schema_name}\n" + json.dumps(schema_def, default=str)[:900]
        chunk_id = hashlib.sha256(f"{spec_id}:schema:{schema_name}".encode()).hexdigest()[:20]
        chunks.append(
            {
                "id": chunk_id,
                "text": text,
                "metadata": {
                    "spec_id": spec_id,
                    "kind": "schema",
                    "schema_name": schema_name,
                },
            }
        )

    return chunks
