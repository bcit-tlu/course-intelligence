# Course Intelligence — Architecture Reference

This document covers the product architecture and the internal architecture of
the Course Intelligence backend subsystems. For deployment instructions see
[deployment.md](deployment.md); for the project tree and quick start see the
root [README](../README.md).

> **Naming transition.** The product was previously called *Dialog*. The
> component names below are authoritative. A small set of infrastructure
> identifiers (the database, namespace, and Secret names) intentionally still use
> `dialog` — see [Legacy identifiers](#legacy-identifiers) for the rationale and
> the full decision record.

---

## Product Components

Course Intelligence is a platform, not a single application. It has one
processing core with multiple interfaces in front of it.

| Component | Role | Current implementation |
|---|---|---|
| **Course Intelligence** | The overall product | — |
| **Course Intelligence Studio** | Standalone web interface for users | `studio/` (React + Vite + TailwindCSS) |
| **Course Intelligence API** | Programmatic interface for applications | `course_intelligence/api.py` (FastAPI) |
| **Course Intelligence Engine** | Core instructional-content analysis layer | `course_intelligence/engine/agents/`, `course_intelligence/engine/graph/`, `course_intelligence/engine/dataflows/` |
| **LLM Gateway** | Centralized interface to configured LLM providers | `course_intelligence/llm/gateway.py` + `course_intelligence/llm/clients/` |
| **Course Intelligence MCP Server** | Future interface for AI applications and agents | Not implemented — intentionally deferred ([design](#future-mcp-server)) |

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

## Future MCP Server

> **Nothing in this section is implemented.** There is no MCP server, no MCP
> dependency, and no MCP code path in this repository. This section records the
> intended integration direction so that a future implementation does not have to
> reverse-engineer it — and so that it is not built prematurely.

### Boundary

An MCP server would let AI agents consume Course Intelligence the way Studio
does today — as a client of the API, not of the Engine:

```text
AI Agent / AI Application
          │
          ▼
Course Intelligence MCP Server
          │
          ▼
Course Intelligence API
          │
          ▼
Course Intelligence Engine
```

The MCP Server calls the API (or an application service layer sitting beside it),
**never the Engine directly**, and never reimplements processing logic. This is
the same rule Studio follows, and it is what keeps a single processing
implementation.

The Engine boundary already permits this without modification: the Engine is
transport-agnostic (no FastAPI types, no HTTP objects), and
`CourseProcessorGraph` is its only entry point. Adding an MCP transport is
therefore additive — it does not require touching
`course_intelligence/engine/`.

### When to build it

Only when a concrete AI consumer requires MCP access. An MCP server added for
architectural symmetry would be another deployable, another auth surface, and
another schema to version, with no user. Deferring it is the decision, not an
oversight.

### Candidate tools

These map onto endpoints that exist today in `course_intelligence/api.py`:

| Candidate tool | Backing endpoint |
|---|---|
| `process_course` | `POST /jobs` (202, multipart upload + `learning_objectives`) |
| `get_processing_status` | `GET /jobs/{job_id}` |
| `list_jobs` | `GET /jobs` (supports `limit`, `status`, `X-Tenant-Id`) |
| `get_learning_elements` | `GET /jobs/{job_id}/results` (409 until `completed`) |
| `get_bloom_classification` | Projection of `GET /jobs/{job_id}/results` |

These would each require **new API capability first** — they are not thin
wrappers:

| Candidate tool | Missing capability |
|---|---|
| `search_learning_elements` | No search/query endpoint; would need vector or text search over `results` |
| `get_course_summary` | No summary is computed or stored |

Because processing is asynchronous, `process_course` cannot be a blocking call.
An MCP client must either poll `get_processing_status` or the API must first grow
a completion notification.

Finally, these have been floated but are **roadmap items, not MCP work** — each
depends on a product capability the system does not have (see
[Retired name](#retired-name)). Exposing them over MCP is the last step, not the
first:

```text
map_learning_objectives      # requires objective-to-content mapping
identify_content_gaps        # requires coverage analysis
generate_knowledge_checks    # requires question generation
analyze_course_coverage      # requires a course entity + coverage analysis
```

### Candidate resources

```text
course://{course_id}
course://{course_id}/elements
course://{course_id}/elements/{element_id}
course://{course_id}/sources/{source_id}
```

**Prerequisite:** the data model is job-centric, not course-centric — `Job` and
`Result` (see [Database](#database)), keyed by job UUID, with no course entity
and no stable `course_id`. These URIs require introducing a course identifier
first; until then the addressable unit is a job, not a course.

### Placement (undecided)

```text
mcp/                        # independently deployed service
course_intelligence/mcp/    # in-package module
```

Deferred until there is a concrete consumer. The trade-off is independent
scaling and deployment isolation versus sharing the API's process, config, and
existing auth. Either satisfies the boundary rules above.

### Naming

The MCP Server exposes Course Intelligence *to* AI agents. The
[LLM Gateway](#llm-gateway) *consumes* LLM providers. They face opposite
directions and must not be conflated — see
[LLM Gateway](#llm-gateway) for why the gateway is never called an "MCP Gateway".

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

Deployment identifiers were reviewed individually rather than renamed by a
blanket find-and-replace. Each decision below is deliberate.

| Identifier | Decision | Reason |
|---|---|---|
| Chart `dialog-backend` → `course-intelligence-backend` | **Renamed** | Done while no production cluster was running, so selector recreation cost nothing |
| Chart `dialog-frontend` → `course-intelligence-studio` | **Renamed** | Same window; also aligns the chart with the `studio` component name |
| Chart dir `charts/frontend` → `charts/studio` | **Renamed** | Makes the directory match both the component and the chart name, so CI can derive `charts/<component>` |
| Image `dialog-api` → `course-intelligence-api` | **Renamed** | New GHCR repository; old tags remain readable under the old name |
| Image `dialog-frontend` → `course-intelligence-studio` | **Renamed** | As above |
| PostgreSQL database, username, password (`dialog`) | **Retained permanently** | Renaming requires a data migration for a cosmetic gain |
| Kubernetes namespace (`dialog`) | **Retained permanently** | Namespaces are immutable; renaming means recreating every namespaced resource |
| Secret names (`dialog-llm`, `dialog-s3`) | **Retained permanently** | Created out-of-band by operators; renaming breaks existing clusters for no benefit |
| Ingress hostnames (`dialog.<env>.ltc.bcit.ca`) | **Deferred** | Requires DNS and certificate changes coordinated outside this repo |
| Redis queue names (`dialog:jobs` → `course-intelligence:jobs`) | **Renamed** | Beta application; downtime acceptable — any in-flight jobs are lost on restart anyway |
| `flux-fleet` overlay path (`apps/overlays/latest/dialog/`) | **Deferred** | Lives in a separate repository, on its own release cadence |

The chart rename is a **breaking deployment change**: `app.kubernetes.io/name`
feeds each Deployment's immutable `spec.selector`, so upgrades require deleting
and recreating the Deployments, and the `flux-fleet` overlays must set the new
`fullnameOverride` values in the same change. See
[deployment.md](deployment.md) for the migration procedure.

### Observability identifiers

No observability configuration (OpenTelemetry, Prometheus, Grafana, Loki, Tempo)
exists in the repository yet. When it is added, service names should follow the
component naming rather than the legacy image names:

```text
course-intelligence-api
course-intelligence-worker
course-intelligence-llm-gateway
```

Any dashboards or queries introduced later must be updated together with the
identifiers they reference.

### Phase 11 reference audit

A full `grep -Rni "dialog"` was run after Phases 2–10. Every match was
classified into one of four categories. Two stale references were found and
fixed during the audit; all remaining matches are legitimate.

**Fixed during audit:**

| File | Was | Now |
|---|---|---|
| `tests/test_db.py` docstring | "dialog.db package" | "course_intelligence.db package" |
| `studio/src/pages/DocsPage.tsx` CSS class | `prose-dialog` | `prose` |

**Infrastructure identifiers (retain — see table above):**

| File(s) | Reference | Notes |
|---|---|---|
| `course_intelligence/worker.py`, `api.py` | Redis queues `course-intelligence:jobs`, `course-intelligence:jobs:processing` | Renamed from `dialog:jobs` during Phase 11 |
| `course_intelligence/db/session.py`, `default_config.py` | Local-dev / example Postgres URL `dialog:dialog@…/dialog` | Matches the retained Postgres credentials |
| `docker-compose.yml` | `POSTGRES_DB/USER/PASSWORD: dialog`, `DATABASE_URL` | Dev-compose Postgres credentials |
| `charts/backend/values.yaml` | Postgres URI / database / username / password | Documented in-chart as intentionally retained |
| `docs/deployment.md` | Namespace `dialog`, secrets `dialog-llm`/`dialog-s3`, ingress hosts, Helm release names, flux-fleet paths | All are live infrastructure identifiers |
| `docs/architecture.md` | Legacy identifiers table, naming-transition note, queue-flow description | Documentation of the retained identifiers |
| `README.md` | Flux-fleet overlay path, example `DATABASE_URL` | Real path in external repo; example uses retained credentials |

**Historical references (retain — do not edit):**

| File(s) | Count | Notes |
|---|---|---|
| `CHANGELOG.md` | 50 | Past release history |
| `studio/CHANGELOG.md` | 20 | Past release history |
| `Course Intelligence Rebranding…Implementation Plan.md` | 22 | Master plan document |
| `docs/rebranding-plan/*.md` | 40 | Rebranding plan phases |
| `flux-fleet-plan.md` | 67 | Migration plan for external repo |

**Build artifacts (Phase 12 — regenerate or gitignore):**

| File(s) | Count | Notes |
|---|---|---|
| `studio/dist/` | 4 | Committed build output with old branding baked in |
| `studio/.vite/` | 8 | Vite dependency cache |

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

1. `BLMOVE course-intelligence:jobs → course-intelligence:jobs:processing` — atomically claim a job
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

`llm/clients/` abstracts the LLM provider behind a common interface.

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
