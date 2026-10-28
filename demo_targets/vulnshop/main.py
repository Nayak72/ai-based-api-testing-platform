"""
VulnShop — Intentionally Vulnerable Demo API

⚠️  This application contains DELIBERATE security flaws for research/demo purposes.
    It MUST only run on localhost and MUST NEVER be exposed to the internet.

Documented flaws (see GROUND_TRUTH.json):
  - BOLA: GET /users/{user_id} — no ownership check
  - BFLA: POST /admin/reset — no role check
  - BOPLA: PATCH /users/{user_id} — accepts privileged 'role' field
  - Resource consumption: GET /products — no pagination cap
  - Misconfiguration: GET /debug — verbose internal info
  - SSRF (simulated): POST /fetch — accepts arbitrary URL (never fetches)
  - No rate limit on login: POST /login
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

# ── In-memory data store ──────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS: dict[int, dict] = {
    1: {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com",
        "role": "user",
        "password_hash": pwd_context.hash("alice_password"),
        "secret": "alice-secret-data-42",
    },
    2: {
        "id": 2,
        "username": "bob",
        "email": "bob@example.com",
        "role": "user",
        "password_hash": pwd_context.hash("bob_password"),
        "secret": "bob-private-note-99",
    },
    3: {
        "id": 3,
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "password_hash": pwd_context.hash("admin_password"),
        "secret": "admin-master-key",
    },
}

PRODUCTS: list[dict] = [
    {"id": i, "name": f"Product {i}", "price": round(9.99 + i * 0.5, 2), "stock": 100 - i}
    for i in range(1, 201)
]

# Tokens: env-configurable for test automation
ALICE_TOKEN = os.environ.get("ALICE_TOKEN", "alice-demo-token-insecure")
BOB_TOKEN = os.environ.get("BOB_TOKEN", "bob-demo-token-insecure")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admin-demo-token-insecure")

TOKEN_TO_USER_ID: dict[str, int] = {
    ALICE_TOKEN: 1,
    BOB_TOKEN: 2,
    ADMIN_TOKEN: 3,
}

# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="VulnShop",
    description="Intentionally vulnerable demo API for security testing research. Run on localhost only.",
    version="1.0.0",
)

security = HTTPBearer(auto_error=False)


def _get_current_user_id(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int | None:
    if not credentials:
        return None
    return TOKEN_TO_USER_ID.get(credentials.credentials)


def _require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> int:
    user_id = TOKEN_TO_USER_ID.get(credentials.credentials if credentials else "")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return user_id


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/login", tags=["auth"], summary="Login (FLAW: no rate limit)")
async def login(body: dict):
    """
    FLAW (API4 + API2): No rate-limit, no brute-force protection.
    Returns a simple static token for demo — not a real JWT.
    """
    username = body.get("username", "")
    password = body.get("password", "")
    user = next((u for u in USERS.values() if u["username"] == username), None)
    if not user or not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token_map = {1: ALICE_TOKEN, 2: BOB_TOKEN, 3: ADMIN_TOKEN}
    return {"access_token": token_map[user["id"]], "token_type": "bearer", "user_id": user["id"]}


# ── Users ─────────────────────────────────────────────────────────────────────

@app.get("/users/{user_id}", tags=["users"], summary="Get user (FLAW: BOLA)")
async def get_user(user_id: int, auth_user_id: int = Depends(_require_auth)):
    """
    FLAW (API1 — BOLA): Any authenticated user can read ANY user's data.
    There is NO check that auth_user_id == user_id.
    """
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Returns secret field — a real API should not do this either
    return {k: v for k, v in user.items() if k != "password_hash"}


@app.patch("/users/{user_id}", tags=["users"], summary="Update user (FLAW: BOPLA mass assignment)")
async def update_user(user_id: int, body: dict, auth_user_id: int = Depends(_require_auth)):
    """
    FLAW (API3 — BOPLA): Accepts 'role' field in body — allows privilege escalation.
    A regular user can promote themselves to admin.
    """
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    allowed_fields = {"email", "username"}  # safe
    # BUG: also accepts 'role' because we don't filter it
    for k, v in body.items():
        USERS[user_id][k] = v  # mass assignment — accepts ANY field including 'role'
    return {k: v for k, v in USERS[user_id].items() if k != "password_hash"}


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.post("/admin/reset", tags=["admin"], summary="Admin reset (FLAW: BFLA)")
async def admin_reset(auth_user_id: int = Depends(_require_auth)):
    """
    FLAW (API5 — BFLA): No role check — any authenticated user can call this admin endpoint.
    Should require role=admin but doesn't check.
    """
    return {"status": "reset complete", "timestamp": datetime.now().isoformat()}


# ── Products ──────────────────────────────────────────────────────────────────

@app.get("/products", tags=["products"], summary="List products (FLAW: no pagination cap)")
async def list_products(limit: int = 20, skip: int = 0):
    """
    FLAW (API4 — Unrestricted Resource Consumption): No cap on 'limit'.
    Client can request all 200 products with limit=9999.
    """
    # BUG: no max cap on limit
    return {
        "products": PRODUCTS[skip: skip + limit],
        "total": len(PRODUCTS),
        "limit": limit,
        "skip": skip,
    }


@app.get("/products/{product_id}", tags=["products"], summary="Get product")
async def get_product(product_id: int):
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ── Debug / Misconfiguration ──────────────────────────────────────────────────

@app.get("/debug", tags=["debug"], summary="Debug info (FLAW: misconfiguration)")
async def debug_info(request: Request):
    """
    FLAW (API8 — Security Misconfiguration): Exposes internal environment info,
    simulated stack trace, and request details. Should never be public.
    """
    return {
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": "3.11",
        "database": "in-memory",
        "users_count": len(USERS),
        "products_count": len(PRODUCTS),
        "request_headers": dict(request.headers),
        "simulated_stack_trace": [
            "File /app/main.py, line 42, in handle_request",
            "File /app/db.py, line 19, in query",
            "SQLAlchemy session: SELECT * FROM users",
        ],
        "internal_note": "Remove this endpoint before deploying to production!",
    }


# ── SSRF (simulated, safe) ────────────────────────────────────────────────────

@app.post("/fetch", tags=["ssrf"], summary="Fetch URL (FLAW: SSRF simulated)")
async def fetch_url(body: dict, auth_user_id: int = Depends(_require_auth)):
    """
    FLAW (API7 — SSRF): Accepts an arbitrary URL parameter.
    SAFE IMPLEMENTATION: validates the URL but NEVER actually makes the request.
    This simulates the vulnerability pattern without real SSRF risk.
    """
    url = body.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="'url' is required")

    # Simulated: we detect but do not actually fetch internal URLs
    import urllib.parse
    parsed = urllib.parse.urlparse(url)
    is_internal = parsed.hostname in ("localhost", "127.0.0.1") or (
        parsed.hostname and (parsed.hostname.startswith("192.168.") or parsed.hostname.startswith("10."))
    )

    # Vulnerable response: returns different message for internal vs external
    # (leaks information about internal network reachability)
    if is_internal:
        return {
            "status": "fetched",
            "url": url,
            "response_preview": "[SIMULATED] Internal service responded with 200 OK",
            "note": "In a real vulnerable API, this would leak internal service content.",
        }
    return {
        "status": "fetched",
        "url": url,
        "response_preview": "[SIMULATED] External URL — response not shown for safety",
    }


# ── Health (no flaw) ─────────────────────────────────────────────────────────

@app.get("/public/health", tags=["public"], summary="Health check (no flaw)")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("VulnShop — Intentionally Vulnerable Demo API")
    print("⚠️  FOR LOCAL TESTING ONLY — DO NOT EXPOSE TO INTERNET")
    print("=" * 60)
    print(f"Alice token: {ALICE_TOKEN}")
    print(f"Bob token:   {BOB_TOKEN}")
    print(f"Admin token: {ADMIN_TOKEN}")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=9000)

