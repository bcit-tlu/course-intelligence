# Dialog — Diagnostic Interactive Assessment of Learning through Open Grading

Emergency Nursing Course Processor — transforms raw nursing course material
(PDF/text) into categorized knowledge chunks and test questions via a
LangGraph pipeline.

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
| GET    | `/jobs/{id}`          | Job status (`queued`/`processing`/`completed`/`failed`) |
| GET    | `/jobs/{id}/results`  | Learning elements for a completed job         |

### Local Development

```bash
uv sync
MOCK_LLM=true uv run python main.py api
```

Or process a single file:

```bash
uv run python main.py docs/nursing_sepsis_learning_module.pdf
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

## Project Structure

```
dialog/                          # repo root
├── pyproject.toml               # single project file
├── main.py                      # CLI entry point (api / file processing)
├── Dockerfile
├── docker-compose.yml
├── docs/                        # sample course material
├── tests/                       # all tests
│
└── dialog/                      # installable package
    ├── default_config.py        # config dict + env-var overlay
    ├── api.py                   # FastAPI endpoints
    ├── agents/                  # agent factories grouped by role
    │   ├── schemas.py           # Pydantic structured-output models
    │   ├── chunker/             # create_semantic_chunker(llm)
    │   ├── questioner/          # create_question_generator(llm)
    │   ├── auditor/             # create_quality_auditor(llm)
    │   ├── classifier/          # create_dept_classifier(llm) (deferred)
    │   └── utils/               # AgentState, shared helpers
    ├── graph/                   # graph orchestration (no agent logic)
    │   ├── processor_graph.py   # CourseProcessorGraph orchestrator
    │   ├── setup.py             # node/edge wiring
    │   ├── propagation.py       # initial state creation
    │   └── conditional_logic.py # routing (future: human-in-the-loop)
    ├── dataflows/               # data-source abstraction
    │   ├── pdf_parser.py        # PyMuPDF
    │   └── text_parser.py       # plain text / markdown
    └── llm_clients/             # LLM provider abstraction
        ├── base_client.py       # ABC
        ├── factory.py           # create_llm_client()
        ├── openai_client.py     # Ollama / OpenAI compat
        └── mock_client.py       # FakeListChatModel for testing
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_API_KEY` | — | **Required.** API key from [ollama.com/settings/keys](https://ollama.com/settings/keys) |
| `OLLAMA_BASE_URL` | `https://ollama.com` | Ollama Cloud endpoint |
| `OLLAMA_MODEL` | `gemma4:31b-cloud` | Chat model |
| `MOCK_LLM` | `false` | Run pipeline with deterministic mock responses |
