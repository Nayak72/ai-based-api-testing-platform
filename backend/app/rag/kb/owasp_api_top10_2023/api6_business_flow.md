# API6:2023 — Unrestricted Access to Sensitive Business Flows

## What It Is
The API exposes business workflows that an attacker can abuse at scale without hitting technical limits:
bulk purchasing, coupon farming, inventory exhaustion, or skipping workflow steps.

## How to Probe
1. Rapidly call checkout/buy/reserve endpoints back-to-back without delays.
2. Try to redeem a coupon or voucher multiple times in quick succession.
3. Skip upstream required steps (e.g., jump to /order/confirm without going through /cart/checkout).
4. Try bulk-enrolling or bulk-purchasing with a single request that references many IDs.

## Vulnerable vs Safe Response
- **Vulnerable**: API allows unlimited rapid purchases; no per-user quotas; no flow sequencing checks.
- **Safe**: Per-user rate limits, CAPTCHA on high-value flows, sequential step enforcement.

## Severity: Medium to High

