"""OpenAI-compatible LLM client (Ollama Cloud, OpenAI, etc.)."""

from typing import Any, Optional

from .base_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """Client for any OpenAI-compatible endpoint (Ollama Cloud, OpenAI, etc.)."""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url=f"{self.base_url}/v1" if self.base_url else None,
            api_key=self.kwargs.get("api_key", ""),
            model=self.model,
            temperature=self.kwargs.get("temperature", 0),
            max_tokens=self.kwargs.get("max_tokens", 8192),
        )

    def validate_model(self) -> bool:
        # Accept any model string for OpenAI-compatible endpoints
        return True
