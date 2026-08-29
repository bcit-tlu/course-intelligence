"""LLM client factory — dispatches to the correct provider client.

Modules are imported lazily so that importing this factory does not
pull in heavy LLM SDKs or fail when API keys are absent.
"""

from typing import Any, Optional

from .base_client import BaseLLMClient


def create_llm_client(
    provider: str = "ollama",
    model: str = "gemma4:31b-cloud",
    base_url: Optional[str] = None,
    mock: bool = False,
    **kwargs,
) -> BaseLLMClient:
    """Create an LLM client for the specified provider.

    Args:
        provider: LLM provider name ("ollama", "lmstudio", "azure", "openai",
                  "litellm", "mock")
        model: Model name / identifier (or Azure deployment name)
        base_url: Optional base URL for the API endpoint
        mock: If True, return a MockClient regardless of provider
        **kwargs: Additional provider-specific arguments:
            - api_key: API key for the provider
            - temperature: Sampling temperature
            - api_version: Azure OpenAI API version (azure only)

    Returns:
        Configured BaseLLMClient instance
    """
    if mock:
        from .mock_client import MockClient
        return MockClient(model, base_url, **kwargs)

    provider_lower = provider.lower()

    if provider_lower in ("openai", "ollama", "lmstudio", "litellm"):
        from .openai_client import OpenAIClient
        return OpenAIClient(model, base_url, **kwargs)

    if provider_lower == "azure":
        from .azure_client import AzureOpenAIClient
        return AzureOpenAIClient(model, base_url, **kwargs)

    raise ValueError(f"Unsupported LLM provider: {provider}")


_PROVIDER_REQUIRED_KEYS: dict[str, list[str]] = {
    "azure": ["azure_openai_endpoint", "azure_openai_api_key", "azure_openai_deployment"],
    "openai": ["openai_api_key"],
    "litellm": ["litellm_base_url", "litellm_api_key"],
}


def _validate_provider_config(provider: str, config: dict) -> None:
    """Fail fast if required config keys are missing for the chosen provider."""
    required = _PROVIDER_REQUIRED_KEYS.get(provider, [])
    missing = [k for k in required if not config.get(k)]
    if missing:
        env_hints = {
            "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
            "azure_openai_api_key": "AZURE_OPENAI_API_KEY",
            "azure_openai_deployment": "AZURE_OPENAI_DEPLOYMENT",
            "openai_api_key": "OPENAI_API_KEY",
            "litellm_base_url": "LITELLM_API_BASE",
            "litellm_api_key": "LITELLM_API_KEY",
        }
        hints = ", ".join(env_hints.get(k, k) for k in missing)
        raise ValueError(
            f"LLM provider '{provider}' requires config keys: {missing}. "
            f"Set env vars: {hints}"
        )


def build_llm_from_config(config: dict) -> Any:
    """Build a LangChain LLM instance from a config dict.

    Centralizes provider selection so gateway.py and processor_graph.py
    don't duplicate the same if/elif/else logic. Validates required
    config keys at init time for fail-fast behavior.
    """
    provider = config.get("llm_provider", "ollama")
    mock = config.get("mock_llm", False)
    max_tokens = config.get("llm_max_tokens", 8192)

    if not mock:
        _validate_provider_config(provider, config)

    if provider == "azure" and not mock:
        client = create_llm_client(
            provider="azure",
            model=config["azure_openai_deployment"],
            base_url=config.get("azure_openai_endpoint"),
            api_key=config.get("azure_openai_api_key", ""),
            api_version=config.get("azure_openai_api_version", "2024-06-01"),
            max_tokens=max_tokens,
        )
    elif provider == "litellm" and not mock:
        client = create_llm_client(
            provider="litellm",
            model=config.get("litellm_model", "default-fast"),
            base_url=config.get("litellm_base_url"),
            api_key=config.get("litellm_api_key", ""),
            max_tokens=max_tokens,
        )
    elif provider == "lmstudio" and not mock:
        client = create_llm_client(
            provider="lmstudio",
            model=config.get("lmstudio_model", "local-model"),
            base_url=config.get("lmstudio_base_url"),
            api_key="lm-studio",
            max_tokens=max_tokens,
            reasoning_effort=config.get("lmstudio_reasoning_effort", "none"),
        )
    elif provider == "openai" and not mock:
        client = create_llm_client(
            provider="openai",
            model=config.get("openai_model", "gpt-4o"),
            base_url=config.get("openai_base_url") or None,
            api_key=config.get("openai_api_key", ""),
            max_tokens=max_tokens,
        )
    else:
        client = create_llm_client(
            provider=provider,
            model=config.get("ollama_model", "gemma4:31b-cloud"),
            base_url=config.get("ollama_base_url"),
            mock=mock,
            api_key=config.get("ollama_api_key", ""),
            max_tokens=max_tokens,
        )

    client.validate_model()
    return client.get_llm()
