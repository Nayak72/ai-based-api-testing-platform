"""Tests for spec chunker."""

from app.rag.chunker import chunk_spec


def test_chunk_spec_endpoints_and_schemas():
    sample_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "tags": ["Users"],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": "Create user",
                    "tags": ["Users"],
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}},
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }

    chunks = chunk_spec(sample_spec, "spec123")
    assert len(chunks) == 3

    endpoint_chunks = [c for c in chunks if c["metadata"]["kind"] == "endpoint"]
    schema_chunks = [c for c in chunks if c["metadata"]["kind"] == "schema"]

    assert len(endpoint_chunks) == 2
    assert len(schema_chunks) == 1

    methods = {c["metadata"]["method"] for c in endpoint_chunks}
    assert methods == {"GET", "POST"}
    assert schema_chunks[0]["metadata"]["schema_name"] == "User"
