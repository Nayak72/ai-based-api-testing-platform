# Architecture & System Design

## Overview

The platform provides autonomous, AI-guided security and functional testing of REST APIs. It supports both cloud LLMs (OpenRouter, NVIDIA NIM) and local private LLMs (Ollama, LM Studio, llama.cpp), operates in two isolation modes (Local and Online), and supports both linear batch runs and agentic human-in-the-loop workflows.

```mermaid
flowchart TD
    UI["Frontend (React + Vite + Tailwind)"]
    API["FastAPI Backend (/api/v1)"]
    Mongo["MongoDB 7 (State & Reports)"]
    Chroma["ChromaDB (OWASP KB + Spec Chunks)"]
    LLM["LLM Orchestrator (Cloud / Local)"]
    Target["Target REST API"]
    VulnShop["VulnShop (Demo Target)"]

    UI -->|REST & SSE Events| API
    API -->|Persistence| Mongo
    API -->|Vector Retrieval| Chroma
    API -->|Structured Generation| LLM
    API -->|HTTP Tests| Target
    Target -.->|Local Testing| VulnShop
```

---

## Execution Modes & Target Safety

| Feature | LOCAL Mode | ONLINE Mode |
|---|---|---|
| **Loopback (`127.0.0.1`, `localhost`)** | Allowed | **Blocked** |
| **Private RFC1918 (`10.*`, `172.16.*`, `192.168.*`)** | Allowed | **Blocked** |
| **Cloud Metadata (`169.254.169.254`)** | **Blocked** | **Blocked** |
| **Public Internet Hosts** | Blocked | Allowed |
| **Rate Limit** | User-defined / None | Max 2 requests/sec |
| **Max Concurrency** | Configurable (default 10) | Hard capped at 3 |
| **Attestation Required** | No | Yes, for security attacks |

---

## Pipeline Architectures

### 1. Legacy Linear Pipeline (`AGENTIC_MODE=false`)
- **Ingest & Parse**: OpenAPI/Postman parsed, endpoints extracted.
- **Generate**: Batch LLM test generation per category with duplicate suppression.
- **Execute**: Async HTTP execution pool with assertion evaluation.
- **Analyze**: LLM analyzes failure traces to separate real bugs from test bugs.
- **Report**: HTML, PDF, and JSON reports generated.

### 2. Agentic Pipeline (`AGENTIC_MODE=true`)
```mermaid
sequenceDiagram
    participant User
    participant Sessions as Sessions API
    participant Ingest as IngestAgent
    participant Planner as PlannerAgent
    participant Executor as ExecutionEngine
    participant Triage as TriageAgent
    participant Reporter as ReporterAgent

    User->>Sessions: POST /api/v1/sessions
    Sessions->>Ingest: Ingest spec & index RAG chunks
    Ingest->>Planner: Generate category plan
    Planner-->>User: SSE: plan waiting_human
    User->>Sessions: POST /approve-plan
    Sessions->>Executor: Execute generated tests
    Executor-->>User: SSE: live results stream
    Executor->>Triage: Triage failed results with OWASP mapping
    Triage->>Reporter: Generate HTML/PDF reports
    Reporter-->>User: SSE: session_done
```

---

## RAG Knowledge Base

- **OWASP API Security Top 10 (2023)**: Original comprehensive guides (`API1:2023 BOLA` through `API10:2023 Unsafe Consumption`).
- **HTTP Standards KB**: Status codes, REST conventions, assertion patterns.
- **Spec Chunks**: Granular chunks of endpoints, parameters, and component schemas.
- **Run Memory**: Confirmed bugs and confirmed false positives recorded for few-shot prompt refinement.

