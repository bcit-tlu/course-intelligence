# Course Intelligence

Course Intelligence is an AI-assisted platform for transforming instructional
content into structured educational information. It can be used through
**Course Intelligence Studio** or integrated into other applications through the
**Course Intelligence API**.

Uploaded course material is analysed into **learning elements** — self-contained
knowledge units, each classified against **Bloom's taxonomy** — by an
asynchronous LangGraph pipeline.

## Components

| Component | Role | Implementation |
|---|---|---|
| **Course Intelligence Studio** | Standalone web interface for users | `studio/` |
| **Course Intelligence API** | Programmatic interface for applications | `course_intelligence/api.py` |
| **Course Intelligence Engine** | Core instructional-content analysis layer | `course_intelligence/engine/` |
| **LLM Gateway** | Centralized interface to configured LLM providers | `course_intelligence/llm/gateway.py` |
| **Course Intelligence MCP Server** | Potential future interface for AI applications and agents | Not implemented — [design](docs/architecture.md#future-mcp-server) |

The LLM Gateway selects its provider via `LLM_PROVIDER` — Ollama for development,
Azure OpenAI for pilot/production, and a deterministic mock for tests.

See [`docs/architecture.md`](docs/architecture.md) for dependency rules, naming
conventions, and subsystem internals.

## Pipeline

```text
Course Content
      │
      ▼
Content Extraction                (engine/agents/extractor — pure Python, no LLM)
      │
      ▼
Learning Element Identification   (engine/agents/chunker — LLM-powered)
      │
      ▼
Bloom's Taxonomy Classification   (engine/agents/classifier — LLM-powered)
      │
      ▼
Structured Course Intelligence
```

Supported inputs: `.zip` (including D2L exports), `.pdf`, `.docx`, `.txt`, `.md`.

Each learning element carries a topic, its content, a Bloom's level with a
rationale, and a source page reference where the parser can determine one.

> **Not implemented.** Course Intelligence does not generate questions or
> assessments, map content to learning objectives automatically, or perform
> grading. The implemented pipeline is extraction, learning-element
> identification, and Bloom's classification.

## Quick Start

```bash
cp .env.example .env          # fill in your Ollama Cloud key
docker compose up --build
```

This brings up the whole stack. Once it's running:

| Service | URL | Description |
|---------|-----|-------------|
| **Studio** | **http://localhost:3000** | Upload modules, watch processing, browse results |
| API | http://localhost:8000 | Course Intelligence API (FastAPI job API) |
| LLM Gateway | http://localhost:8100 | LLM proxy (centralizes calls, logs tokens) |
| MinIO console | http://localhost:9001 | Object storage (uploads) |

The database schema is migrated automatically by the one-shot `migrate`
service before the `api`/`worker` start.

### Mock Mode (no LLM tokens)

```bash
MOCK_LLM=true docker compose up --build
```

### Endpoints

| Method | Path                  | Description                                   |
|--------|-----------------------|-----------------------------------------------|
| GET    | `/health`             | Health check                                  |
| POST   | `/jobs`               | Upload a module (zip/pdf/docx/txt/md), queue it |
| GET    | `/jobs`               | List jobs (optional `status` and `X-Tenant-Id` filtering) |
| GET    | `/jobs/{id}`          | Job status (`queued`/`processing`/`completed`/`failed`) |
| GET    | `/jobs/{id}/results`  | Learning elements for a completed job         |

### Local Development

```bash
uv sync
MOCK_LLM=true uv run python main.py api      # FastAPI server
```

Other entrypoints:

```bash
uv run python main.py worker                  # Background job worker
uv run python main.py gateway                 # LLM gateway proxy (:8100)
uv run python main.py <file.pdf|docx|txt|md|zip>  # Process a single file
```

For Studio development against the running API (hot reload on
http://localhost:5173), see `studio/README.md`.

### Kubernetes Deployment

For deploying to a cluster with Helm (charts in `charts/`), see
[`docs/deployment.md`](docs/deployment.md) — install prerequisites (CNPG, ingress,
metrics-server), secrets, the Flux GitOps deploy flow, verification, and upgrade/rollback.
Cluster-specific values live in the
[`flux-fleet`](https://github.com/bcit-tlu/flux-fleet) repo
(`apps/overlays/latest/course-intelligence/`).

### Tests

```bash
uv sync --all-extras
uv run pytest tests/ -v
```

Test suite:

| File | Description |
|------|-------------|
| `test_graph_mock.py` | End-to-end pipeline test with mock LLM |
| `test_jobs_api.py` | Async job flow — happy path + failure cases |
| `test_blooms_classifier.py` | Bloom's taxonomy classification logic |
| `test_directory_parser.py` | Directory/zip/D2L parsing |
| `test_db.py` | SQLAlchemy models and session |
| `test_progress.py` | Per-node progress tracking |
| `test_retention.py` | S3 upload retention cleanup |

## Project Structure

```
course-intelligence/             # repo root
├── pyproject.toml               # single project file
├── main.py                      # CLI entry point (api / worker / gateway / file)
├── Dockerfile
├── docker-compose.yml
├── alembic/                     # database migrations
├── alembic.ini
├── charts/                      # Helm charts (backend + studio)
├── docs/                        # architecture + deployment guides
├── studio/                      # Course Intelligence Studio (React + Vite + TailwindCSS SPA)
├── tests/                       # all tests
│
└── course_intelligence/         # installable package
    ├── __init__.py              # loads .env via dotenv
    ├── default_config.py        # config dict + env-var overlay
    ├── api.py                   # FastAPI endpoints (async job API)
    ├── worker.py                # background worker (Redis queue, reliable pattern)
    ├── storage.py               # S3/MinIO object storage wrapper
    ├── engine/                  # transport-independent processing core
    │   ├── agents/              # agent factories grouped by role
    │   │   ├── schemas.py       # Pydantic structured-output models (ChunkOutput)
    │   │   ├── extractor/       # create_content_extractor() — pure Python, no LLM
    │   │   ├── chunker/         # create_semantic_chunker(llm) — LLM-powered chunking
    │   │   ├── classifier/      # create_blooms_classifier(llm) — Bloom's taxonomy tagging
    │   │   └── utils/           # AgentState, KnowledgeChunk, shared helpers
    │   ├── graph/               # graph orchestration (no agent logic)
    │   │   ├── processor_graph.py   # CourseProcessorGraph orchestrator
    │   │   ├── setup.py             # node/edge wiring (extract → chunk → classify → END)
    │   │   ├── propagation.py       # initial state creation
    │   │   ├── steps.py             # node-to-step progress mapping
    │   │   └── conditional_logic.py # routing (placeholder, future human-in-the-loop)
    │   └── dataflows/           # data-source abstraction
    │       ├── interface.py     # parse_document() dispatcher
    │       ├── pdf_parser.py    # PyMuPDF
    │       ├── text_parser.py   # plain text / markdown
    │       ├── docx_parser.py   # python-docx
    │       ├── html_parser.py   # BeautifulSoup4
    │       └── d2l_parser.py    # D2L export (Table of Contents structure)
    ├── db/                      # database layer
    │   ├── models.py            # Job, Result, JobStatus (SQLAlchemy)
    │   └── session.py           # engine + session factory
    └── llm/                      # LLM layer (clients + gateway)
        ├── gateway.py            # LLM Gateway proxy (FastAPI, port 8100)
        └── clients/              # LLM provider abstraction
            ├── base_client.py    # ABC
            ├── factory.py        # create_llm_client(provider, model, mock, ...)
            ├── openai_client.py  # Ollama / OpenAI compat
            ├── azure_client.py   # Azure OpenAI (AzureChatOpenAI)
            └── mock_client.py    # FakeListChatModel for testing
```

## Environment Variables

LLM and dev/testing options are in [`.env.example`](.env.example).
Infrastructure vars (database, Redis, S3, gateway) are set in
`docker-compose.yml`.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM provider: `ollama` (dev), `azure` (pilot/prod), `mock` (testing) |
| `OLLAMA_API_KEY` | — | API key from [ollama.com/settings/keys](https://ollama.com/settings/keys) |
| `OLLAMA_BASE_URL` | `https://ollama.com` | Ollama Cloud endpoint |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | Chat model |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI instance URL |
| `AZURE_OPENAI_API_KEY` | — | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | `2024-06-01` | Azure OpenAI API version |
| `AZURE_OPENAI_DEPLOYMENT` | — | Azure chat model deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | — | Azure embedding model deployment name |
| `LLM_MAX_TOKENS` | `8192` | Max output tokens per LLM call (prevents truncated JSON) |
| `MOCK_LLM` | `false` | Run pipeline with deterministic mock responses |
| `DEV_RELOAD` | `false` | Enable uvicorn auto-reload (dev only) |
| `RETENTION_COUNT` | `10` | Number of recent job uploads to retain in S3 |
| `DATABASE_URL` | — | Postgres connection string (e.g. `postgresql://course_intelligence:course_intelligence@db:5432/course_intelligence`) |
| `REDIS_URL` | — | Redis connection string (e.g. `redis://redis:6379/0`) |
| `S3_ENDPOINT_URL` | — | S3/MinIO endpoint (e.g. `http://minio:9000`) |
| `S3_ACCESS_KEY` | — | S3 access key |
| `S3_SECRET_KEY` | — | S3 secret key |
| `S3_BUCKET` | `uploads` | S3 bucket name for uploads |
| `LLM_GATEWAY_URL` | — | LLM gateway proxy URL (e.g. `http://llm-gateway:8100`) |
| `GATEWAY_PORT` | `8100` | Port for the LLM gateway service |
