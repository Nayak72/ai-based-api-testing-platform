# API5:2023 — Broken Function Level Authorization (BFLA)

## What It Is
The API does not verify whether the authenticated user has permission to invoke a particular function
or endpoint. Regular users can call admin-only or privileged operations.

## How to Probe
1. Discover admin/internal endpoints: try /admin/, /internal/, /management/, /superuser/, /ops/.
2. Call admin endpoints with a regular user token — expect 403.
3. Try HTTP method switching: a path may allow GET for all but only admins should POST/DELETE.
4. Look for role hints in the API response (e.g., "role": "user") and try escalating via BOPLA.

## Vulnerable vs Safe Response
- **Vulnerable**: POST /admin/reset with a regular user token returns 200.
- **Safe**: 403 Forbidden for any non-admin call to admin-scoped endpoints.

## Severity: High to Critical

