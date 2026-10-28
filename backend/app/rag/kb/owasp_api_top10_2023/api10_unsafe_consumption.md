# API10:2023 — Unsafe Consumption of APIs

## What It Is
The application blindly trusts data received from third-party APIs and passes it to databases,
renderers, or other downstream systems without sanitization. An attacker who controls or can
influence the third-party can inject malicious payloads.

## How to Probe
1. Identify fields in the response that appear to come from third-party sources and are rendered
   or stored (e.g., user bio from a social login, address from a geocoder).
2. Inject SQL, XSS, or command injection payloads via API inputs that flow through external services.
3. Check if the application validates content-type and response schema from third-party calls.
4. Supply a third-party callback URL you control and monitor what the server sends you.

## Vulnerable vs Safe Response
- **Vulnerable**: Third-party-supplied field rendered directly in HTML (stored XSS); or used in a SQL
  query without parameterization.
- **Safe**: All third-party data is sanitized and validated before downstream use; output encoding
  applied before rendering.

## Severity: High

