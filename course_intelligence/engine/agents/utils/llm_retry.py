"""Retry wrapper for LLM invoke calls.

Handles transient errors from local LLM servers (e.g. LM Studio
peg-gemma4 format parsing failures) by retrying with exponential backoff.
Also provides per-call observability: timing, token counts (including
reasoning tokens), and retry tracking.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2


def _extract_usage(result: Any) -> dict:
    """Extract token usage from a LangChain AIMessage-like response."""
    usage = {}
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        usage = {
            "input_tokens": result.usage_metadata.get("input_tokens", 0),
            "output_tokens": result.usage_metadata.get("output_tokens", 0),
            "total_tokens": result.usage_metadata.get("total_tokens", 0),
        }
        reasoning = result.usage_metadata.get("output_tokens_details", {}).get("reasoning_tokens", 0)
        if reasoning:
            usage["reasoning_tokens"] = reasoning
    elif hasattr(result, "response_metadata") and result.response_metadata:
        meta = result.response_metadata
        token_usage = meta.get("token_usage") or meta.get("usage", {})
        if token_usage:
            usage = {
                "input_tokens": token_usage.get("prompt_tokens", token_usage.get("input_tokens", 0)),
                "output_tokens": token_usage.get("completion_tokens", token_usage.get("output_tokens", 0)),
                "total_tokens": token_usage.get("total_tokens", 0),
            }
            reasoning = (
                token_usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0)
                or token_usage.get("reasoning_tokens", 0)
            )
            if reasoning:
                usage["reasoning_tokens"] = reasoning
    return usage


def _model_name(llm: Any) -> str:
    return getattr(llm, "model_name", "") or getattr(llm, "model", "unknown")


def invoke_with_retry(
    llm: Any,
    messages: Any,
    max_retries: int = MAX_RETRIES,
    caller: str = "",
) -> Any:
    """Call llm.invoke(messages) with retry on transient errors.

    Some local models (e.g. Gemma 4 thinking models via LM Studio)
    intermittently produce output that the server cannot parse, resulting
    in HTTP 400/500 errors. Retrying typically succeeds because the model
    generates different output on the next attempt.

    Args:
        llm: The LangChain LLM instance.
        messages: Messages list to pass to invoke().
        max_retries: Maximum number of attempts.
        caller: Optional label for logging (e.g. "chunker", "classifier").
    """
    model = _model_name(llm)
    tag = f"[{caller}]" if caller else ""
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        t0 = time.perf_counter()
        try:
            result = llm.invoke(messages)
            elapsed = time.perf_counter() - t0
            usage = _extract_usage(result)

            parts = [f"{tag} model={model} elapsed={elapsed:.1f}s"]
            if usage:
                parts.append(f"tokens: {usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out")
                if usage.get("reasoning_tokens"):
                    parts.append(f"({usage['reasoning_tokens']} reasoning)")
                parts.append(f"= {usage.get('total_tokens', 0)} total")
            else:
                content_len = len(result.content) if hasattr(result, "content") else 0
                parts.append(f"response={content_len} chars (no usage metadata)")

            if attempt > 1:
                parts.append(f"(succeeded on attempt {attempt}/{max_retries})")

            logger.info("  ".join(parts))
            return result

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            last_exc = exc
            if attempt < max_retries:
                backoff = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "%s model=%s invoke failed (attempt %d/%d, %.1fs): %s — retrying in %ds",
                    tag, model, attempt, max_retries, elapsed, exc, backoff,
                )
                time.sleep(backoff)
            else:
                logger.error(
                    "%s model=%s invoke failed after %d attempts (%.1fs total): %s",
                    tag, model, max_retries, elapsed, exc,
                )
    raise last_exc  # type: ignore[misc]
