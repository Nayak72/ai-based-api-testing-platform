# API7:2023 — Server-Side Request Forgery (SSRF)

## What It Is
The API accepts a user-controlled URL and uses it to make a server-side HTTP request.
An attacker can point this at internal services (metadata APIs, databases, admin dashboards)
to read data or pivot into the internal network.

## How to Probe
1. Supply internal URLs: http://localhost:8080, http://127.0.0.1:22, http://192.168.1.1.
2. Try cloud metadata endpoints: http://169.254.169.254/latest/meta-data/ (AWS IMDS).
3. Try DNS rebinding: use a domain you control that resolves to 127.0.0.1.
4. Check if the API response differs between an internal URL and a random external URL.
5. Try URL-encoded variants: http://%31%32%37%2E%30%2E%30%2E%31 (127.0.0.1 encoded).

## Vulnerable vs Safe Response
- **Vulnerable**: Returns internal content in the response; returns a different response for 127.0.0.1 vs
  a non-existent host; leaks error messages mentioning internal services.
- **Safe**: Validates URL against an allowlist; rejects private/loopback IPs with 400; returns identical
  generic errors for all blocked URLs.

## Severity: High to Critical

