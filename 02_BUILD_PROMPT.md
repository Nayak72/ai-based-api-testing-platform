# BUILD PROMPT — Upgrade "AI-Powered API Testing Platform" with RAG, Agents, Local + Cloud LLMs, and Local/Online Testing Modes

> Paste everything below into your coding agent (Claude Code / Cursor / Antigravity) at the repo root. Work phase by phase; after each phase run the listed checks and stop for review before the next one.

---

## 0. Role and rules

You are a senior full-stack engineer extending an existing repository. Work incrementally, keep the app runnable after every phase, and never rewrite what already works.

**Existing stack (keep):** FastAPI (async) · MongoDB via Motor · Pydantic v2 · httpx · prance/openapi-spec-validator · Jinja2 + WeasyPrint · JWT auth · React 18 + TypeScript + Vite + Tailwind v3 + TanStack Query + Phosphor icons.

**New dependencies allowed:** `langgraph`, `chromadb`, `json-repair`, `cryptography` (Fernet), `sse-starlette`, `sentence-transformers` (optional, only if not using Ollama embeddings), `rank-bm25` (optional). Declare every dependency in `backend/pyproject.toml` (also declare `pyyaml`, which is already imported).

**Frontend rule:** follow `.agents/AGENTS.md` and the `raashi-brand` skill for all UI work. Status states (pass/fail/error/skipped) must not rely on colour alone — use icon + text, and use only brand-permitted colours.

**Engineering rules**
- Type hints everywhere; `ruff` and `pyright` clean; `tsc` clean.
- No secrets in logs, API responses, or `localStorage`.
- Every new module gets unit tests; network and LLM calls are mocked in tests.
- Keep existing API routes backward compatible; add new routes under `/api/v1/`.
- Prefer small files; no copy-paste (the four generators currently duplicate `parse_response`).

---

## 1. Context: what exists (do not re-discover)

```
backend/app/
  ai/            orchestrator.py (primary→fallback), providers/{base,nim,openrouter}.py
  parsers/       openapi.py, postman.py
  generators/    base.py, functional.py (4 generator classes), orchestrator.py, prompts/*.j2
  executor/      engine.py (TestExecutor), runner.py (RunOrchestrator), assertions.py
  analyzer/      engine.py (ResultAnalyzer)
  reports/       generator.py (+ styles/report.css; templates/ is MISSING)
  db/            models.py, mongo.py, repositories/*
  api/routes/    auth, specs, test_cases, runs, reports
frontend/src/    pages/{Dashboard,SpecsList,SpecUpload,SpecDetail,TestCases,RunHistory,RunDetail,ReportsList,ReportView,Settings}.tsx
```

Current flow: upload spec → parse → generate (1 LLM call per endpoint×category, strict JSON, cached) → run (asyncio.gather + httpx + assertions) → analyze (1 LLM call per result) → HTML/PDF report.

---

## 2. Phase 0 — Fix existing defects (mandatory first)

