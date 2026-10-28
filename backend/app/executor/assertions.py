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
        result = _evaluate_single_assertion(status_assertion, status_code, headers, body, response_schema, duration_ms)
        results.append(AssertionResult(assertion=status_assertion, result=result))

    for assertion in assertions:
        try:
            result = _evaluate_single_assertion(assertion, status_code, headers, body, response_schema, duration_ms)
            results.append(AssertionResult(assertion=assertion, result=result))
        except Exception as e:
            logger.warning("Assertion evaluation error", assertion=assertion.model_dump(), error=str(e))
            results.append(AssertionResult(assertion=assertion, result=False))

    return results


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
