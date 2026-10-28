# API2:2023 — Broken Authentication

## What It Is
Authentication mechanisms are missing, weak, or bypassable. Attackers can impersonate legitimate users
by exploiting weak tokens, missing expiry, no rate limiting on login, or accepting unsigned/tampered JWTs.

## How to Probe
1. Send requests to protected endpoints with no Authorization header — expect 401.
2. Send a malformed or truncated JWT — expect 401.
3. Try using a JWT after logout — expect 401 (token should be revoked).
4. Try `alg: none` JWT attack — modify header to algorithm=none, strip signature.
5. Repeatedly attempt login with wrong passwords — expect 429 or lockout after N failures.
6. Try the same token from a different IP or User-Agent — some APIs should reject this.

## Vulnerable vs Safe Response
- **Vulnerable**: Protected endpoint returns 200 with no auth header; accepts expired/tampered tokens;
  no lockout on login brute force.
- **Safe**: 401 for all unauthenticated requests; rate-limits login; invalidates tokens on logout.

## Severity: Critical