1. **Reports:** create `backend/app/reports/templates/report.html` (summary cards, per-category tables, failed-test details with request/response, AI findings, disclaimer). Make the template dir resolve via `Path(__file__)`. Handle the empty-PDF case (`WeasyPrint` unavailable) with a clear API message, not a silent `""` path.
2. **Prompt loader:** in `generators/base.py` replace `FileSystemLoader("backend/app/generators/prompts")` with a path relative to `__file__`.
3. **Cache bug:** pass `ObjectId` (not `str`) into `generate_for_endpoint`; add a test proving a second generation call hits the cache.
4. **Analyzer:** accept `provider/model/api_key` like the generator does; fix the `ProviderError(...)` call (missing `provider`).
5. **Live results:** in `runner.py` persist each result immediately after it completes (`result_repository.create`), increment summary counters atomically per result, set `started_at/completed_at/duration_seconds`, wire `rate_limit_rps` from settings/run config, fix `final_status` logic (`completed` / `completed_with_errors` / `cancelled`).
6. **Raw body support:** `RequestTemplate` gains `raw_body: str | None` and `content_type: str | None`. Executor uses `content=raw_body` when set (needed for malformed-JSON and wrong-content-type tests) and `json=` otherwise. Send falsy bodies (`0`, `false`, `{}`) correctly (`is not None`).
7. **`response_time` assertion:** implement (`lt`/`lte` against `duration_ms`); pass `duration_ms` into `evaluate_assertions`.
8. **Dedupe:** extract one `extract_endpoints(spec) -> list[Endpoint]` into `parsers/common.py` with stable `endpoint_id`; use it in parser, generator orchestrator and `specs` route. Collapse the 4 generators' `parse_response` into `BaseGenerator`.
9. **Postman base URL:** resolve `{{baseUrl}}` from collection variables when present; otherwise require `base_url_override` at run creation (validation error, not silent failure).
10. **Secrets:** remove API keys from `localStorage` and from the user document in plaintext (see Phase 2 `secrets.py`); `GET /auth/me` must never return keys.
11. **Docs:** fix absolute paths in `.agents/AGENTS.md` to relative ones.

**Done when:** `pytest` passes; with uvicorn started from `backend/`, generate → run → report works end to end against a mocked LLM.

---

## 3. Phase 1 — Target safety + the two testing modes

### 3.1 `app/safety/target_guard.py`
```python
class TargetPolicy(StrEnum): LOCAL = "local"; ONLINE = "online"

class TargetGuard:
    def check(self, url: str, policy: TargetPolicy, allowlist: set[str] = frozenset()) -> GuardDecision
```
- Parse URL; only `http`/`https`; reject credentials in URL; reject non-standard schemes.
- **Resolve DNS** and classify every returned IP: loopback, private (RFC1918, ULA), link-local (incl. `169.254.169.254`), multicast, unspecified, public.
- `LOCAL`: allow loopback + private + `host.docker.internal`; reject public hosts (prevents using Local mode as a loophole).
- `ONLINE`: allow public IPs only; reject everything else.
- Re-validate on **every redirect hop** (set `follow_redirects=False` in httpx and follow manually through the guard, max 3 hops). Re-resolve at connect time to defeat DNS rebinding (pin the resolved IP).
- Return `GuardDecision(allowed, reason, classification)`.
- Wire into `TestExecutor` so **no request leaves without a guard check**; a blocked request becomes a result with `status="blocked"` and the reason.

### 3.2 Mode model
Add to `RunConfig`:
```python
mode: Literal["local", "online"] = "local"
intensity: Literal["safe", "standard", "aggressive"] = "standard"
max_total_requests: int = 500
owned_host_attestation: bool = False   # online only
```
Effective limits (server-enforced, UI cannot exceed):

| | local | online |
|---|---|---|
| max concurrency | 20 | 3 |
| rate limit | none | 2 req/s |
| categories allowed | all | functional, edge, malformed; `security` only if host is in `owned_allowlist` AND attestation is true; `resource_consumption` never |
| redirects | guarded | guarded |
| `429` handling | retry once | honour `Retry-After`, then stop the run if repeated |

Add `blocked` to result statuses, summaries, report, and UI.

### 3.3 Target catalog (online mode)
`backend/app/modes/catalog.json` — array of `{id, name, base_url, spec_path_or_inline, auth: none|api_key, notes, safe_methods_only: bool, rate_limit_rps}`. Ship bundled OpenAPI files under `backend/app/modes/specs/` for each entry (do not rely on remote spec fetching). Initial entries: **JSONPlaceholder, httpbin, DummyJSON, Restful-Booker, Swagger Petstore v3, PokeAPI** (read-only), plus a comment in the file telling the user to verify each service is still online and check its terms. Some sites change terms or require keys — the catalog must support `auth: api_key` with the key typed in the UI.
Endpoints: `GET /api/v1/catalog`, `POST /api/v1/catalog/{id}/import` (creates a spec for the user).

