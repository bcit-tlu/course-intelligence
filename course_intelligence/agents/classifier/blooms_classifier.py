"""Bloom's Classifier agent — tags each knowledge chunk with a Bloom's
taxonomy level and a short rationale.

Classifies in batches to keep LLM call count low (one call per
BATCH_SIZE chunks, not one per chunk).
"""

from __future__ import annotations

import json
import logging

from course_intelligence.agents.utils.agent_states import AgentState, KnowledgeChunk
from course_intelligence.agents.utils.json_parsing import parse_llm_json

logger = logging.getLogger(__name__)

BATCH_SIZE = 10
UNCLASSIFIED = "unclassified"

BLOOMS_LEVELS = {
    "remember": "Remember",
    "understand": "Understand",
    "apply": "Apply",
    "analyze": "Analyze",
    "evaluate": "Evaluate",
    "create": "Create",
}

SYSTEM_PROMPT = """\
You are an instructional design expert. For each knowledge unit below,
assign the single most appropriate Bloom's taxonomy level based on the
cognitive demand of the content, plus a one-sentence rationale.

The levels are: Remember, Understand, Apply, Analyze, Evaluate, Create.

Return your answer as a JSON array with one object per knowledge unit,
in the SAME ORDER as the input, with keys "chunk_id", "blooms_level",
and "rationale". Example:
[
  {{"chunk_id": "a1b2c3d4", "blooms_level": "Understand", "rationale": "Requires explaining the concept of sepsis in own words."}},
  {{"chunk_id": "e5f6a7b8", "blooms_level": "Apply", "rationale": "Requires using the qSOFA score in a clinical scenario."}}
]

Return ONLY the JSON array. No markdown fences, no explanation.
"""


def _normalize_level(raw: str | None) -> str | None:
    """Map an LLM-provided level string to a canonical Bloom's level."""
    if not raw:
        return None
    return BLOOMS_LEVELS.get(raw.strip().lower())


def _classify_batch(llm, batch: list[KnowledgeChunk]) -> None:
    """Classify one batch of chunks in-place. Failures leave chunks
    unclassified rather than raising."""
    units = [
        {"chunk_id": c["chunk_id"], "topic": c["topic"], "content": c["content"]}
        for c in batch
    ]
    response = llm.invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(units, indent=2)},
    ])

    items = parse_llm_json(response.content)
    if items is None:
        logger.warning("Classifier returned invalid JSON for a batch of %d", len(batch))
        items = []

    # Prefer matching by chunk_id; fall back to position when the LLM
    # echoed different/missing ids but the counts line up.
    by_id = {
        item["chunk_id"]: item
        for item in items
        if isinstance(item, dict) and "chunk_id" in item
    }
    positional_ok = len(items) == len(batch)

    for i, chunk in enumerate(batch):
        item = by_id.get(chunk["chunk_id"])
        if item is None and positional_ok and isinstance(items[i], dict):
            item = items[i]

        level = _normalize_level(item.get("blooms_level")) if item else None
        if level is None:
            chunk["blooms_level"] = UNCLASSIFIED
            chunk["blooms_rationale"] = ""
        else:
            chunk["blooms_level"] = level
            chunk["blooms_rationale"] = item.get(
                "rationale", item.get("blooms_rationale", "")
            )


def create_blooms_classifier(llm):
    """Factory: create a Bloom's classifier node that captures the given LLM."""

    def blooms_classifier_node(state: AgentState) -> dict:
        """Tag every knowledge_map chunk with a Bloom's level."""
        knowledge_map = state.get("knowledge_map", [])
        if not knowledge_map:
            return {}

        for start in range(0, len(knowledge_map), BATCH_SIZE):
            batch = knowledge_map[start : start + BATCH_SIZE]
            try:
                _classify_batch(llm, batch)
            except Exception as e:
                # A failing batch must not fail the whole job
                logger.error("Classifier batch failed: %s", e)
                for chunk in batch:
                    chunk.setdefault("blooms_level", UNCLASSIFIED)
                    chunk.setdefault("blooms_rationale", "")

        n_unclassified = sum(
            1 for c in knowledge_map if c.get("blooms_level") == UNCLASSIFIED
        )
        if n_unclassified:
            logger.warning(
                "%d of %d chunks left unclassified",
                n_unclassified, len(knowledge_map),
            )
        return {"knowledge_map": knowledge_map}

    return blooms_classifier_node
