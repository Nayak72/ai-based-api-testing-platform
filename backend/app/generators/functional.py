import json

import structlog
from bson import ObjectId

from app.db.models import (
    ExpectedResponse,
    RequestTemplate,
    TestCaseCreate,
    TestCaseMetadata,
)
from app.generators.base import BaseGenerator

logger = structlog.get_logger()


class FunctionalGenerator(BaseGenerator):
    CATEGORY = "functional"
    SUBCATEGORIES = ["happy_path", "optional_params", "enum_values", "pagination"]
    PROMPT_VERSION = "v1"

    def get_system_prompt(self) -> str:
        return """You are an expert API testing engineer. Generate functional test cases in STRICT JSON format matching the provided schema. No explanations, no markdown, only valid JSON.

Each test case must include:
- endpoint_id: the stable endpoint identifier
- subcategory: one of "happy_path", "optional_params", "enum_values", "pagination"
- title: descriptive test name
- description: what this test verifies
- request: {method, path, headers, query_params, body}
- expected: {status_code, response_schema, assertions}
- metadata: {owasp_category, severity, generated_by, generation_prompt_hash, tokens_used, request_hash}

Output format: {"test_cases": [...]}"""

    def get_prompt_template_name(self) -> str:
        return "functional.j2"

    def parse_response(self, content: str, endpoint_id: str, spec_id: ObjectId) -> list[TestCaseCreate]:
        data = json.loads(content)
        test_cases = []
        for item in data.get("test_cases", []):
            tc = TestCaseCreate(
                spec_id=spec_id,
                endpoint_id=endpoint_id,
                category=self.CATEGORY,
                subcategory=item["subcategory"],
                title=item["title"],
                description=item["description"],
                request=RequestTemplate(**item["request"]),
                expected=ExpectedResponse(**item["expected"]),
                metadata=TestCaseMetadata(
                    owasp_category=item["metadata"].get("owasp_category"),
                    severity=item["metadata"].get("severity", "medium"),
                    generated_by="",
                    generation_prompt_hash="",
                    tokens_used=0,
                    request_hash="",
                ),
            )
            test_cases.append(tc)
        return test_cases


class EdgeGenerator(BaseGenerator):
    CATEGORY = "edge"
    SUBCATEGORIES = ["boundary_values", "string_length", "array_size", "datetime_edge", "numeric_precision"]
    PROMPT_VERSION = "v1"

    def get_system_prompt(self) -> str:
        return """You are an expert API testing engineer. Generate edge/boundary test cases in STRICT JSON format matching the provided schema. No explanations, no markdown, only valid JSON.

Each test case must include:
- endpoint_id: the stable endpoint identifier
- subcategory: one of "boundary_values", "string_length", "array_size", "datetime_edge", "numeric_precision"
- title: descriptive test name
- description: what boundary this test verifies
- request: {method, path, headers, query_params, body}
- expected: {status_code, response_schema, assertions}
- metadata: {owasp_category, severity, generated_by, generation_prompt_hash, tokens_used, request_hash}

Focus on: min/max boundaries, off-by-one, empty strings, max length, array limits, leap years, timezone variants, float precision.
Output format: {"test_cases": [...]}"""

    def get_prompt_template_name(self) -> str:
        return "edge.j2"

    def parse_response(self, content: str, endpoint_id: str, spec_id: ObjectId) -> list[TestCaseCreate]:
        data = json.loads(content)
        test_cases = []
        for item in data.get("test_cases", []):
            tc = TestCaseCreate(
                spec_id=spec_id,
                endpoint_id=endpoint_id,
                category=self.CATEGORY,
                subcategory=item["subcategory"],
                title=item["title"],
                description=item["description"],
                request=RequestTemplate(**item["request"]),
                expected=ExpectedResponse(**item["expected"]),
                metadata=TestCaseMetadata(
                    owasp_category=item["metadata"].get("owasp_category"),
                    severity=item["metadata"].get("severity", "medium"),
                    generated_by="",
                    generation_prompt_hash="",
                    tokens_used=0,
                    request_hash="",
                ),
            )
            test_cases.append(tc)
        return test_cases