### 3.4 Spec ingestion additions
- `POST /api/v1/specs/from-url` `{url, name, mode}` — fetch an OpenAPI doc (e.g. `http://localhost:8000/openapi.json`) through `TargetGuard`, size cap 5 MB, 10 s timeout, content-type sniffing for JSON/YAML.
- `POST /api/v1/quick-test` `{mode, method, url, headers, query, body, auth}` — single-request tester: guard → send → return response + (if AI enabled) a short Triage-agent explanation. Powers the "Quick Test" page.

### 3.5 VulnShop demo target
Create `demo_targets/vulnshop/` — standalone FastAPI app (own `requirements.txt`, port 9000, in-memory data, `openapi.json` auto-served) with **intentional, documented, harmless** flaws, each listed in `demo_targets/vulnshop/GROUND_TRUTH.json` as `{id, endpoint, owasp, description}`:
`GET /users/{id}` (BOLA: any token reads any user) · `POST /admin/reset` (BFLA: normal user can call) · `PATCH /users/{id}` accepts `role` (mass assignment/BOPLA) · `GET /products` (no pagination cap) · `GET /debug` (verbose stack trace / misconfiguration) · `POST /fetch?url=` (SSRF-style, **simulated: validates the URL but never performs a request**) · `POST /login` (no rate limit, weak token) · `GET /public/health` (control endpoint with no flaw). Include 2 users (`alice`, `bob`) with tokens set via env so BOLA is testable.
Add a `README` stating it must only run on localhost.

**Done when:** guard unit tests cover loopback/private/metadata/redirect/rebinding cases; online mode refuses `127.0.0.1` and local mode refuses a public host; VulnShop runs and its OpenAPI imports.

---

## 4. Phase 2 — Provider layer: third-party + local LLM

### 4.1 `app/ai/providers/openai_compat.py`
One class `OpenAICompatProvider(name, base_url, api_key|None, default_model, capabilities)`; reuse the retry/error taxonomy from `base.py`. `nim.py` and `openrouter.py` become thin presets (keep the OpenRouter `HTTP-Referer`/`X-Title` headers as optional extra headers).

Presets (all via `/chat/completions`):
| Preset | Base URL default | Key |
|---|---|---|
| `openrouter` | `https://openrouter.ai/api/v1` | yes |
| `nim` | `https://integrate.api.nvidia.com/v1` | yes |
| `openai_compatible` | user-entered (OpenAI, Groq, Together, Gemini-compat …) | yes |
| `ollama` | `http://localhost:11434/v1` | no |
| `lmstudio` | `http://localhost:1234/v1` | no |
| `llamacpp` | `http://localhost:8080/v1` | no |

`ModelCapabilities`: `json_mode`, `json_schema`, `tools`, `context_window`, `is_local`. Defaults per preset, overridable per provider profile. Local models get conservative defaults (`json_mode=True`, `tools=False`, `context_window=8192`).

Local-specific: request timeout 180 s default; `num_ctx` passed through Ollama's `options` when supported; sequential (concurrency 1–2) calls for local providers; health check hits `/models` (Ollama also `GET /api/tags` to list installed models).

### 4.2 Provider profiles + secrets
- `app/safety/secrets.py`: Fernet encrypt/decrypt with key from `SECRETS_ENCRYPTION_KEY` env (fail startup in non-debug if missing; generate-and-print helper command in README).
- New collection `provider_profiles`: `{user_id, name, preset, base_url, model, embedding_model, api_key_encrypted, capabilities, is_default}`.
- Routes: `GET/POST/PATCH/DELETE /api/v1/providers`, `POST /api/v1/providers/{id}/test` (sends a tiny prompt, returns latency + whether JSON mode works), `GET /api/v1/providers/ollama/models?base_url=` (lists local models), `GET /api/v1/providers/presets`.
- API keys are write-only: responses return `has_key: true`, never the key.

