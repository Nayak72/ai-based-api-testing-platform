# API1:2023 — Broken Object Level Authorization (BOLA)

## What It Is
BOLA (also called IDOR — Insecure Direct Object Reference) occurs when an API does not verify that
the requesting user is authorized to access a specific resource identified by an object ID.
An attacker substitutes their own ID with another user's ID in the URL or body and receives data they
should not see.

## How to Probe via Black-Box HTTP
1. Authenticate as User A and retrieve User A's resource IDs (user ID, order ID, record ID).
2. Authenticate as User B (or use User A's token) and request User A's resources using those IDs.
3. Try incrementing or decrementing numeric IDs by 1 (sequential IDs are especially vulnerable).
4. Try UUIDs of other users if you can observe them in responses.
5. Test nested paths: GET /users/{A's id}/orders should refuse User B's token.

## Vulnerable vs Safe Response Signals
- **Vulnerable**: 200 OK with another user's personal data in the body.
- **Vulnerable**: 200 with a body that contains fields belonging to User A when authenticated as User B.
- **Safe**: 403 Forbidden or 404 Not Found when accessing another user's resource.

## Assertion Ideas for Test Cases
- Expected status_code: 403 or 404 (not 200) when using a second user's token for the first user's object.
- Body must NOT contain the target user's email, name, or secret fields.
- If 200 is returned, assert that user_id in body matches the authenticated user's id.

## Severity: High to Critical
Leads to mass data exposure, privacy violations, and regulatory fines.

