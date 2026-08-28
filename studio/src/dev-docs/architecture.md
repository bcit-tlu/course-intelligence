# Architecture

## Product Components

Course Intelligence is a platform, not a single application. It has one
processing core with multiple interfaces in front of it.

| Component | Role | Current implementation |
|---|---|---|
| **Course Intelligence** | The overall product | — |
| **Course Intelligence Studio** | Standalone web interface for users | `studio/` (React + Vite + TailwindCSS) |
| **Course Intelligence API** | Programmatic interface for applications | `course_intelligence/api.py` (FastAPI) |
| **Course Intelligence Engine** | Core instructional-content analysis layer | `course_intelligence/engine/agents/`, `engine/graph/`, `engine/dataflows/` |
| **LLM Gateway** | Centralized interface to configured LLM providers | `course_intelligence/llm/gateway.py` + `llm/clients/` |

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

## Dependency Rules

These are design constraints, enforced at code review:

- Studio communicates with Course Intelligence **through the API** — never
  directly with the Engine.
- External applications communicate **through the API**.
- The API invokes the Course Intelligence Engine.
- The Engine **must not** depend on the Studio.
- The Engine **must remain independent of transport mechanisms** — no FastAPI
  routing, no HTTP request/response objects. It accepts Python inputs/state and
  returns structured results.

The Engine's only permitted dependencies are LangGraph/LangChain, the LLM client
abstraction, and pure-Python parsing libraries. `CourseProcessorGraph` is the
single public entry point into the Engine.

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

### Orchestrator

`CourseProcessorGraph` (`graph/processor_graph.py`) is the single public API:

- Owns LLM creation (routes by `llm_provider`: ollama / azure / litellm / mock)
- Compiles the LangGraph state machine
- `process(source_path, learning_objectives)` — single invoke
- `process_with_progress(source_path, learning_objectives, on_step)` — dual-mode streaming with per-node callback

Ready to dive deeper? See [System Components](#components) or
[API Reference](#api-reference).
