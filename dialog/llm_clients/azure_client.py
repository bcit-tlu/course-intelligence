"""Azure OpenAI LLM client."""

from typing import Any, Optional

from .base_client import BaseLLMClient


class AzureOpenAIClient(BaseLLMClient):
    """Client for Azure OpenAI Service."""

    def __init__(self, model: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, base_url, **kwargs)

    def get_llm(self) -> Any:
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=self.base_url or "",
            api_key=self.kwargs.get("api_key", ""),
            api_version=self.kwargs.get("api_version", "2024-06-01"),
            azure_deployment=self.model,
            temperature=self.kwargs.get("temperature", 0),
            max_tokens=self.kwargs.get("max_tokens", 8192),
        )

    def validate_model(self) -> bool:
        return bool(self.model and self.base_url)