### 4.3 Router with policies
Replace `AIOrchestrator` internals with `LLMRouter`:
```python
class RoutingPolicy(StrEnum):
    LOCAL_ONLY; CLOUD_ONLY; LOCAL_FIRST; CLOUD_FIRST; PER_AGENT
```
`RoutingConfig{policy, local_profile_id, cloud_profile_id, per_agent: dict[agent_name, profile_id]}`.
- `local_only` must make **zero** external network calls (assert in a test by blocking non-loopback sockets).
- `local_first`: fall back to cloud when JSON validation still fails after the repair loop or the local server is down.
- Keep backward compatibility: existing `create_orchestrator()` call sites keep working.

### 4.4 Structured-output helper (critical for small local models)
`app/ai/structured.py`:
```python
async def generate_structured(router, agent, prompt, system, model_cls: type[BaseModel], max_repairs=2) -> BaseModel
```
Strategy: JSON schema/JSON mode if the capability says so → `json_repair.loads` → Pydantic validation → on failure re-prompt with the exact validation error and the previous output (max 2) → raise `StructuredOutputError`. Record `repairs_used` in the event stream.

**Done when:** a provider profile for Ollama and one for OpenRouter can be created and tested from the API; a mocked small-model response with broken JSON is repaired; `local_only` test passes.

---

## 5. Phase 3 — RAG

### 5.1 Modules (`backend/app/rag/`)
- `embeddings.py` — `Embedder` interface; `OpenAICompatEmbedder` (`/embeddings`; Ollama `nomic-embed-text`, or cloud) and `SentenceTransformerEmbedder` (`all-MiniLM-L6-v2`, lazy-loaded). Chosen per provider profile (`embedding_model`).
- `store.py` — `VectorStore` interface (`upsert`, `query`, `delete_by_filter`, `count`); `ChromaStore` using `chromadb.PersistentClient(path=settings.vector_dir)`. Collection name includes embedding model id so a model change forces re-index (detect and surface "re-index required").
- `chunker.py` — spec → chunks: **one chunk per endpoint** (method, path, summary, parameters, request body schema, response schemas, security) and **one per component schema**; metadata `{spec_id, endpoint_id, kind, tags}`. Cap chunk size ≈ 1,200 tokens; split large schemas by property group.
- `retriever.py` — `retrieve(query, collections, filters, k=6)`; optional BM25 hybrid (reciprocal rank fusion) behind a setting; returns `RetrievedChunk{id, collection, text, score, metadata}`.
- `kb/` — Markdown files **you write in your own words**, short and practical:
  - `owasp_api_top10_2023/api1_bola.md … api10_unsafe_consumption.md` — risk summary, how to probe via black-box HTTP, vulnerable vs safe response signals, assertion ideas, severity guidance.
  - `http_kb/status_codes.md`, `rest_conventions.md`, `assertion_patterns.md`.
- `ingest_kb.py` — CLI `python -m app.rag.ingest_kb` (idempotent; hash-based skip).
- `run_memory.py` — after each run, embed short summaries of confirmed bugs and marked false positives (`spec_id`, endpoint, category, outcome) into `run_memory`.

### 5.2 API
`POST /api/v1/kb/reindex`, `GET /api/v1/kb/status` (collections, counts, embedding model, stale flag), `POST /api/v1/kb/documents` (upload `.md/.txt/.pdf` into `user_docs`, per spec), `GET /api/v1/kb/search?q=&spec_id=` (debug/search UI).

### 5.3 Rules
- Every retrieval result used in a generation or finding must be stored as `rag_sources: list[{chunk_id, collection, score}]` on the test case / analysis.
- Retrieval must degrade gracefully: if the vector store or embedder is unavailable, log a warning, set `rag_used=false` in the event, and continue with the non-RAG prompt.

**Done when:** KB ingests offline with the local embedder; `kb/search` returns relevant OWASP chunks for "object id belongs to another user"; unit tests cover chunking and retrieval filters.

---

## 6. Phase 4 — Agents (LangGraph)

