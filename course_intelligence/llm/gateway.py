"""LLM Gateway — thin proxy that centralizes all LLM calls.

Purpose (from hybrid architecture plan):
- Centralize Azure OpenAI / Ollama calls in one service
- Manage retries and rate limits
- Log token usage and estimate cost
- Keep API keys out of workers (only the gateway needs credentials)
- Make it easy to switch providers without touching workers

Workers and API call the gateway instead of calling the LLM directly.
The gateway forwards requests to the configured LLM provider.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.llm.clients import create_llm_client

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Gateway",
    version="0.1.0",
    description="Internal proxy for LLM calls — centralizes credentials, logging, and retries.",
)

# --- Request / Response models ---


class CompletionRequest(BaseModel):
    """A chat completion request forwarded from workers."""
    messages: list[dict[str, str]]
    temperature: float = 0.0
    max_tokens: int | None = None


class CompletionResponse(BaseModel):
    """Response from the gateway including usage metadata."""
    content: str
    model: str
    usage: dict[str, int]
    latency_ms: int


# --- Stats ---

_stats: dict[str, Any] = {
    "total_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "errors": 0,
}


# --- LLM client (initialized lazily on first request) ---

_llm = None


def _get_llm():
    """Lazily initialize the LLM client from config."""
    global _llm
    if _llm is not None:
        return _llm

    provider = DEFAULT_CONFIG.get("llm_provider", "ollama")
    mock = DEFAULT_CONFIG.get("mock_llm", False)

    if provider == "azure" and not mock:
        client = create_llm_client(
            provider="azure",
            model=DEFAULT_CONFIG["azure_openai_deployment"],
            base_url=DEFAULT_CONFIG.get("azure_openai_endpoint"),
            api_key=DEFAULT_CONFIG.get("azure_openai_api_key", ""),
            api_version=DEFAULT_CONFIG.get("azure_openai_api_version", "2024-06-01"),
        )
    else:
        client = create_llm_client(
            provider=provider,
            model=DEFAULT_CONFIG.get("ollama_model", "gemma4:31b-cloud"),
            base_url=DEFAULT_CONFIG.get("ollama_base_url"),
            mock=mock,
            api_key=DEFAULT_CONFIG.get("ollama_api_key", ""),
        )

    _llm = client.get_llm()
    logger.info("LLM Gateway initialized with provider=%s", provider)
    return _llm


# --- Endpoints ---


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "provider": DEFAULT_CONFIG.get("llm_provider", "ollama"),
        "stats": _stats,
    }


@app.post("/v1/complete", response_model=CompletionResponse)
async def complete(request: CompletionRequest):
    """Forward a chat completion request to the configured LLM.

    Workers call this endpoint instead of calling the LLM directly.
    """
    llm = _get_llm()
    _stats["total_requests"] += 1

    start = time.perf_counter()
    try:
        from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

        messages = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                messages.append(SystemMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        result = llm.invoke(messages)
        latency_ms = int((time.perf_counter() - start) * 1000)

        # Extract usage if available
        usage = {}
        if hasattr(result, "usage_metadata") and result.usage_metadata:
            usage = {
                "input_tokens": result.usage_metadata.get("input_tokens", 0),
                "output_tokens": result.usage_metadata.get("output_tokens", 0),
                "total_tokens": result.usage_metadata.get("total_tokens", 0),
            }
            _stats["total_input_tokens"] += usage.get("input_tokens", 0)
            _stats["total_output_tokens"] += usage.get("output_tokens", 0)

        content = result.content if hasattr(result, "content") else str(result)
        model_name = getattr(llm, "model_name", "") or getattr(llm, "model", "unknown")

        return CompletionResponse(
            content=content,
            model=model_name,
            usage=usage,
            latency_ms=latency_ms,
        )

    except Exception as e:
        _stats["errors"] += 1
        logger.error("LLM completion failed: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")


@app.get("/v1/stats")
async def stats():
    """Return cumulative token usage and request stats."""
    return _stats
