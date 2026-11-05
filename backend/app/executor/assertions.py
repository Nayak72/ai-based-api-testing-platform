import json
from typing import Any

import structlog
from jsonpath_ng import parse as jsonpath_parse
from jsonschema import ValidationError, validate

from app.db.models import Assertion, AssertionResult

logger = structlog.get_logger()


def evaluate_assertions(
    assertions: list[Assertion],
    status_code: int,
    headers: dict,
    body: str | None,
    response_schema: dict | None = None,
    expected_status_code: int | None = None,
    duration_ms: int | None = None,
) -> list[AssertionResult]:
    results = []

    # Always evaluate status code if expected_status_code is provided
    if expected_status_code is not None:
        status_assertion = Assertion(type="status_code", path="", operator="eq", value=expected_status_code)
        results.append(_build_result(status_assertion, status_code, headers, body, response_schema, duration_ms))

    for assertion in assertions:
        try:
            results.append(_build_result(assertion, status_code, headers, body, response_schema, duration_ms))
        except Exception as e:
            logger.warning("Assertion evaluation error", assertion=assertion.model_dump(), error=str(e))
            results.append(AssertionResult(
                assertion=assertion, result=False, name=_assertion_name(assertion),
                assertion_type=assertion.type, path=assertion.path, operator=assertion.operator,
                expected=assertion.value, actual=None, message=f"Assertion could not be evaluated: {type(e).__name__}",
            ))

    # A schema supplied by a test case is itself an assertion, even when the
    # generator did not emit a redundant explicit schema assertion.
    if response_schema and not any(item.assertion.type == "schema" for item in results):
        schema_assertion = Assertion(type="schema", path="$", operator="valid", value=True)
        results.append(_build_result(schema_assertion, status_code, headers, body, response_schema, duration_ms))

    return results


def _assertion_name(assertion: Assertion) -> str:
    if assertion.type == "status_code":
        return "Response status matches expected outcome"
    if assertion.type == "header":
        return f"Response header {assertion.path}"
    if assertion.type == "json_path":
        return f"Response value at {assertion.path}"
    if assertion.type == "schema":
        return "Response matches documented schema"
    if assertion.type == "response_time":
        return "Response time constraint"
    return assertion.type


def _actual_value(assertion: Assertion, status_code: int, headers: dict, body: str | None, duration_ms: int | None) -> Any:
    if assertion.type == "status_code":
        return status_code
    if assertion.type == "header":
        return headers.get(assertion.path.lower())
    if assertion.type == "response_time":
        return duration_ms
    if assertion.type == "json_path" and body:
        try:
            matches = [match.value for match in jsonpath_parse(assertion.path).find(json.loads(body))]
            return matches[0] if len(matches) == 1 else matches
        except Exception:
            return None
    return None


def _build_result(assertion: Assertion, status_code: int, headers: dict, body: str | None, response_schema: dict | None, duration_ms: int | None) -> AssertionResult:
    actual = _actual_value(assertion, status_code, headers, body, duration_ms)
    passed = _evaluate_single_assertion(assertion, status_code, headers, body, response_schema, duration_ms)
    message = None if passed else f"Expected {assertion.operator} {assertion.value!r}; received {actual!r}."
    if assertion.type == "schema" and not passed:
        message = "The response body did not validate against the documented response schema."
    return AssertionResult(
        assertion=assertion, result=passed, name=_assertion_name(assertion), assertion_type=assertion.type,
        path=assertion.path, operator=assertion.operator, expected=assertion.value,
        actual=actual, message=message, evidence={"status_code": status_code, "duration_ms": duration_ms},
    )


def _evaluate_single_assertion(
    assertion: Assertion,
    status_code: int,
    headers: dict,
    body: str | None,
    response_schema: dict | None = None,
    duration_ms: int | None = None,
) -> bool:
    if assertion.type == "status_code":
        return _compare(status_code, assertion.operator, assertion.value)

    if assertion.type == "header":
        header_value = headers.get(assertion.path.lower(), "")
        return _compare(header_value, assertion.operator, assertion.value)

    if assertion.type == "json_path":
        if not body:
            return False
        try:
            data = json.loads(body)
            jsonpath_expr = jsonpath_parse(assertion.path)
            matches = [match.value for match in jsonpath_expr.find(data)]

            if not matches:
                return False

            if assertion.operator == "exists":
                return len(matches) > 0
            if assertion.operator == "is_array":
                return isinstance(matches[0], list)
            if assertion.operator == "is_object":
                return isinstance(matches[0], dict)
            if len(matches) == 1:
                return _compare(matches[0], assertion.operator, assertion.value)
            return any(_compare(m, assertion.operator, assertion.value) for m in matches)

        except (json.JSONDecodeError, Exception):
            return False

    elif assertion.type == "schema":
        if not body or not response_schema:
            return False
        try:
            data = json.loads(body)
            validate(instance=data, schema=response_schema)
            return True
        except (ValidationError, json.JSONDecodeError):
            return False

    elif assertion.type == "response_time":
        if duration_ms is None:
            return False
        return _compare(duration_ms, assertion.operator, assertion.value)

    return False


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "gt":
        return actual > expected
    if operator == "gte":
        return actual >= expected
    if operator == "lt":
        return actual < expected
    if operator == "lte":
        return actual <= expected
    if operator == "contains":
        if (isinstance(actual, str) and isinstance(expected, str)) or isinstance(actual, (list, tuple)):
            return expected in actual
        return False
    if operator == "startswith":
        return isinstance(actual, str) and actual.startswith(str(expected))
    if operator == "endswith":
        return isinstance(actual, str) and actual.endswith(str(expected))
    if operator == "matches":
        import re

        return bool(re.match(str(expected), str(actual)))
    if operator == "is_array":
        return isinstance(actual, list)
    if operator == "is_object":
        return isinstance(actual, dict)
    if operator == "is_null":
        return actual is None
    if operator == "not_null":
        return actual is not None
    return False
