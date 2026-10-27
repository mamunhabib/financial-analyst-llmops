# Financial & Market Analyst Agent — LLMOps & Guardrails
## Step-by-Step Implementation Plan (Approach 2: Cloud Serverless Data + Local K8s Apps)

> **System Blueprint:** Visualized in detail in [`architecture.html`](architecture.html)  
> **Cluster Namespace:** `financial-agent` (OrbStack Mac mini)  
> **Dedicated Port Block:** `8090–8092` (Collision-free per [`PORT_PLAN.md`](../PORT_PLAN.md))  
> **Cloud Serverless Data Tier:** Upstash Serverless (Dual Purpose: Upstash Redis for Sessions + Upstash Vector for SEC 10-K RAG)  
> **Shared Cluster Logging:** Existing ELK Stack in `logging` namespace (Kibana on `:8084`, Filebeat DaemonSet)

---

## 🔌 Port & Service Allocation Map

### 1. Local Kubernetes Cluster (`financial-agent` Namespace & Shared Platform)

| Component / Pod | Type / Kind | Port Mapping | Lifecycle / Description |
| :--- | :--- | :--- | :--- |
| **Streamlit UI** | LoadBalancer | `8090:8501` | **CI/CD (Phase 9)** — Conversational financial dashboard |
| **FastAPI Agent Ingress** | LoadBalancer | `8091:8000` | **CI/CD (Phase 9)** — ReAct core brain & webhook endpoints |
| **Market Gateway** | ClusterIP | `8004` | **CI/CD (Phase 9)** — Real-time stock quotes, yields & financial news (`yfinance`) |
| **Security Robot Runner** | Job / Pod | — | **CI/CD / Test (Phase 9)** — Automated red-teaming robot for multi-turn security auditing |
| **Langfuse LLMOps UI** | LoadBalancer | `8092:3000` | **Platform (Phase 2)** — OTel traces, latency, costs & DeepEval quality metrics |
| **Langfuse Database** | ClusterIP | `5432` | **Platform (Phase 2)** — Relational persistence for Langfuse traces (`10Gi` PVC) |
| **Kibana Logging UI** | LoadBalancer | `8084:5601` | **Existing Platform (`logging` ns)** — Interactive cluster log dashboards |
| **Elasticsearch Master** | ClusterIP | `9200` | **Existing Platform (`logging` ns)** — Distributed log search & index master |
| **Logstash Pipeline** | ClusterIP | `5044` | **Existing Platform (`logging` ns)** — Beats log ingestion pipeline |
| **Filebeat** | DaemonSet | — | **Existing Platform (`logging` ns)** — Node-level container stdout/stderr harvester |

### 2. Cloud Serverless Data Tier ($0 Cost — 0 Pods in Local K8s)

| Service | Provider | Free Tier Specification | Project Role |
| :--- | :--- | :--- | :--- |
| **Session & Audit Store** | **Upstash Serverless Redis** | 10,000 commands/day free forever | Multi-turn security robot state, audit trail & ReAct checkpoints |
| **Vector DB (RAG)** | **Upstash Serverless Vector** | 1 index · 100k vectors · 10k ops/day free forever | SEC 10-K filings semantic search (`bge-small-en-v1.5` embeddings) |
| **Core Reasoning Brain** | **Groq Cloud LPU** | Free tier (`Meta Llama 3.3 70B`) | Main ReAct intelligence & tool synthesis |
| **Fast Intent Router** | **Groq Cloud LPU** | Free tier (`Meta Llama 3.2 3B`) | Sub-150ms query routing |
| **Input Security Shield** | **Hugging Face Serverless** | Free tier (`Prompt Guard 86M`) | Scans & blocks prompt injections/jailbreaks |
| **Output Safety Auditor** | **Groq Cloud LPU** | Free tier (`Llama Guard 3 8B`) | Fact-checking & safety auditing |
| **Document Embeddings** | **Hugging Face Serverless** | Free tier (`bge-small-en-v1.5`) | 384-dimensional financial document embeddings |

---

