import json
import re

import structlog
import yaml

logger = structlog.get_logger()


async def parse_postman_collection(raw_content: str) -> tuple[dict, list[dict], str, str]:
    try:
        try:
            collection = json.loads(raw_content)
        except json.JSONDecodeError:
            collection = yaml.safe_load(raw_content)

        if not collection or "item" not in collection:
            raise ValueError("Invalid Postman collection format")

        info = collection.get("info", {})
        name = info.get("name", "Imported Collection")

        # Extract baseUrl from collection variables
        base_url = "{{baseUrl}}"
        variables = collection.get("variable", [])
        if isinstance(variables, list):
            for var in variables:
                if var.get("key") == "baseUrl" and var.get("value"):
                    base_url = var["value"]
                    break

        openapi_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": name,
                "version": info.get("version", "1.0.0"),
                "description": info.get("description", ""),
            },
            "servers": [{"url": base_url}],
            "paths": {},
            "components": {"schemas": {}, "securitySchemes": {}},
        }

        endpoints = []
        _process_items(collection["item"], openapi_spec, endpoints, "")

        version = "3.0.3"

        return openapi_spec, endpoints, version, base_url

    except Exception as e:
        logger.error("Postman parse error", error=str(e))
        raise


def _process_items(items: list, spec: dict, endpoints: list, path_prefix: str) -> None:
    for item in items:
        if "item" in item:
            _process_items(item["item"], spec, endpoints, path_prefix)
        elif "request" in item:
            request = item["request"]
            method = request.get("method", "GET").lower()
            url = request.get("url", {})

            if isinstance(url, str):
                path = url
            else:
                path = url.get("path", [])
                if isinstance(path, list):
                    path = "/" + "/".join(str(p) for p in path)
                elif isinstance(path, str):
                    path = path if path.startswith("/") else "/" + path
                else:
                    path = "/"

            full_path = path_prefix + path
            full_path = _normalize_path(full_path)

            operation = _build_operation(request, item.get("name", ""), spec)

            if full_path not in spec["paths"]:
                spec["paths"][full_path] = {}
            spec["paths"][full_path][method] = operation

            endpoints.append(
                {
                    "method": method.upper(),
                    "path": full_path,
                    "operation": operation,
                }
            )


def _normalize_path(path: str) -> str:
    path = re.sub(r"\{\{(.*?)\}\}", r"{\1}", path)
    path = re.sub(r":(\w+)", r"{\1}", path)
    if not path.startswith("/"):
        path = "/" + path
    return path


def _build_operation(request: dict, name: str, openapi_spec: dict) -> dict:
    operation = {
        "summary": name,
        "description": request.get("description", ""),
        "parameters": [],
        "responses": {"default": {"description": "Default response"}},
    }

    url = request.get("url", {})
    if isinstance(url, dict):
        query_params = url.get("query", [])
        for param in query_params:
            if param.get("disabled"):
                continue
            operation["parameters"].append(
                {
                    "name": param.get("key", ""),
                    "in": "query",
                    "description": param.get("description", ""),
                    "required": False,
                    "schema": {"type": "string"},
                }
            )

        path_vars = url.get("variable", [])
        for param in path_vars:
            operation["parameters"].append(
                {
                    "name": param.get("key", ""),
                    "in": "path",
                    "description": param.get("description", ""),
                    "required": True,
                    "schema": {"type": "string"},
                }
            )

    headers = request.get("header", [])
    for header in headers:
        if header.get("disabled"):
            continue
        operation["parameters"].append(
            {
                "name": header.get("key", ""),
                "in": "header",
                "description": header.get("description", ""),
                "required": False,
                "schema": {"type": "string"},
            }
        )

    body = request.get("body", {})
    if body and body.get("mode") != "none":
        content_type = "application/json"
        if body.get("mode") == "formdata":
            content_type = "multipart/form-data"
        elif body.get("mode") == "urlencoded":
            content_type = "application/x-www-form-urlencoded"

        operation["requestBody"] = {
            "content": {
                content_type: {
                    "schema": {"type": "object"},
                }
            }
        }

    auth = request.get("auth", {})
    if auth and auth.get("type") != "noauth":
        operation["security"] = [{"bearerAuth": []}]
        if "bearerAuth" not in openapi_spec["components"]["securitySchemes"]:
            openapi_spec["components"]["securitySchemes"]["bearerAuth"] = {"type": "http", "scheme": "bearer"}

    return operation
