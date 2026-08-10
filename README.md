# Dialog — Diagnostic Interactive Assessment of Learning through Open Grading

Emergency Nursing Course Processor — transforms raw nursing course material
(PDF/text/DOCX/HTML/zip) into categorized knowledge chunks with Bloom's
taxonomy classification via a LangGraph pipeline.

## Quick Start

```bash
cp .env.example .env          # fill in your Ollama Cloud key
docker compose up --build
```

This brings up the whole stack. Once it's running:

| Service | URL | Description |
|---------|-----|-------------|
| **Web UI** | **http://localhost:3000** | Upload modules, watch processing, browse results |
| API | http://localhost:8000 | FastAPI job API |
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
uv run python main.py docs/nursing_sepsis_learning_module.pdf  # Process a single file
```

For frontend development against the running API (hot reload on
http://localhost:5173), see `frontend/README.md`.

### Kubernetes Deployment

For deploying to a cluster with Helm (charts in `charts/`), see
[`docs/deployment.md`](docs/deployment.md) — install prerequisites (CNPG, ingress,
metrics-server), secrets, the Flux GitOps deploy flow, verification, and upgrade/rollback.
Cluster-specific values live in the
[`flux-fleet`](https://github.com/bcit-tlu/flux-fleet) repo
(`apps/overlays/latest/dialog/`).

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
dialog/                          # repo root
├── pyproject.toml               # single project file
├── main.py                      # CLI entry point (api / worker / gateway / file)
├── Dockerfile
├── docker-compose.yml
├── alembic/                     # database migrations
├── alembic.ini
├── charts/                      # Helm charts (backend + frontend)
├── docs/                        # sample course material + deployment guide
├── frontend/                    # React + Vite + TailwindCSS SPA
├── tests/                       # all tests
│
└── dialog/                      # installable package
    ├── __init__.py              # loads .env via dotenv
    ├── default_config.py        # config dict + env-var overlay
    ├── api.py                   # FastAPI endpoints (async job API)
    ├── worker.py                # background worker (Redis queue, reliable pattern)
    ├── gateway.py               # LLM gateway proxy (centralizes LLM calls)
    ├── storage.py               # S3/MinIO object storage wrapper
    ├── agents/                  # agent factories grouped by role
    │   ├── schemas.py           # Pydantic structured-output models (ChunkOutput)
    │   ├── extractor/           # create_content_extractor() — pure Python, no LLM
    │   ├── chunker/             # create_semantic_chunker(llm) — LLM-powered chunking
    │   ├── classifier/          # create_blooms_classifier(llm) — Bloom's taxonomy tagging
    │   └── utils/               # AgentState, KnowledgeChunk, shared helpers
    ├── graph/                   # graph orchestration (no agent logic)
    │   ├── processor_graph.py   # CourseProcessorGraph orchestrator
    │   ├── setup.py             # node/edge wiring (extract → chunk → classify → END)
    │   ├── propagation.py       # initial state creation
    │   ├── steps.py             # node-to-step progress mapping
    │   └── conditional_logic.py # routing (placeholder, future human-in-the-loop)
    ├── dataflows/               # data-source abstraction
    │   ├── interface.py         # parse_document() dispatcher
    │   ├── pdf_parser.py        # PyMuPDF
    │   ├── text_parser.py       # plain text / markdown
    │   ├── docx_parser.py       # python-docx
    │   ├── html_parser.py       # BeautifulSoup4
    │   └── d2l_parser.py        # D2L export (Table of Contents structure)
    ├── db/                      # database layer
    │   ├── models.py            # Job, Result, JobStatus (SQLAlchemy)
    │   └── session.py           # engine + session factory
    └── llm_clients/             # LLM provider abstraction
        ├── base_client.py       # ABC
        ├── factory.py           # create_llm_client(provider, model, mock, ...)
        ├── openai_client.py     # Ollama / OpenAI compat
        ├── azure_client.py      # Azure OpenAI (AzureChatOpenAI)
        └── mock_client.py       # FakeListChatModel for testing
```

## Environment Variables

See [`.env.example`](.env.example) for all options with inline comments.

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
| `DATABASE_URL` | — | Postgres connection string (e.g. `postgresql://dialog:dialog@db:5432/dialog`) |
| `REDIS_URL` | — | Redis connection string (e.g. `redis://redis:6379/0`) |
| `S3_ENDPOINT_URL` | — | S3/MinIO endpoint (e.g. `http://minio:9000`) |
| `S3_ACCESS_KEY` | — | S3 access key |
| `S3_SECRET_KEY` | — | S3 secret key |
| `S3_BUCKET` | `uploads` | S3 bucket name for uploads |
| `LLM_GATEWAY_URL` | — | LLM gateway proxy URL (e.g. `http://llm-gateway:8100`) |
| `GATEWAY_PORT` | `8100` | Port for the LLM gateway service |
