# API8:2023 — Security Misconfiguration

## What It Is
Insecure defaults, verbose error messages, missing security headers, open CORS, or exposed
management/debug endpoints that reveal implementation details or allow unintended access.

## How to Probe
1. Trigger a 500 error (send malformed input) and inspect the response for stack traces, framework info.
2. Check HTTP response headers for: CORS (Access-Control-Allow-Origin: *), X-Powered-By, Server.
3. Look for exposed endpoints: /swagger-ui, /docs, /redoc, /actuator, /metrics, /health (with details).
4. Try uncommon HTTP methods: TRACE, OPTIONS — TRACE should be disabled; OPTIONS should only show
   allowed methods.
5. Send extra unexpected headers or a body larger than expected and inspect error messages.

## Vulnerable vs Safe Response
- **Vulnerable**: 500 response body includes "Traceback", "at line", SQL error, file path, version strings.
- **Vulnerable**: Access-Control-Allow-Origin: * on authenticated endpoints.
- **Safe**: Generic error messages ("An error occurred"); minimal response headers; debug endpoints
  require auth or are disabled in production.

## Severity: Medium to High

