"""Graph construction — wires nodes and edges, no agent logic here."""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from course_intelligence.engine.agents.utils.agent_states import AgentState
from course_intelligence.engine.agents import (
    create_blooms_classifier,
    create_content_extractor,
    create_semantic_chunker,
)


class GraphSetup:
    """Handles the setup and configuration of the processing graph."""

    def __init__(self, llm: Any):
        """Initialize with the LLM instance used by all agent factories."""
        self.llm = llm

    def setup_graph(self) -> StateGraph:
        """Build and return the workflow (uncompiled).

        Pipeline: extract → chunk → classify → END
        """
        workflow = StateGraph(AgentState)

        # Create agent nodes via factories
        extractor_node = create_content_extractor()
        chunker_node = create_semantic_chunker(self.llm)
        classifier_node = create_blooms_classifier(self.llm)

        # Register nodes
        workflow.add_node("extract", extractor_node)
        workflow.add_node("chunk", chunker_node)
        workflow.add_node("classify", classifier_node)

        # Wire edges
        workflow.set_entry_point("extract")
        workflow.add_edge("extract", "chunk")
        workflow.add_edge("chunk", "classify")
        workflow.add_edge("classify", END)

        return workflow