### 6.1 State and events
`app/agents/state.py` — `SessionState(TypedDict)`: `session_id, user_id, spec_id, mode, routing, categories, plan, test_cases, critic_report, run_id, results, triage, report_id, errors, interrupts`.
`app/agents/events.py` — `AgentEvent{session_id, ts, agent, step, status: started|progress|completed|failed|waiting_human, message, data, tokens, latency_ms, provider, model, rag_used, rag_sources}`; persisted in `agent_events`; published to an in-process `asyncio` pub/sub for SSE.

### 6.2 Base agent
`app/agents/base.py` — `BaseAgent(name)` with `run(state) -> state`, `llm(...)` wrapper over `generate_structured`, automatic event emission (started/completed/failed with token and latency totals), per-agent routing profile lookup, cancellation check.

### 6.3 Agents (each in its own file; each has a Pydantic output model)
1. **IngestAgent** — parse via existing parsers; `extract_endpoints`; build **dependency graph** (producer→consumer edges by matching response fields like `id` to path params `{id}`, `{userId}`); chunk + embed into `spec_chunks`. Deterministic first; LLM only to summarise undocumented endpoints (optional).
2. **PlannerAgent** — for each endpoint, RAG over `spec_chunks` + `owasp_kb` + `run_memory`; output `Plan{endpoints:[{endpoint_id, categories, priority, needs_auth, depends_on, setup_steps, notes}]}`. Respect mode limits (online: drop security/resource tests unless allowed). **Interrupt for human approval** (`waiting_human`), accepting edits to the plan.
3. **GeneratorAgents** — keep the 4 categories and existing prompt templates, extended with a `{{ context }}` block containing retrieved chunks. Output validated against the existing `TestCase` schema (+ `rag_sources`, `depends_on`, `extract: [{name, jsonpath}]` for chaining). Honour plan priorities and `max_tests_per_endpoint`. Run endpoints concurrently for cloud providers, sequentially for local ones.
4. **CriticAgent** — deterministic checks first, LLM only for ambiguous cases: (a) request conforms to the spec (path exists, required params present unless the test is intentionally negative, types), (b) expected status plausible for the category, (c) duplicates by `request_hash`, (d) safety (`TargetGuard` classification of any absolute URL in body/params, no destructive methods against catalog hosts marked `safe_methods_only`), (e) assertions executable. Failed cases go back to the generator with the reasons (max 2 repair loops, then dropped and reported).
5. **ExecutorAgent** — wraps the existing executor: topological order from `depends_on`; **variable store** (`{{user_id}}` filled from earlier responses via `extract`); per-test live event + immediate persistence; two identities (`auth` + `auth_secondary`) so BOLA/BFLA tests send the second user's token against the first user's objects; if auth is required but missing → `waiting_human` interrupt asking for a token; obeys mode limits and `max_total_requests`.
6. **TriageAgent** — process results in **batches** (cloud: 10–20, local: 3–5); input = request/response (bodies truncated, secrets masked), the test intent, retrieved OWASP/http chunks, run memory. Output per result: `verdict ∈ {real_bug, test_bug, spec_drift, flaky, environment, ok}`, `risk_level`, `owasp_category`, `evidence`, `recommendation`, `false_positive_likelihood`, `rag_sources`. For `real_bug` with `risk ≥ high` and low confidence, request **one confirmation re-run** through the executor before finalising.
7. **ReporterAgent** — executive summary, risk matrix, findings grouped by OWASP category with citations (`rag_sources` titles), remediation list, methodology/model/provider table (reproducibility), disclaimer. Renders via the fixed Jinja template (HTML/PDF) plus a JSON export.
8. **AssistantAgent (stretch)** — `POST /api/v1/sessions/{id}/chat`; RAG over `spec_chunks` + results; answers questions like "why did the BOLA test on /users/{id} fail?".

