# API3:2023 — Broken Object Property Level Authorization (BOPLA)

## What It Is
An API either returns more object properties than the user should see (excessive data exposure)
or allows the user to write properties they should not control (mass assignment).

## How to Probe — Excessive Data Exposure
- Inspect responses for fields like: password_hash, internal_id, admin_notes, credit_card, ssn, secret.
- Compare the response schema against the documented API — extra fields are a red flag.

## How to Probe — Mass Assignment
- Include extra fields in PUT/PATCH/POST bodies: role, is_admin, balance, subscription_tier.
- Verify whether the change persists in a subsequent GET — if it does, mass assignment is confirmed.
- Try setting role=admin, is_active=true, credit=9999 in update requests.

## Vulnerable vs Safe Response
- **Vulnerable**: PATCH /users/{id} with body {"role": "admin"} → GET user returns role=admin.
- **Vulnerable**: GET /users/{id} returns password_hash in the JSON body.
- **Safe**: Server ignores unauthorized fields in input; strips sensitive fields from output.

## Severity: High