## 📂 Target Project Directory Structure (Industry Standard)

```text
05-Financial-Analyst-LLMOps/
├── architecture.html                        # Visual Architecture Blueprint (1920x1080)
├── Implementation_Plan.md                 # This Execution Plan
├── pyproject.toml                        # Modern Python packaging, ruff & pytest configuration
├── requirements.txt                      # Pinned production dependencies
├── .env                                  # Local environment configuration (private)
├── .gitignore
├── .dockerignore
├── Makefile                              # Automation targets: setup, test, lint, run, deploy
│
├── .github/
│   └── workflows/
│       └── ci_cd.yml                     # CI/CD: Lint, DeepEval gate, GHCR build, K8s deploy
│
├── config/                               # Centralized Configurations
│   ├── __init__.py
│   ├── settings.py                       # Pydantic Settings (API keys, ports, models)
│   └── prompt_templates.yaml             # System prompts for ReAct, shields & router
│
├── src/                                  # Core Agent Package (Installable: pip install -e .)
│   ├── __init__.py
│   │
│   ├── agent/                            # Cognitive Engine & Orchestration
│   │   ├── __init__.py
│   │   ├── engine.py                     # ReAct Orchestration Loop (LangGraph / Custom)
│   │   ├── state.py                      # Agent State & Execution Schemas
│   │   └── memory.py                     # Upstash Serverless Redis session thread manager
│   │
│   ├── handlers/                         # 4 Core Internal Service Handlers
│   │   ├── __init__.py
│   │   ├── input_shield.py               # (B) Prompt Guard 86M injection/jailbreak detector
│   │   ├── prompt_router.py              # (C) Llama 3.2 3B fast intent & routing classifier
│   │   ├── react_core.py                 # (D) Meta Llama 3.3 70B main reasoning brain
│   │   └── output_shield.py              # (E) Llama Guard 3 8B safety & hallucination auditor
│   │
│   ├── tools/                            # ReAct Tool Adapters
│   │   ├── __init__.py
│   │   ├── rag_tool.py                   # Upstash Vector SEC 10-K retrieval tool
│   │   ├── sandbox_tool.py               # Deterministic DCF, CAGR & math calculation tool
│   │   └── market_tool.py                # Real-time quotes & news tool (queries :8004)
│   │
│   ├── rag/                              # Upstash Vector Ingestion & Query Pipeline
│   │   ├── __init__.py
│   │   ├── data_collector.py             # SEC EDGAR scraper & markdown document generator
│   │   ├── embeddings.py                 # FastEmbed bge-small-en-v1.5 embedding client (384-dim)
│   │   ├── vector_client.py              # Upstash Vector Client (upstash-vector Python SDK)
│   │   └── ingest.py                     # Document chunker & Upstash Vector loader
│   │
│   └── sandbox/                          # Deterministic Execution Sandbox Runtime
│       ├── __init__.py
│       ├── runner.py                     # Restricted Python AST executor (timeout & safety)
│       └── formulas.py                   # Financial models (DCF, WACC, CAGR, P/E, FCF)
│
├── serving/                              # FastAPI Agent Ingress Service (:8091 / :8000)
│   ├── app.py                            # FastAPI application, CORS & lifespan
│   ├── routes.py                         # Endpoints: /api/v1/analyze, /api/v1/chat, /healthz
│   ├── schemas.py                        # Pydantic v2 request & response DTOs
│   └── Dockerfile                        # Production container for Agent serving
│
├── market_gateway/                       # Market Data Microservice (:8004)
│   ├── app.py                            # Standalone FastAPI service
│   ├── feeds.py                          # yfinance real-time quotes, 10Y yields & financial news
│   └── Dockerfile                        # Production container for market data
│
├── ui/                                   # Streamlit Web UI Frontend (:8090 / :8501)
│   ├── app.py                            # Interactive financial analyst dashboard
│   ├── components/                       # Reusable UI components
│   │   ├── charts.py                     # Plotly stock trends & DCF sensitivity tables
│   │   └── citations.py                  # SEC 10-K source citations & guardrail badges
│   ├── styles.css                        # Modern financial terminal styling
│   └── Dockerfile                        # Production container for Streamlit UI
│
├── observability/                        # LLMOps & Quality Gate
│   ├── langfuse_tracer.py                # Langfuse OTel tracer, latency & cost tracker
│   └── deepeval_gate.py                  # DeepEval quality gate (G-Eval, Faithfulness >= 0.90)
│
├── k8s/                                  # Kubernetes Manifests (Namespace: financial-agent)
│   ├── platform/                         # Persistent Platform Infrastructure (Deploy ONCE in Phase 2)
│   │   ├── 00-namespace.yaml             # Namespace: financial-agent
│   │   ├── 01-sealed-secrets.yaml        # Encrypted credentials via kubeseal (Upstash, Groq, HF, Langfuse)
│   │   ├── 02-configmap.yaml             # URLs, ports, model configurations
│   │   ├── 03-postgres-storage.yaml      # PVC for PostgreSQL database (10Gi)
│   │   ├── 04-postgres-db.yaml           # PostgreSQL Deployment + ClusterIP (:5432)
│   │   └── 05-langfuse-webui.yaml        # Langfuse Web UI + LoadBalancer (:8092)
│   └── apps/                             # Application Workloads (Continuous CI/CD Delivery in Phase 9)
│       ├── market-gateway.yaml           # Market Gateway Deployment + ClusterIP (:8004)
│       ├── agent-serving.yaml            # FastAPI Agent Pod + LoadBalancer (:8091 -> :8000)
│       ├── streamlit-ui.yaml             # Streamlit UI + LoadBalancer (:8090 -> :8501)
│       └── security-robot-job.yaml       # Automated Security Testing Robot Runner Job
│
└── tests/                                # Automated Test Suite
    ├── conftest.py                       # Fixtures & mock LLM responses
    ├── unit/                             # Fast unit tests
    │   ├── test_input_shield.py          # Injection & jailbreak filter tests
    │   ├── test_prompt_router.py         # Intent classification tests
    │   ├── test_output_shield.py         # Output safety check tests
    │   └── test_sandbox_formulas.py      # Math formula precision tests
    ├── integration/                      # End-to-end integration tests
    │   ├── test_react_engine.py          # ReAct reasoning loop & tool calls
    │   ├── test_serving_api.py           # FastAPI endpoints validation
    │   └── test_eval_metrics.py          # DeepEval CI/CD quality gate tests
    └── security_robot/                   # Automated Security Red-Teaming Suite
        ├── run_security_audit.py         # Multi-turn prompt injection & jailbreak robot
        └── attack_vectors.json           # Catalog of adversarial multi-turn test attacks
```

