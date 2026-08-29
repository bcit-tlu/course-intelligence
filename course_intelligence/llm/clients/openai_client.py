"""OpenAI-compatible LLM client (Ollama Cloud, OpenAI, etc.)."""

from typing import Any, Optional

from .base_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """Client for any OpenAI-compatible endpoint (Ollama Cloud, OpenAI, etc.)."""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        from langchain_openai import ChatOpenAI

        base_url = self.base_url
        if base_url and not base_url.rstrip("/").endswith("/v1"):
            base_url = f"{base_url.rstrip('/')}/v1"

        model_kwargs = {}
        reasoning_effort = self.kwargs.get("reasoning_effort")
        if reasoning_effort:
            model_kwargs["reasoning_effort"] = reasoning_effort

        return ChatOpenAI(
            base_url=base_url or None,
            api_key=self.kwargs.get("api_key", ""),
            model=self.model,
            temperature=self.kwargs.get("temperature", 0),
            max_tokens=self.kwargs.get("max_tokens", 8192),
            max_retries=0,
            model_kwargs=model_kwargs,
        )

    def validate_model(self) -> bool:
        # Accept any model string for OpenAI-compatible endpoints
        return True
