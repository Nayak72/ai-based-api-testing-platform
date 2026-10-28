def extract_endpoints(parsed_spec: dict) -> list[dict]:
    endpoints = []
    paths = parsed_spec.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
                endpoint_id = f"{method.lower()}_{path.replace('/', '_').strip('_')}"
                endpoints.append(
                    {
                        "endpoint_id": endpoint_id,
                        "method": method.upper(),
                        "path": path,
                        "operation": details,
                    }
                )
    return endpoints


def generate_endpoint_id(method: str, path: str) -> str:
    return f"{method.lower()}_{path.replace('/', '_').strip('_')}"
