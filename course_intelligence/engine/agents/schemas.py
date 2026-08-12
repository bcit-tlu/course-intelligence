"""Pydantic schemas for structured LLM outputs and their render helpers.

Each agent that produces structured output has a corresponding schema here.
Render helpers convert parsed Pydantic instances back into markdown / plain
text that the rest of the system can consume unchanged.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Semantic Chunker
# ---------------------------------------------------------------------------


class ChunkOutput(BaseModel):
    """A single atomic knowledge unit extracted from course material."""

    topic: str = Field(description="Short descriptive title for the chunk.")
    content: str = Field(description="Self-contained explanation of one concept, procedure, or fact.")


def render_chunk(chunk: ChunkOutput) -> str:
    return f"**{chunk.topic}**\n\n{chunk.content}"