---

## 🚀 Execution Roadmap

### Phase 1: Environment & Project Foundation
- [x] **1.1 Workspace Scaffolding:** Create standard directory layout (`config/`, `src/`, `serving/`, `market_gateway/`, `ui/`, `observability/`, `k8s/`, `tests/`).
- [x] **1.2 Dependencies & Packaging:** Configure `pyproject.toml` and `requirements.txt` (FastAPI, Streamlit, LangChain, Groq, Upstash Redis, Upstash Vector, yfinance, Langfuse, DeepEval).
- [x] **1.3 Dedicated Virtual Environment (`venv`):** Create isolated Python virtual environment (`python3 -m venv venv`).
- [x] **1.4 Settings (`config/settings.py`):** Centralize Pydantic settings reading from `.env` (Groq, HF, Upstash, Langfuse keys, port mappings).

### Phase 2: Platform Infrastructure Setup (`k8s/platform/`)
- [x] **2.1 Namespace & Sealed Secrets Pipeline (`kubeseal`):**
  - [x] Create and apply `00-namespace.yaml` (Namespace: `financial-agent`).
  - [x] Collect API keys from cloud providers (Groq, Hugging Face, Upstash).
  - [x] Store keys locally in `.env` (kept private, git-ignored).
  - [x] Encrypt `.env` into `k8s/platform/01-sealed-secrets.yaml` using `kubeseal` and cluster certificate (`pub-cert.pem`).
  - [x] Deploy `01-sealed-secrets.yaml` and verify decrypted `agent-api-secrets` Secret in `financial-agent`.
