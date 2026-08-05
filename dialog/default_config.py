"""Single source of truth for configuration with env-var overlay.

Inspired by TradingAgents' default_config.py — a plain dict that applies
environment variable overrides at import time. No pydantic-settings needed.
"""

import os

_ENV_OVERRIDES = {
    # LLM provider selection
    "LLM_PROVIDER":       "llm_provider",

    # Ollama (dev)
    "OLLAMA_BASE_URL":    "ollama_base_url",
    "OLLAMA_API_KEY":     "ollama_api_key",
    "OLLAMA_MODEL":       "ollama_model",

    # Azure OpenAI (pilot/prod)
    "AZURE_OPENAI_ENDPOINT":    "azure_openai_endpoint",
    "AZURE_OPENAI_API_KEY":     "azure_openai_api_key",
    "AZURE_OPENAI_API_VERSION": "azure_openai_api_version",
    "AZURE_OPENAI_DEPLOYMENT":  "azure_openai_deployment",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "azure_openai_embedding_deployment",

    # LLM gateway
    "LLM_GATEWAY_URL":   "llm_gateway_url",

    # Infrastructure
    "DATABASE_URL":       "database_url",
    "REDIS_URL":          "redis_url",
    "S3_ENDPOINT_URL":    "s3_endpoint_url",
    "S3_ACCESS_KEY":      "s3_access_key",
    "S3_SECRET_KEY":      "s3_secret_key",
    "S3_BUCKET":          "s3_bucket",

    # Processing
    "MOCK_LLM":           "mock_llm",
    "MAX_CHUNK_TOKENS":   "max_chunk_tokens",
    "MIN_CHUNK_TOKENS":   "min_chunk_tokens",
    "LLM_MAX_TOKENS":     "llm_max_tokens",

    # API server
    "API_HOST":           "api_host",
    "API_PORT":           "api_port",
    "DEV_RELOAD":         "dev_reload",
}


def _coerce(value: str, reference):
    """Coerce env-var string to the type of the existing default value."""
    if isinstance(reference, bool):
        return value.strip().lower() in ("true", "1", "yes", "on")
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: dict) -> dict:
    """Apply env vars to the config dict in-place."""
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        config[key] = _coerce(raw, config.get(key))
    return config


DEFAULT_CONFIG = _apply_env_overrides({
    # LLM provider: "ollama" (dev), "azure" (pilot/prod), "mock" (testing)
    "llm_provider": "ollama",

    # Ollama settings (dev default)
    "ollama_base_url": "https://ollama.com",
    "ollama_api_key": "",
    "ollama_model": "gemma4:31b-cloud",

    # Azure OpenAI settings (pilot/prod)
    "azure_openai_endpoint": "",       # e.g. https://myinstance.openai.azure.com
    "azure_openai_api_key": "",
    "azure_openai_api_version": "2024-06-01",
    "azure_openai_deployment": "",     # chat model deployment name
    "azure_openai_embedding_deployment": "",  # embedding model deployment name

    # LLM gateway — internal proxy that centralizes all LLM calls
    "llm_gateway_url": "",             # e.g. http://llm-gateway:8100

    # Infrastructure
    "database_url": "",                # e.g. postgresql://dialog:dialog@db:5432/dialog
    "redis_url": "",                   # e.g. redis://redis:6379/0
    "s3_endpoint_url": "",             # e.g. http://minio:9000
    "s3_access_key": "",
    "s3_secret_key": "",
    "s3_bucket": "uploads",

    # Processing defaults
    "max_chunk_tokens": 800,
    "min_chunk_tokens": 100,

    # LLM output token limit — prevents truncated JSON responses
    "llm_max_tokens": 8192,

    # Mock mode — run the graph without real LLM calls
    "mock_llm": False,

    # API server
    "api_host": "0.0.0.0",
    "api_port": 8000,

    # Enable uvicorn auto-reload (dev only). Must stay False in production/containers.
    "dev_reload": False,
})
