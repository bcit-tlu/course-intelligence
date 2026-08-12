# Course Intelligence — Architecture Reference

This document covers the product architecture and the internal architecture of
the Course Intelligence backend subsystems. For deployment instructions see
[deployment.md](deployment.md); for the project tree and quick start see the
root [README](../README.md).

> **Naming transition.** The product was previously called *Dialog*. The
> component names below are authoritative going forward; some code paths,
> infrastructure identifiers, and image names still use `dialog` and are being
> migrated in phases. See [rebranding-plan/](rebranding-plan/README.md).

---

## Product Components

Course Intelligence is a platform, not a single application. It has one
processing core with multiple interfaces in front of it.

| Component | Role | Current implementation |
|---|---|---|
| **Course Intelligence** | The overall product | — |
| **Course Intelligence Studio** | Standalone web interface for users | `frontend/` (React + Vite + TailwindCSS) |
| **Course Intelligence API** | Programmatic interface for applications | `dialog/api.py` (FastAPI) |
| **Course Intelligence Engine** | Core instructional-content analysis layer | `dialog/agents/`, `dialog/graph/`, `dialog/dataflows/` |
| **LLM Gateway** | Centralized interface to configured LLM providers | `dialog/gateway.py` + `dialog/llm_clients/` |
| **Course Intelligence MCP Server** | Future interface for AI applications and agents | Not implemented — intentionally deferred |

### Component Architecture

```text
                        Course Intelligence
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
            Studio             API          MCP Server
                                               (future)
              │                 │                 │
              └─────────────────┼─────────────────┘
                                │
                              Engine
                                │
                 ┌──────────────┼──────────────┐
                 │              │              │
             Extraction     Learning       Bloom's
                            Elements     Classification
```