- [x] **2.2 Cluster ConfigMap:** Create and apply `02-configmap.yaml` (ports, model names, endpoints).
- [x] **2.3 PostgreSQL Database & Persistent Storage:** Apply `03-postgres-storage.yaml` (`10Gi` PVC) and `04-postgres-db.yaml` (PostgreSQL Deployment + ClusterIP on `:5432`).
- [x] **2.4 Langfuse Web UI Deployment:** Apply `05-langfuse-webui.yaml` (Langfuse Server on LoadBalancer `8092:3000`). Verify `http://localhost:8092` responds.
- [x] **2.5 Shared Logging Verification:** Confirm existing `logging` namespace stack (`elasticsearch:9200`, `logstash:5044`, `filebeat-48pmq`, and `kibana` on `http://localhost:8084`) automatically harvests `financial-agent` logs.

### Phase 3: Upstash Vector Store & SEC 10-K Ingestion (`src/rag/`)
- [x] **3.1 SEC Data Scraper & Markdown Converter (`src/rag/data_collector.py`):** Programmatic SEC EDGAR client that fetches 10-K annual reports, extracts Items 1, 1A, and 7, and saves formatted markdown files to `data/sec_filings/`.
- [x] **3.2 Embeddings Client (`src/rag/embeddings.py`):** FastEmbed BAAI/bge-small-en-v1.5 embedding generator (384-dim, local ONNX runtime, 100% free).
- [x] **3.3 Upstash Vector Client (`src/rag/vector_client.py`):** Connect to Upstash Vector Index via REST SDK (`upstash-vector`) with cosine similarity and metadata filtering.
- [x] **3.4 Ingestion Pipeline (`src/rag/ingest.py`):** Parse, chunk, and embed SEC 10-K filings (Apple, Microsoft, Nvidia) with Item 1, 1A, and 7 segmentations into the Upstash Vector index.

### Phase 4: Execution Tools & Microservices (`src/tools/` & `src/sandbox/`)
- [x] **4.1 Deterministic Sandbox (`src/sandbox/`):** Safe Python execution engine with AST inspection; verified formulas for DCF, WACC, CAGR, P/E.
- [x] **4.2 Market Gateway Microservice (`market_gateway/`):** Standalone FastAPI service on ClusterIP `:8004` serving real-time prices, 10Y yields, and financial news (`yfinance`).
- [x] **4.3 Agent Tool Adapters (`src/tools/`):** Tool wrappers for Upstash Vector RAG, Python sandbox math, and market gateway feeds.

### Phase 5: Core Agent & 4 Service Handlers (`src/agent/` & `src/handlers/`)
- [x] **5.1 Input Shield (`src/handlers/input_shield.py`):** Prompt Guard 86M integration to reject prompt injection and jailbreaks before LLM invocation.
- [x] **5.2 Prompt Router (`src/handlers/prompt_router.py`):** Llama 3.2 3B classifier (< 150ms) routing intent (`RAG_QUERY`, `MARKET_LIVE`, `COMPLEX_VALUATION`, `GENERAL_CHAT`).
- [x] **5.3 ReAct Core Engine (`src/handlers/react_core.py`):** Qwen 27B reasoning loop on Groq LPU driving Thought &rarr; Action &rarr; Observation cycles across tools with resilient fallback synthesis.
- [x] **5.4 Output Shield (`src/handlers/output_shield.py`):** SEC/FINRA regulatory compliance auditor, credential leak scrubber, and factual grounding validator.
- [x] **5.5 Agent Serving API (`serving/`):** FastAPI service on port `:8000` (Ext `:8091`) with Upstash Serverless Redis session checkpoints (`src/agent/memory.py`).

