# System Components

This page describes each subsystem of Course Intelligence and where its code
lives.

## Engine

The core instructional-content analysis layer. Transport-agnostic — no FastAPI
types, no HTTP objects. `CourseProcessorGraph` is the single public entry point.

### Agents (`course_intelligence/engine/agents/`)

LangGraph node factories that implement each pipeline stage:

| Factory | Node | LLM | Output |
|---------|------|-----|--------|
| `create_content_extractor()` | `extract` | No | `CourseModule` with structured pages |
| `create_semantic_chunker(llm)` | `chunk` | Yes | `list[KnowledgeChunk]` (topic + content) |
| `create_blooms_classifier(llm)` | `classify` | Yes | Each chunk tagged with Bloom's level + rationale |

The classifier batches 10 chunks per LLM call (`BATCH_SIZE = 10`). If the LLM
returns invalid JSON for a batch, those chunks are left `unclassified` rather
than failing the job.

### Graph (`course_intelligence/engine/graph/`)

- `processor_graph.py` — `CourseProcessorGraph`: compiles the LangGraph state
  machine, owns LLM client creation, exposes `process()` and
  `process_with_progress()`.
- `steps.py` — maps LangGraph node names to human-readable step labels
  (`extracting`, `chunking`, `classifying`) for progress tracking.

### Dataflows / Parsers (`course_intelligence/engine/dataflows/`)

`interface.py` is the entry point — `dispatch(source)` detects the input type
and routes to the correct parser. All parsers return a `CourseModule`.

| Format | Extension(s) | Parser | Notes |
|--------|-------------|--------|-------|
| PDF | `.pdf` | `pdf_parser.py` (PyMuPDF) | |
| Word | `.docx` | `docx_parser.py` (python-docx) | |
| HTML | `.html`, `.htm` | `html_parser.py` (BeautifulSoup4) | |
| Text | `.txt`, `.md` | `text_parser.py` | |
| Zip | `.zip` | `interface.py` | Extracts only `.html`/`.htm`/`.pdf`; skips media |
| Directory | — | `interface.py` | D2L `Table of Contents.html` detection → `d2l_parser.py`; or generic recursive scan |

## LLM Gateway

`course_intelligence/llm/gateway.py` is a thin FastAPI proxy that centralizes
all LLM calls.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + provider + cumulative stats |
| POST | `/v1/complete` | Forward a chat completion request to the configured LLM |
| GET | `/v1/stats` | Cumulative token usage and request stats |

Provider selection is driven by the `LLM_PROVIDER` env var. The gateway lazily
initializes the LLM client on first request.

### LLM Clients (`course_intelligence/llm/clients/`)

| File | Provider | Class |
|------|----------|-------|
| `base_client.py` | — | `BaseLLMClient` ABC |
| `factory.py` | — | `create_llm_client(provider, model, mock, ...)` |
| `openai_client.py` | Ollama / OpenAI / LiteLLM | `ChatOpenAI` (langchain_openai) |
| `azure_client.py` | Azure OpenAI | `AzureChatOpenAI` (langchain_openai) |
| `mock_client.py` | Testing | `FakeListChatModel` (langchain_core) |

## API

`course_intelligence/api.py` — FastAPI application providing the async job API.
See [API Reference](#api-reference) for endpoint details.

## Worker

`worker.py` dequeues jobs from Redis and runs the pipeline using the reliable
queue pattern (`BLMOVE` / `LREM`):

1. Atomically claim a job from Redis
2. Download the upload from MinIO to a temp directory
3. Run `CourseProcessorGraph.process_with_progress()` with an `on_step` callback
4. Save results to Postgres, mark job completed/failed
5. Remove the job from the processing list

On startup, `_reclaim_stale_jobs()` moves any jobs left in the processing list
back to the main queue (handles worker crashes).

## Database

`course_intelligence/db/models.py` — SQLAlchemy models, migrations via Alembic.

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

## Storage

`course_intelligence/storage.py` wraps boto3 for S3-compatible object storage
(MinIO locally, any S3 in production).

| Function | Description |
|----------|-------------|
| `upload_fileobj(fileobj, key)` | Stream a file-like object to storage |
| `download_file(key, dest_path)` | Download an object to a local path |
| `delete_object(key)` | Delete an object |
| `object_exists(key)` | Check if an object exists |

## Studio

`studio/` — React + Vite + TailwindCSS single-page application.

- Communicates with the backend **through the API** — never directly with the
  Engine.
- Pages: Upload, Jobs List, Job Detail, Docs, Dev Docs.
- Components: `BloomsBadge`, `BloomsSummary`, `ElementCard`, `LevelFilter`,
  `ProcessingView`, `ResultsView`.
- API client in `studio/src/api/`.
- Analytics events in `studio/src/analytics/`.
