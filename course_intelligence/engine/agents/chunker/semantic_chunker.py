"""Semantic Chunker agent — splits text into Atomic Knowledge Units."""

from __future__ import annotations

import logging
import time
import uuid

from course_intelligence.engine.agents.utils.agent_states import AgentState, KnowledgeChunk
from course_intelligence.engine.agents.utils.json_parsing import parse_llm_json
from course_intelligence.engine.agents.utils.llm_retry import invoke_with_retry
from course_intelligence.engine.graph.progress_context import report_progress

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert content analyst across all academic and professional
disciplines. Given the full text of a course module, split the text into
self-contained "Atomic Knowledge Units".

Each unit must:
1. Cover exactly ONE concept, procedure, or fact.
2. Be understandable without the surrounding context.
3. Have a short descriptive topic title.

Return your answer as a JSON array of objects with keys "topic" and "content".
Example:
[
  {{"topic": "Newton's Second Law", "content": "Force equals mass times acceleration..."}},
  {{"topic": "Supply and Demand Equilibrium", "content": "The equilibrium price occurs where..."}}
]

Return ONLY the JSON array. No markdown fences, no explanation.
"""


def _chunk_text(llm, text: str) -> list[KnowledgeChunk] | None:
    """Run one chunking LLM call over a block of text.

    Returns None on parse failure or transient LLM errors so the caller
    can record the page as failed and continue with remaining pages.
    """
    try:
        response = invoke_with_retry(llm, [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ], caller="chunker")
    except Exception:
        return None

    chunks_raw = parse_llm_json(response.content)
    if chunks_raw is None:
        return None

    return [
        KnowledgeChunk(
            chunk_id=str(uuid.uuid4())[:8],
            topic=item.get("topic", "Untitled"),
            content=item.get("content", ""),
        )
        for item in chunks_raw
    ]


def create_semantic_chunker(llm):
    """Factory: create a semantic chunker node that captures the given LLM.

    Chunks page-by-page when a course_module is available (keeps each
    LLM call within a manageable context size). Falls back to a single
    call over raw_text for plain inputs.
    """

    def semantic_chunker_node(state: AgentState) -> dict:
        """Chunk content into knowledge_map entries."""
        course_module = state.get("course_module")
        knowledge_map: list[KnowledgeChunk] = []
        failed_pages: list[str] = []

        if course_module and course_module.get("pages"):
            # Chunk each page separately — one LLM call per page
            n_pages = len(course_module["pages"])
            for i, page in enumerate(course_module["pages"], 1):
                if not page["text"].strip():
                    continue
                report_progress("chunking", i, n_pages, "pages")
                page_input = f"# {page['title']}\n\n{page['text']}"
                t0 = time.perf_counter()
                chunks = _chunk_text(llm, page_input)
                page_elapsed = time.perf_counter() - t0
                n_chunks = len(chunks) if chunks else 0
                logger.info(
                    "[chunker] page %d/%d \"%s\": %.1fs, %d chunks",
                    i, n_pages, page["title"][:60], page_elapsed, n_chunks,
                )
                if chunks is None:
                    failed_pages.append(page["title"])
                    continue
                for chunk in chunks:
                    chunk["source_page"] = page["title"]
                    chunk["page_number"] = page["page_number"]
                knowledge_map.extend(chunks)
        else:
            # Fallback: single call over raw_text
            raw = state.get("raw_text", "")
            chunks = _chunk_text(llm, raw)
            if chunks is None:
                return {"knowledge_map": [], "error": "Chunker returned invalid JSON"}
            knowledge_map = chunks

        result: dict = {"knowledge_map": knowledge_map}
        if failed_pages:
            result["error"] = (
                f"Chunker failed on {len(failed_pages)} page(s): "
                + ", ".join(failed_pages[:5])
            )
        return result

    return semantic_chunker_node
