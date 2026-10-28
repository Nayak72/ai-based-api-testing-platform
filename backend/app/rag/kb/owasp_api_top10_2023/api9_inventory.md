# API9:2023 — Improper Inventory Management

## What It Is
Outdated, undocumented, or shadow API versions are left active with weaker security controls than
the current version. Attackers can find and exploit these forgotten endpoints.

## How to Probe
1. Try old API version paths: /v1/, /v2/, /v0/, /beta/, /legacy/, /old/, /deprecated/.
2. Check if old versions have the same authentication requirements as the current version.
3. Look for endpoints in JS bundles, error messages, or API docs that are not in the main spec.
4. Try paths with different casing or trailing slashes: /Users vs /users, /users/.

## Vulnerable vs Safe Response
- **Vulnerable**: Old version paths return 200 and accept weaker or no auth.
- **Safe**: Old versions return 410 Gone or redirect to the current version; all paths require the same auth.

## Severity: Medium

