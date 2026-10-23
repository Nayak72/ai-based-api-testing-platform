import structlog
from openapi_spec_validator import validate
from prance import ResolvingParser

logger = structlog.get_logger()


async def parse_openapi_spec(raw_content: str) -> tuple[dict, list[dict], str, str]:
    try:
        parser = ResolvingParser(spec_string=raw_content, backend="openapi-spec-validator", strict=True)
        spec = parser.specification

        validate(spec)

        paths = spec.get("paths", {})
        endpoints = []
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
                    endpoints.append(
                        {
                            "method": method.upper(),
                            "path": path,
                            "operation": details,
                        }
                    )

        version = spec.get("openapi", "3.0.0")
        servers = spec.get("servers", [{"url": "/"}])
        base_url = servers[0].get("url", "/") if servers else "/"

        return spec, endpoints, version, base_url

    except Exception as e:
        logger.error("OpenAPI parse error", error=str(e))
        raise
