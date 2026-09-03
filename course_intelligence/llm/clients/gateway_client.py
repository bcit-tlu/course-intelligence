"""LLM client that routes calls through the CI LLM gateway."""

import logging
from typing import Any

import httpx
from langchain_core.messages import AIMessage

from .base_client import BaseLLMClient

logger = logging.getLogger(__name__)


class GatewayLLMClient(BaseLLMClient):
    """Calls the CI LLM gateway's /v1/complete endpoint.

    Used by the worker and API so all LLM traffic flows through the
    gateway, which records ci_llm_* metrics and analytics events.
    """

    def __init__(self, gateway_url: str, **kwargs):
        super().__init__(model="gateway", base_url=gateway_url, **kwargs)
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = kwargs.get("request_timeout", 180)

    def get_llm(self) -> Any:
        """Return self — this client IS the LLM interface.

        Unlike other clients that return a LangChain ChatModel, this
        client is directly callable via .invoke() since it translates
        messages to HTTP calls.
        """
        return self

    def validate_model(self) -> bool:
        return True

    def invoke(self, messages: Any) -> AIMessage:
        """Send messages to the gateway and return an AIMessage.

        Accepts the same message formats as ChatOpenAI.invoke():
        - List of dicts: [{"role": "system", "content": "..."}, ...]
        - List of LangChain message objects
        """
        normalized = []
        for msg in messages:
            if isinstance(msg, dict):
                normalized.append({"role": msg.get("role", "user"),
                                   "content": msg.get("content", "")})
            elif hasattr(msg, "type") and hasattr(msg, "content"):
                normalized.append({"role": msg.type, "content": msg.content})
            else:
                normalized.append({"role": "user", "content": str(msg)})

        resp = httpx.post(
            f"{self.gateway_url}/v1/complete",
            json={"messages": normalized,
                  "temperature": self.kwargs.get("temperature", 0),
                  "max_tokens": self.kwargs.get("max_tokens", 8192)},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        usage = data.get("usage", {})
        return AIMessage(
            content=data["content"],
            usage_metadata={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            } if usage else None,
        )