class MalformedGenerator(BaseGenerator):
    CATEGORY = "malformed"
    SUBCATEGORIES = ["missing_required", "wrong_type", "invalid_enum", "malformed_json", "oversized_payload", "invalid_content_type", "path_traversal", "duplicate_params"]
    PROMPT_VERSION = "v1"

    def get_system_prompt(self) -> str:
        return """You are an expert API security and testing engineer. Generate malformed/negative test cases in STRICT JSON format matching the provided schema. No explanations, no markdown, only valid JSON.

Each test case must include:
- endpoint_id: the stable endpoint identifier
- subcategory: one of "missing_required", "wrong_type", "invalid_enum", "malformed_json", "oversized_payload", "invalid_content_type", "path_traversal", "duplicate_params"
- title: descriptive test name
- description: what invalid input this test sends
- request: {method, path, headers, query_params, body}
- expected: {status_code, response_schema, assertions} - typically expects 4xx errors
- metadata: {owasp_category, severity, generated_by, generation_prompt_hash, tokens_used, request_hash}

Focus on: missing required fields, type mismatches, invalid enums, broken JSON, huge payloads, wrong content-type, path traversal attempts, duplicate parameters.
Output format: {"test_cases": [...]}"""

    def get_prompt_template_name(self) -> str:
        return "malformed.j2"

    def parse_response(self, content: str, endpoint_id: str, spec_id: ObjectId) -> list[TestCaseCreate]:
        data = json.loads(content)
        test_cases = []
        for item in data.get("test_cases", []):
            tc = TestCaseCreate(
                spec_id=spec_id,
                endpoint_id=endpoint_id,
                category=self.CATEGORY,
                subcategory=item["subcategory"],
                title=item["title"],
                description=item["description"],
                request=RequestTemplate(**item["request"]),
                expected=ExpectedResponse(**item["expected"]),
                metadata=TestCaseMetadata(
                    owasp_category=item["metadata"].get("owasp_category"),
                    severity=item["metadata"].get("severity", "medium"),
                    generated_by="",
                    generation_prompt_hash="",
                    tokens_used=0,
                    request_hash="",
                ),
            )
            test_cases.append(tc)
        return test_cases


class SecurityGenerator(BaseGenerator):
    CATEGORY = "security"
    SUBCATEGORIES = [
        "bola", "broken_auth", "bopla", "resource_consumption", "bfla",
        "business_flow", "ssrf", "misconfiguration", "inventory", "unsafe_consumption"
    ]
    OWASP_MAPPING = {
        "bola": "API1:2023",
        "broken_auth": "API2:2023",
        "bopla": "API3:2023",
        "resource_consumption": "API4:2023",
        "bfla": "API5:2023",
        "business_flow": "API6:2023",
        "ssrf": "API7:2023",
        "misconfiguration": "API8:2023",
        "inventory": "API9:2023",
        "unsafe_consumption": "API10:2023",
    }
    PROMPT_VERSION = "v1"

    def get_system_prompt(self) -> str:
        return """You are an expert API security engineer. Generate OWASP API Top 10 2023 security test cases in STRICT JSON format matching the provided schema. No explanations, no markdown, only valid JSON.

Each test case must include:
- endpoint_id: the stable endpoint identifier
- subcategory: one of "bola", "broken_auth", "bopla", "resource_consumption", "bfla", "business_flow", "ssrf", "misconfiguration", "inventory", "unsafe_consumption"
- title: descriptive test name
- description: what vulnerability this test probes
- request: {method, path, headers, query_params, body} - include attack payloads
- expected: {status_code, response_schema, assertions} - check for data leakage, unauthorized access, etc.
- metadata: {owasp_category: "API1:2023" etc, severity: "high"/"critical", generated_by, generation_prompt_hash, tokens_used, request_hash}

OWASP Categories:
- API1: Broken Object Level Authorization (IDOR)
- API2: Broken Authentication
- API3: Broken Object Property Level Authorization
- API4: Unrestricted Resource Consumption
- API5: Broken Function Level Authorization
- API6: Unrestricted Access to Sensitive Business Flows
- API7: Server Side Request Forgery
- API8: Security Misconfiguration
- API9: Improper Inventory Management
- API10: Unsafe Consumption of APIs

Output format: {"test_cases": [...]}"""

    def get_prompt_template_name(self) -> str:
        return "security.j2"

    def parse_response(self, content: str, endpoint_id: str, spec_id: ObjectId) -> list[TestCaseCreate]:
        data = json.loads(content)
        test_cases = []
        for item in data.get("test_cases", []):
            subcat = item["subcategory"]
            tc = TestCaseCreate(
                spec_id=spec_id,
                endpoint_id=endpoint_id,
                category=self.CATEGORY,
                subcategory=subcat,
                title=item["title"],
                description=item["description"],
                request=RequestTemplate(**item["request"]),
                expected=ExpectedResponse(**item["expected"]),
                metadata=TestCaseMetadata(
                    owasp_category=self.OWASP_MAPPING.get(subcat),
                    severity=item["metadata"].get("severity", "high"),
                    generated_by="",
                    generation_prompt_hash="",
                    tokens_used=0,
                    request_hash="",
                ),
            )
            test_cases.append(tc)
        return test_cases
