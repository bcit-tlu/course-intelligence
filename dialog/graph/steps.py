"""Canonical mapping from LangGraph node names to progress step labels.

Kept in one place so adding/reordering pipeline nodes only requires a
one-line change here (and a mirror update in the frontend STEPS list).
"""

NODE_TO_STEP: dict[str, str] = {
    "extract": "extracting",
    "chunk": "chunking",
    "classify": "classifying",
}

STEP_ORDER: list[str] = ["extracting", "chunking", "classifying"]
