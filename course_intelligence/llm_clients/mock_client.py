"""Mock LLM client — deterministic responses for testing the graph flow."""

import json
from typing import Any, Optional

from .base_client import BaseLLMClient


class MockClient(BaseLLMClient):
    """Returns pre-canned responses via FakeListChatModel."""

    def __init__(self, model: str = "mock", base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        # One response shape serves both LLM nodes: the chunker reads
        # "topic"/"content" and ignores the rest; the classifier matches
        # positionally (2 items per batch) and reads "blooms_level"/
        # "rationale".
        combined_response = json.dumps([
            {
                "topic": "Mock Topic A",
                "content": "This is mock knowledge chunk A.",
                "blooms_level": "Understand",
                "rationale": "Mock rationale A.",
            },
            {
                "topic": "Mock Topic B",
                "content": "This is mock knowledge chunk B.",
                "blooms_level": "Apply",
                "rationale": "Mock rationale B.",
            },
        ])

        # FakeListChatModel cycles through responses in order.
        # Current pipeline: extract (no LLM) → chunk (≥1 call) →
        # classify (≥1 call) — the same response works for every call.
        return FakeListChatModel(
            responses=[
                combined_response,
            ]
        )

    def validate_model(self) -> bool:
        return True
