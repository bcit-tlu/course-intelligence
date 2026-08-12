"""Content Extractor agent — detects file format and extracts raw text.

This is a pure-Python node (no LLM). It delegates to the dataflows
parsers and normalises the result into raw_text on the graph state.
"""

from __future__ import annotations

from course_intelligence.agents.utils.agent_states import AgentState


def create_content_extractor():
    """Factory: create a content extractor graph node.

    No LLM is needed — this node handles format detection and text
    extraction only.
    """

    def content_extractor_node(state: AgentState) -> dict:
        """Extract text from the source file and store it in raw_text."""
        from course_intelligence.dataflows import parse_document

        return parse_document(state)

    return content_extractor_node