### 6.4 Graph
`app/agents/graph.py`:
```
ingest → planner → [interrupt: approve_plan] → generate → critic ─┬─ (invalid & loops<2) → generate
                                                                   └─ ok → [interrupt: auth_if_needed] → execute → triage ─┬─ (needs_confirmation) → execute(confirm) → triage
                                                                                                                              └─ report → END
```
- Mongo checkpointer (collection `agent_checkpoints`) so a session resumes after restart.
- **Feature flag** `AGENTIC_MODE` (setting + per-session toggle). When off, the legacy linear pipeline is used unchanged → enables baseline-vs-agentic comparison in the evaluation.

### 6.5 Session API
- `POST /api/v1/sessions` `{spec_id, mode, categories, intensity, routing, agentic: bool, base_url, auth, auth_secondary, owned_host_attestation}` → `{session_id}`
- `GET /api/v1/sessions`, `GET /api/v1/sessions/{id}` (state summary)
- `GET /api/v1/sessions/{id}/events` — **SSE** stream (replay from `Last-Event-ID`)
- `POST /api/v1/sessions/{id}/approve-plan` `{plan_edits?}` · `POST /api/v1/sessions/{id}/provide-auth` · `POST /api/v1/sessions/{id}/cancel`
- Secrets in `auth`/`auth_secondary` are encrypted at rest, masked in all responses and events, and deleted when the session ends (unless the user saves them in a provider/target profile).

**Done when:** with a mocked router the full graph completes; resume-after-restart test passes; `critic` repair loop test passes; events stream over SSE.

---

## 7. Phase 5 — Frontend

New/changed pages (keep existing ones working):

1. **New Test Session wizard** (`pages/NewSession.tsx`) — steps:
   1. **Mode:** Local API / Online free API (explain the safety differences inline).
   2. **Source:** *Local:* upload OpenAPI/Postman · import from URL (`http://localhost:PORT/openapi.json`) · pick **VulnShop demo**. *Online:* pick from catalog · import URL · upload. Plus **Quick Test** link (single request).
   3. **Target & auth:** base URL (prefilled), auth type (none / bearer / API key header+name / basic), **token input field (masked, never stored in localStorage)**, optional second identity token (explains it enables BOLA/BFLA checks), online: ownership attestation checkbox (only shown for non-catalog hosts).
   4. **AI:** choose Cloud profile and/or Local profile, routing policy (local-only / cloud-only / local-first / cloud-first / per-agent), embedding model, "Test connection" buttons, agentic toggle.
   5. **Scope:** categories, intensity, max tests per endpoint, max total requests, endpoint tree with checkboxes.
   6. **Review & Start.**
2. **Session page** (`pages/SessionDetail.tsx`) — left: stepper of agents (Ingest → Plan → Generate → Critic → Execute → Triage → Report) with status; centre: **Agent Trace** (live SSE feed; expandable cards showing prompt summary, retrieved chunks with scores, tokens, latency, provider/model, repairs used); right: live counters (tests generated/valid, requests sent, pass/fail/blocked, tokens, cost estimate). Modals for **Approve Plan** (editable table) and **Auth needed**.
3. **Providers settings** (replace the AI section of `Settings.tsx`) — profiles list, preset picker, base URL, model (with **"Fetch models"** for Ollama), embedding model, capability toggles, test button, key field write-only (shows "Key saved").
4. **Knowledge Base page** — collection counts, embedding model, re-index button, search box showing retrieved chunks, upload docs per spec.
5. **Results view upgrades** — verdict badges (real bug / test bug / spec drift / flaky), OWASP chip, "Why?" drawer listing `rag_sources`, request/response diff, re-run button, "mark false positive" (feeds `run_memory`).
6. **Compare page** (`pages/Compare.tsx`) — pick 2+ sessions → table of metrics (valid-test rate, bugs found, tokens, latency, local vs cloud, agentic vs baseline) and a bar chart.
7. **Quick Test page** — method, URL, headers, body, auth, mode → response viewer + optional AI explanation.

Replace 2 s polling in run/session views with SSE where available (keep polling as a fallback).

**Done when:** `npm run build` is clean; every wizard step validates and the whole flow works against VulnShop with mocked backend responses.

---

## 8. Phase 6 — Evaluation harness (for the COE report)

