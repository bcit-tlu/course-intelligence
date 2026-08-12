"""Shared helpers for parsing LLM JSON responses."""

from __future__ import annotations

import json


def parse_llm_json(content: str) -> list | None:
    """Parse an LLM's JSON array response, tolerating markdown fences."""
    text = content.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        result = json.loads(text.strip())
        return result if isinstance(result, list) else None
    except json.JSONDecodeError:
        return None
