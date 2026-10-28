# API4:2023 — Unrestricted Resource Consumption

## What It Is
The API does not limit the size, rate, or number of operations in a request.
This enables DoS via large payloads, unbounded list queries, or rapid request floods.

## How to Probe
1. Send GET with very large limit/page_size (e.g., ?limit=99999) — should be capped server-side.
2. POST a huge body (1 MB, 10 MB) — should be rejected with 413.
3. POST to a compute-heavy endpoint rapidly without pausing — expect 429.
4. Request deeply nested/recursive structures if the API supports it.
5. Check if Retry-After header is provided on 429 responses.

## Vulnerable vs Safe Response
- **Vulnerable**: Returns all records regardless of limit; accepts 10 MB body; never returns 429.
- **Safe**: Server-side cap on result count (e.g., max 100); 413 for oversized body;
  429 with Retry-After on rate limit.

## Severity: Medium to High