The three Engine capabilities map to the LangGraph nodes documented under
[Pipeline](#pipeline): `extract`, `chunk`, and `classify`.

---

## Dependency Rules

These are design constraints, enforced at code review:

- Studio communicates with Course Intelligence **through the API** — never
  directly with the Engine.
- External applications communicate **through the API**.
- Future AI applications may communicate through an **MCP Server**.
- The API invokes the Course Intelligence Engine.
- The Engine **must not** depend on the Studio.
- The Engine **must remain independent of transport mechanisms** — no FastAPI
  routing, no HTTP request/response objects, no MCP types. It accepts Python
  inputs/state and returns structured results.
- A future MCP layer **must call the API or an application service layer**
  rather than duplicating processing logic.

The Engine's only permitted dependencies are LangGraph/LangChain, the LLM client
abstraction, and pure-Python parsing libraries. `CourseProcessorGraph` is the
single public entry point into the Engine.

---

## Naming Conventions

### Product vs. code names

Product names are title-cased prose ("Course Intelligence Engine"). Code uses
ordinary Python module naming (`engine`, `llm`, `api`). Product names are not
embedded in identifiers.

### User-facing vs. internal terminology

The user-facing term is **Learning Elements**. The internal representation keeps
its existing name:

| Layer | Term |
|---|---|
| Studio / API docs / user messaging | Learning Element |
| Python, database, JSON payloads | `KnowledgeChunk`, `knowledge_map`, `chunk_id` |

Renaming the internal type would touch the database schema, the API response
contract, and the Studio's TypeScript types. That is deliberately **out of
scope** — the internal name is retained, and only presentation strings change.
Avoid introducing further synonyms ("Semantic Chunk", "Knowledge Element") in
either layer.

### LLM Gateway

The service that talks to Ollama, Azure OpenAI, and future providers is the
**LLM Gateway** — never an "MCP Gateway" or "AI Gateway". This keeps it clearly
distinct from a future MCP Server, which serves a different purpose (exposing
Course Intelligence *to* AI agents, rather than consuming LLMs).

### Retired name

The former acronym *"Diagnostic Interactive Assessment of Learning through Open
Grading"* is retired. It describes assessment and grading capabilities that the
system does not implement — the pipeline is `extract → chunk → classify`, and
question generation, auditing, and grading are not present. Any such
capabilities belong in a roadmap, not in product naming.

### Legacy identifiers

Some `dialog` identifiers are retained deliberately because renaming them
carries operational risk with no functional benefit: the PostgreSQL database
name/user, object-storage buckets, Kubernetes resource names and selectors, and
published container image names. These are reviewed — not automatically
renamed — during the deployment phase.

---

## Pipeline

The processing pipeline is a LangGraph state machine with three nodes:

```
extract → chunk → classify → END
```

### Nodes

| Node | Factory | LLM | Purpose |
|------|---------|-----|---------|
| `extract` | `create_content_extractor()` | No | Detects format, routes to the appropriate parser in `dataflows/`, returns a `CourseModule` |
| `chunk` | `create_semantic_chunker(llm)` | Yes | Splits extracted text into atomic `KnowledgeChunk` objects (topic + content) |
| `classify` | `create_blooms_classifier(llm)` | Yes | Tags each chunk with a Bloom's taxonomy level + rationale, batched (10 chunks per LLM call) |

### AgentState

The state object that flows through every node (`agents/utils/agent_states.py`):

| Field | Set by | Type |
|-------|--------|------|
| `source_path` | Propagator | `str` |
| `learning_objectives` | Propagator | `str` |
| `raw_text` | extract | `str` (concatenated page texts) |
| `course_module` | extract | `CourseModule` (structured pages) |
| `knowledge_map` | chunk, classify | `list[KnowledgeChunk]` |
| `error` | any node | `str \| None` |

### CourseModule / ContentPage

`CourseModule` is the intermediate representation produced by the extractor:

```python
CourseModule:
    course_name: str
    module_id: str       # "single" | "generic" | D2L module id
    source_folder: str
    pages: list[ContentPage]

ContentPage:
    page_number: int
    title: str
    source_file: str
    content_type: str    # "html_page" | "pdf" | "docx" | "text"
    text: str
```

### KnowledgeChunk

```python
KnowledgeChunk:
    chunk_id: str
    topic: str
    content: str
    source_page: str     # optional — title of the originating page
    page_number: int     # optional
    blooms_level: str    # optional — set by classifier
    blooms_rationale: str # optional
```

### Orchestrator

`CourseProcessorGraph` (`graph/processor_graph.py`) is the single public API:

- Owns LLM creation (routes by `llm_provider`: ollama / azure / mock)
- Compiles the LangGraph state machine
- `process(source_path, learning_objectives)` — single invoke
- `process_with_progress(source_path, learning_objectives, on_step)` — dual-mode streaming with per-node callback

### Progress tracking

`graph/steps.py` maps LangGraph node names to human-readable step labels:

```python
NODE_TO_STEP = {
    "extract": "extracting",
    "chunk": "chunking",
    "classify": "classifying",
}
```

The worker passes `on_step` to `process_with_progress`, which writes the current
step to the `Job.current_step` column. The frontend mirrors `STEP_ORDER` to
render a progress indicator.

---

## Dataflows (parsers)

`dataflows/interface.py` is the entry point — `dispatch(source)` detects the
input type and routes to the correct parser. All parsers return a `CourseModule`.

### Supported input formats

| Format | Extension(s) | Parser | Notes |
|--------|-------------|--------|-------|
| PDF | `.pdf` | `pdf_parser.py` (PyMuPDF) | |
| Word | `.docx` | `docx_parser.py` (python-docx) | |
| HTML | `.html`, `.htm` | `html_parser.py` (BeautifulSoup4) | |
| Text | `.txt`, `.md` | `text_parser.py` | |
| Zip | `.zip` | `interface.py` (selective extraction) | Extracts only `.html`/`.htm`/`.pdf`; skips media, macOS metadata |
| Directory | — | `interface.py` | Tier 1: D2L `Table of Contents.html` detection → `d2l_parser.py`; Tier 2: generic recursive scan with natural sort |

### D2L parser

`d2l_parser.py` handles D2L (Desire2Learn) course exports. It detects a
`Table of Contents.html` file in the directory tree and follows the D2L
module structure to build an ordered `CourseModule`.

### Zip handling

The zip dispatcher extracts only `.html`, `.htm`, and `.pdf` files to a
temporary directory (skipping images, video, audio, and macOS metadata),
then re-dispatches as a directory. A 2 GB D2L export with media typically
shrinks to ~200 MB of extractable content.

---

## LLM Gateway

`gateway.py` is a thin FastAPI proxy that centralizes all LLM calls.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + provider + cumulative stats |
| POST | `/v1/complete` | Forward a chat completion request to the configured LLM |
| GET | `/v1/stats` | Cumulative token usage and request stats |

### Purpose

- Centralize Azure OpenAI / Ollama calls in one service
- Manage retries and rate limits
- Log token usage and estimate cost
- Keep API keys out of workers (only the gateway needs credentials)
- Make it easy to switch providers without touching workers

The gateway lazily initializes the LLM client on first request, using the
same `create_llm_client()` factory as the graph. Provider selection is driven
by `LLM_PROVIDER` env var.

---

## Worker

`worker.py` dequeues jobs from Redis and runs the pipeline.

### Reliable queue pattern

Uses Redis `BLMOVE` / `LREM` (the reliable queue pattern from Redis docs):

1. `BLMOVE dialog:jobs → dialog:jobs:processing` — atomically claim a job
2. Download the upload from MinIO to a temp directory
3. Run `CourseProcessorGraph.process_with_progress()` with an `on_step` callback
4. Save results to Postgres, mark job completed/failed
5. `LREM` to remove the job from the processing list

### Stale job recovery

On startup, `_reclaim_stale_jobs()` moves any jobs left in the processing list
back to the main queue. This handles worker crashes mid-job.

### Idempotency

Before re-inserting results, the worker deletes any existing `Result` rows for
the job (`session.query(Result).filter_by(job_id=...).delete()`). This ensures
a reclaimed job doesn't produce duplicate results.

### Upload retention

After each job, `cleanup_old_uploads()` deletes S3 objects for jobs beyond
`RETENTION_COUNT` (default 10). Job and Result rows are preserved in Postgres;
only the S3 upload is purged and the job row is deleted.

---

## Storage

`storage.py` wraps boto3 for S3-compatible object storage (MinIO locally,
any S3 in production).

| Function | Description |
|----------|-------------|
| `upload_fileobj(fileobj, key)` | Stream a file-like object to storage (multipart upload) |
| `download_file(key, dest_path)` | Download an object to a local path |
| `delete_object(key)` | Delete an object |
| `object_exists(key)` | Check if an object exists |

Configuration via `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`,
`S3_BUCKET` env vars. Falls back to `http://localhost:9000` with default
MinIO credentials for local dev.

---

## Database

`db/models.py` defines the SQLAlchemy models. Migrations are managed by
Alembic (`alembic/` directory, `alembic.ini` config).

### Job

| Column | Type | Notes |
|--------|------|-------|
| `id` | Text (PK) | UUID4 |
| `status` | Enum | `queued` / `processing` / `completed` / `failed` |
| `filename` | Text | Original upload filename |
| `storage_key` | Text | S3 object key |
| `learning_objectives` | Text | Instructor-provided objectives |
| `tenant_id` | Text (nullable, indexed) | Optional tenant isolation |
| `error` | Text (nullable) | Error message if failed |
| `current_step` | Text (nullable) | Current pipeline step label |
| `created_at` | DateTime (tz) | |
| `updated_at` | DateTime (tz) | Auto-updated on commit |

### Result

| Column | Type | Notes |
|--------|------|-------|
| `id` | Text (PK) | UUID4 |
| `job_id` | Text (FK → jobs.id) | `ON DELETE CASCADE` |
| `topic` | Text | Chunk topic |
| `content` | Text | Chunk content |
| `blooms_level` | Text (nullable) | Bloom's taxonomy level |
| `blooms_rationale` | Text (nullable) | Classification rationale |
| `source_page` | Text (nullable) | Originating page title |
| `page_number` | Integer (nullable) | Originating page number |

### Session management

`db/session.py` provides `get_session()` — a session factory backed by the
engine configured from `DATABASE_URL`. Both the API and worker use this.

---

## LLM Clients

`llm_clients/` abstracts the LLM provider behind a common interface.

| File | Provider | Class |
|------|----------|-------|
| `base_client.py` | — | `BaseLLMClient` ABC |
| `factory.py` | — | `create_llm_client(provider, model, mock, ...)` |
| `openai_client.py` | Ollama / OpenAI | `ChatOpenAI` (langchain_openai) |
| `azure_client.py` | Azure OpenAI | `AzureChatOpenAI` (langchain_openai) |
| `mock_client.py` | Testing | `FakeListChatModel` (langchain_core) |

Provider selection is driven by `LLM_PROVIDER` env var:
- `ollama` — dev default, uses OpenAI-compatible API against Ollama Cloud
- `azure` — pilot/prod, uses Azure OpenAI
- `mock` — testing, deterministic responses without API calls

---

## Bloom's Classifier

`agents/classifier/blooms_classifier.py` tags each knowledge chunk with a
Bloom's taxonomy level and a one-sentence rationale.

### Levels

Remember, Understand, Apply, Analyze, Evaluate, Create.

### Batching

Chunks are classified in batches of 10 (`BATCH_SIZE = 10`) to minimize LLM
call count. One LLM call per batch, not per chunk.

### Fallback handling

- If the LLM returns invalid JSON for a batch, those chunks are left
  `unclassified` rather than failing the job.
- If a batch raises an exception, chunks get `blooms_level = "unclassified"`
  via `setdefault` — the job continues.
- Matching is by `chunk_id` first, falling back to positional matching when
  the LLM echoes different/missing IDs but the counts line up.
