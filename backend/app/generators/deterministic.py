"""Contract-derived tests that complement, but never depend on, an LLM response."""

from __future__ import annotations

import hashlib
import json

from bson import ObjectId

from app.db.models import ExpectedResponse, RequestTemplate, TestCaseCreate, TestCaseMetadata


class DeterministicGenerator:
    """Create small, safe baseline cases from an endpoint's OpenAPI contract."""

    def generate(self, *, spec_id: ObjectId, endpoint: dict, category: str, subcategory: str) -> list[TestCaseCreate]:
        method = str(endpoint.get("method", "GET")).upper()
        path = str(endpoint.get("path", "/"))
        endpoint_id = str(endpoint["endpoint_id"])
        request = self._request(method, path, endpoint)
        if category == "functional":
            return [self._case(spec_id, endpoint_id, category, subcategory, "Documented request", "Exercises the endpoint using documented request fields.", request, self._success_status(endpoint), endpoint)]
        if category == "malformed":
            required = next((p for p in endpoint.get("parameters", []) if p.get("required")), None)
            if not required:
                return []
            malformed = self._request(method, path, endpoint)
            malformed.query_params.pop(required.get("name", ""), None)
            return [self._case(spec_id, endpoint_id, category, subcategory, f"Missing required {required.get('name', 'parameter')}", "Omits one required documented parameter and expects request validation.", malformed, 400, endpoint)]
        if category == "edge":
            numeric = next((p for p in endpoint.get("parameters", []) if p.get("schema", {}).get("type") in {"integer", "number"}), None)
            if not numeric:
                return []
            boundary = self._request(method, path, endpoint)
            boundary.query_params[numeric.get("name", "value")] = numeric.get("schema", {}).get("minimum", 0)
            return [self._case(spec_id, endpoint_id, category, subcategory, f"Boundary value for {numeric.get('name', 'parameter')}", "Uses the documented minimum boundary for a numeric parameter.", boundary, self._success_status(endpoint), endpoint)]
        return []

    @staticmethod
    def _request(method: str, path: str, endpoint: dict) -> RequestTemplate:
        query_params: dict[str, object] = {}
        resolved_path = path
        for parameter in endpoint.get("parameters", []):
            name = parameter.get("name")
            if not name or not parameter.get("required"):
                continue
            value = DeterministicGenerator._sample(parameter.get("schema", {}))
            if parameter.get("in") == "path":
                resolved_path = resolved_path.replace("{" + name + "}", str(value))
            elif parameter.get("in") == "query":
                query_params[name] = value
        return RequestTemplate(method=method, path=resolved_path, query_params=query_params)

    @staticmethod
    def _sample(schema: dict) -> object:
        if schema.get("example") is not None:
            return schema["example"]
        if schema.get("enum"):
            return schema["enum"][0]
        return {"integer": 1, "number": 1, "boolean": True}.get(schema.get("type"), "sample")

    @staticmethod
    def _success_status(endpoint: dict) -> int:
        responses = endpoint.get("responses") or {}
        for code in responses:
            if str(code).startswith("2"):
                return int(code)
        return 201 if str(endpoint.get("method", "")).upper() == "POST" else 200

    @staticmethod
    def _case(spec_id: ObjectId, endpoint_id: str, category: str, subcategory: str, title: str, description: str, request: RequestTemplate, status_code: int, endpoint: dict) -> TestCaseCreate:
        request_data = request.model_dump()
        request_hash = "sha256:" + hashlib.sha256(json.dumps(request_data, sort_keys=True, default=str).encode()).hexdigest()
        return TestCaseCreate(
            spec_id=spec_id, endpoint_id=endpoint_id, category=category, subcategory=subcategory,
            title=title, description=description, request=request,
            expected=ExpectedResponse(status_code=status_code),
            metadata=TestCaseMetadata(generated_by="deterministic", generation_prompt_hash="contract-derived-v1", tokens_used=0, request_hash=request_hash),
        )