`backend/eval/`:
- `run_eval.py --target vulnshop --configs configs/*.yaml --repeats 3` — for each config creates a session through the service layer (no UI), waits, scores results against `GROUND_TRUTH.json`, writes `eval/results/<timestamp>.json` and a Markdown summary.
- Configs: `baseline_cloud`, `baseline_local`, `rag_cloud`, `rag_local`, `agentic_cloud`, `agentic_local`, `agentic_hybrid`.
- Metrics: valid-JSON rate (before repair), valid-test rate (after Critic), **vulnerability recall** (seeded flaws detected), **precision** (findings that map to a seeded flaw or a manually confirmed issue), false-positive rate, total tokens, wall-clock time, requests sent.
- Output a ready-to-paste table and a chart image (`matplotlib`, optional dependency group `eval`).
- Document that LLM output is non-deterministic: report mean ± std over repeats.

---

## 9. Phase 7 — Tests, docs, packaging

- Backend tests for: target guard, structured-output repair, router policies (incl. `local_only` no-egress), chunker/retriever, each agent with a fake router, graph resume, critic loop, executor chaining + two identities, raw-body sending, mode limits, secrets encryption, SSE.
- Frontend: component tests for wizard validation and trace rendering (Vitest + Testing Library) — add only if setup stays small.
- `docker-compose.yml`: `mongo`, `backend`, `frontend`, `vulnshop`; optional `ollama` service (profile `local-llm`) with a documented GPU note.
- Update `README.md` (modes, providers, RAG, agents, safety model, eval) and add `docs/ARCHITECTURE.md` with the diagrams from the analysis document.
- Add `.env.example` entries: `SECRETS_ENCRYPTION_KEY`, `VECTOR_DIR`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `AGENTIC_MODE`, `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, `OWNED_HOST_ALLOWLIST`, `ONLINE_MAX_RPS`, `ONLINE_MAX_CONCURRENCY`.

---

## 10. Data model additions (summary)

- `RequestTemplate`: `raw_body`, `content_type`.
- `TestCaseMetadata`: `rag_sources`, `depends_on`, `extract`, `agent`, `repairs_used`.
- `RunConfig`: `mode`, `intensity`, `max_total_requests`, `owned_host_attestation`, `routing`.
- Result status: add `blocked`. `LLMAnalysis`: add `verdict`, `owasp_category`, `rag_sources`.
- New collections: `sessions`, `agent_events`, `agent_checkpoints`, `provider_profiles`, `kb_documents`, `run_memory` (metadata) — plus Chroma directory on disk.
- Indexes: `agent_events(session_id, ts)`, `sessions(user_id, created_at)`, `provider_profiles(user_id)`.

---

## 11. Acceptance criteria (definition of done)

1. Fresh clone → follow `RUN_GUIDE.md` → platform runs; **Local mode** test of VulnShop completes and the report lists BOLA, BFLA, mass assignment, debug exposure and unbounded listing findings.
2. **Online mode** test of a catalog API (e.g. JSONPlaceholder) completes within the limits; attempts to target `127.0.0.1` or a private IP in online mode are blocked; security payload categories are off for catalog hosts.
3. Same session runs with (a) a cloud profile, (b) a local Ollama profile, (c) `local_first` with fallback — and `local_only` makes no external calls.
4. Agent Trace shows each agent's retrieved chunks, tokens, latency, provider/model live.
5. Plan approval and auth-needed interrupts work and resume correctly, including after a backend restart.
6. Reports (HTML + PDF + JSON) generate; no API key appears in any response, log, event, or report.
7. `pytest`, `ruff`, `pyright`, `npm run build` all pass; eval harness produces a results table.

## 12. Do NOT

- Do not run attack payloads against any host that is not local or explicitly owned.
- Do not log or return raw API keys/tokens; do not put them in `localStorage`.
- Do not paste copyrighted text into the knowledge base — write original summaries.
- Do not remove the legacy linear pipeline until the evaluation harness has run baseline vs agentic.
- Do not skip Phase 0.
