"""CourseProcessorGraph — the single public API for the processing pipeline.

Inspired by TradingAgents' TradingAgentsGraph: owns LLM creation, config,
graph compilation, and the process() entry point. Consumers never touch
LangGraph directly.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.llm.clients import create_llm_client
from .propagation import Propagator
from .setup import GraphSetup

logger = logging.getLogger(__name__)


class CourseProcessorGraph:
    """Main orchestrator for the course processing pipeline."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        debug: bool = False,
    ):
        """Initialize the processing graph and components.

        Args:
            config: Configuration dictionary. If None, uses DEFAULT_CONFIG.
            debug: Whether to stream node-by-node output for debugging.
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        # Initialize LLM via the client abstraction
        provider = self.config.get("llm_provider", "ollama")
        mock = self.config.get("mock_llm", False)

        max_tokens = self.config.get("llm_max_tokens", 8192)

        if provider == "azure" and not mock:
            client = create_llm_client(
                provider="azure",
                model=self.config["azure_openai_deployment"],
                base_url=self.config.get("azure_openai_endpoint"),
                api_key=self.config.get("azure_openai_api_key", ""),
                api_version=self.config.get("azure_openai_api_version", "2024-06-01"),
                max_tokens=max_tokens,
            )
        elif provider == "litellm" and not mock:
            client = create_llm_client(
                provider="litellm",
                model=self.config.get("litellm_model", "default-fast"),
                base_url=self.config.get("litellm_base_url"),
                api_key=self.config.get("litellm_api_key", ""),
                max_tokens=max_tokens,
            )
        else:
            client = create_llm_client(
                provider=provider,
                model=self.config.get("ollama_model", "gemma4:31b-cloud"),
                base_url=self.config.get("ollama_base_url"),
                mock=mock,
                api_key=self.config.get("ollama_api_key", ""),
                max_tokens=max_tokens,
            )
        self.llm = client.get_llm()

        # Build the graph
        self.graph_setup = GraphSetup(self.llm)
        self.propagator = Propagator()

        workflow = self.graph_setup.setup_graph()
        self.graph = workflow.compile()

    def process(
        self, source_path: str, learning_objectives: str = ""
    ) -> Dict[str, Any]:
        """Process a document through the full pipeline.

        This is the single public entry point — upload a file path,
        get back structured results.

        Args:
            source_path: Path to the uploaded file or directory.
            learning_objectives: Instructor-provided objectives string.

        Returns:
            Final graph state dict with knowledge_map and error.
        """
        initial_state = self.propagator.create_initial_state(
            source_path, learning_objectives
        )

        if self.debug:
            for chunk in self.graph.stream(initial_state, stream_mode="values"):
                logger.info("Graph step: %s", list(chunk.keys()))
            return chunk  # last chunk is the final state
        else:
            return self.graph.invoke(initial_state)

    def process_with_progress(
        self,
        source_path: str,
        learning_objectives: str = "",
        on_step: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Process a document, calling *on_step* after each graph node.

        Uses LangGraph dual-mode streaming (updates + values) to get both
        the node name (for progress tracking) and the full final state.

        Args:
            source_path: Path to the uploaded file or directory.
            learning_objectives: Instructor-provided objectives string.
            on_step: Optional callback invoked with the node name after
                each node completes (e.g. ``on_step("extract")``).

        Returns:
            Final graph state dict — same shape as ``process()``.
        """
        initial_state = self.propagator.create_initial_state(
            source_path, learning_objectives
        )
        final_state = None
        for mode, chunk in self.graph.stream(
            initial_state, stream_mode=["updates", "values"]
        ):
            if mode == "updates":
                for node_name in chunk:
                    if not node_name.startswith("__") and on_step is not None:
                        on_step(node_name)
            elif mode == "values":
                final_state = chunk
        return final_state if final_state is not None else initial_state