### Phase 6: LLMOps Tracing & Automated Evaluation (`observability/`)
- [x] **6.1 Langfuse Tracing (`observability/langfuse_tracer.py`):** Instrument pipeline with OpenTelemetry; stream step-by-step waterfall traces, token usage, and $0 cost metrics directly to live Langfuse (`:8092`).
- [x] **6.2 DeepEval Quality Gate (`observability/deepeval_gate.py`):** Automated test suite evaluating Faithfulness, Answer Relevancy, Hallucination, and Toxicity (score threshold &ge; 0.90).

### Phase 7: Interactive Financial Dashboard (`ui/`)
- [x] **7.1 Streamlit App (`ui/app.py`):** Conversational analyst UI exposed on Port `:8090` with real-time SSE response streaming and reasoning accordions.
- [x] **7.2 Visualization Components (`ui/components/charts.py`):** Plotly stock price charts and interactive DCF sensitivity tables.
- [x] **7.3 Guardrail & Citation Badges (`ui/components/citations.py`):** Visual indicators for Input/Output Shield status and clickable SEC 10-K document references.

### Phase 8: Containerization & Dockerfiles
- [x] **8.1 `serving/Dockerfile`:** Production multi-stage image for FastAPI Agent Pod (port `:8000`).
- [x] **8.2 `market_gateway/Dockerfile`:** Slim image for Market Gateway microservice (port `:8004`).
- [x] **8.3 `ui/Dockerfile`:** Lightweight image for Streamlit UI (port `:8501`).

### Phase 9: CI/CD Pipeline & Automated Security Robot (`Jenkinsfile` & `k8s/apps/`)
- [x] **9.1 Application Deployment Manifests (`k8s/apps/`):**
  - `market-gateway.yaml` (Deployment + ClusterIP `:8004`).
  - `agent-serving.yaml` (Deployment + LoadBalancer `:8091 -> :8000`).
  - `streamlit-ui.yaml` (Deployment + LoadBalancer `:8090 -> :8501`).
  - `security-robot-job.yaml` (Automated Security Testing Runner Job).
- [x] **9.2 On-Cluster Jenkins CI/CD Pipeline (`Jenkinsfile`):**
  - Continuous SCM polling (`pollSCM('H/2 * * * *')`) monitoring GitHub repository `mamunhabib/financial-analyst-llmops`.
  - Code quality checks (`ruff check .`).
  - Native host Mac Docker builds on Apple Silicon (`linux/arm64`) for `market-gateway`, `agent-serving`, and `streamlit-ui`.
  - Push to GHCR (`ghcr.io/mamunhabib/...`) using existing Jenkins `github-pat` credentials.
  - Automatic local cache cleanup (`docker rmi`) to maintain Mac host disk space.
  - In-cluster automated rolling deployment (`kubectl apply -f k8s/apps/`, rollout restart, and rollout status validation).
- [x] **9.3 Automated Security Robot Run (`tests/security_robot/`):**
  - Launch Security Robot Runner (`security-robot-job.yaml` & UI sidebar trigger) executing multi-turn adversarial injection and jailbreak attacks against the live agent.
  - Verified 100% defense success rate (10/10 attacks defended, 0% leakage) with full trace audit in **Langfuse** (`:8092`).

### Phase 10: Validation & Demonstration
- [x] **10.1 Port Check:** Verified external ports strictly match `:8090` (Streamlit), `:8091` / `:8000` (FastAPI), `:8092` (Langfuse), and `:8084` (Kibana).
- [x] **10.2 Attack Ingress Test:** Confirmed Input Shield blocks prompt injection attempts (`threat=IGNORE_INSTRUCTIONS, score=0.95`, 0 tokens wasted).
- [x] **10.3 Multi-Tool Valuation Test:** Ran 5-year DCF analysis query combining Upstash Vector RAG, live stock price, 10Y Treasury yield, corporate headlines, and Python sandbox math (all 5 tools invoked and synthesized into an institutional report with regulatory disclaimers).
- [x] **10.4 Observability Verification:** Confirmed traces in Langfuse (`:8092`) via API and live web UI, and container stdout/stderr logs in Kibana (`:8084`).
