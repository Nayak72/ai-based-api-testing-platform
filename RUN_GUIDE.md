# Run Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB 7+
- Git

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <repo-url>
cd COE
cp .env.example .env
# Edit .env: set SECRET_KEY (min 32 chars), OPENROUTER_API_KEY (or use local Ollama)
```

### 2. Start MongoDB

```bash
mongod --dbpath ./data/mongo
# Or via Docker:
docker compose up mongo -d
```

### 3. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 5. Start VulnShop (Demo Vulnerable Target)

```bash
cd demo_targets/vulnshop
pip install -r requirements.txt
uvicorn main:app --port 8001
```

---

## Testing VulnShop (Local Mode)

1. Register and log in at `http://localhost:5173`.
2. Go to **New Session** → select **Local** mode.
3. Source: Select **VulnShop** preset (or upload `demo_targets/vulnshop/openapi.json`).
4. Target URL: `http://localhost:8001`.
5. Click **Start Session** — the testing platform executes the pipeline and detects:
   - **BOLA** on `/orders/{order_id}`
   - **BFLA** on `/admin/metrics` and `/admin/users`
   - **Mass Assignment** on `POST /orders` and `/users/{user_id}`
   - **Debug Endpoint Exposure** on `/debug/config` and `/debug/sql-console`
   - **Unbounded Resource Listing** on `/products?limit=1000000`

---

## Using Online Mode

1. Select **Online** mode in **New Session**.
2. Pick a pre-configured public API from the **Catalog** (JSONPlaceholder, httpbin, DummyJSON, PokeAPI).
3. Localhost and private RFC 1918 IPs (`127.0.0.1`, `192.168.x.x`, `10.x.x.x`, `169.254.x.x`) are automatically blocked.
4. Security categories are excluded unless `owned_host_attestation` is explicitly checked.
5. Online mode is strictly rate-limited to 2 RPS and max 3 concurrent requests.

---

## Provider Profiles (Settings)

Navigate to **Settings → AI Providers**:
- **Cloud**: Add your OpenRouter or NVIDIA NIM API key.
- **Local Ollama**: Base URL `http://localhost:11434/v1`, Model `llama3`.
- **Local LM Studio**: Base URL `http://localhost:1234/v1`.

---

## Docker Compose (All Services)

```bash
docker compose up -d
# Or with Ollama:
docker compose --profile ollama up -d
```

---

## Running Backend Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

---

## Eval Harness

```bash
cd backend
source venv/bin/activate
# Update backend/eval/configs/baseline_cloud.yaml with your imported spec_id
python eval/run_eval.py eval/configs/baseline_cloud.yaml
```

