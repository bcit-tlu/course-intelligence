"""Single source of truth for configuration with env-var overlay.

Inspired by TradingAgents' default_config.py — a plain dict that applies
environment variable overrides at import time. No pydantic-settings needed.
"""

import os

_ENV_OVERRIDES = {
    # LLM provider selection
    "LLM_PROVIDER":       "llm_provider",

    # Ollama (local or cloud)
    "OLLAMA_BASE_URL":    "ollama_base_url",
    "OLLAMA_API_KEY":     "ollama_api_key",
    "OLLAMA_MODEL":       "ollama_model",

    # LM Studio (local)
    "LMSTUDIO_BASE_URL":     "lmstudio_base_url",
    "LMSTUDIO_MODEL":        "lmstudio_model",
    "LMSTUDIO_REASONING_EFFORT": "lmstudio_reasoning_effort",

    # OpenAI (cloud)
    "OPENAI_BASE_URL":    "openai_base_url",
    "OPENAI_API_KEY":     "openai_api_key",
    "OPENAI_MODEL":       "openai_model",

    # Azure OpenAI (pilot/prod)
    "AZURE_OPENAI_ENDPOINT":    "azure_openai_endpoint",
    "AZURE_OPENAI_API_KEY":     "azure_openai_api_key",
    "AZURE_OPENAI_API_VERSION": "azure_openai_api_version",
    "AZURE_OPENAI_DEPLOYMENT":  "azure_openai_deployment",

    # LiteLLM gateway (OpenAI-compatible proxy)
    "LITELLM_API_BASE":  "litellm_base_url",
    "LITELLM_API_KEY":   "litellm_api_key",
    "LITELLM_MODEL":     "litellm_model",

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
    "LLM_MAX_TOKENS":     "llm_max_tokens",
    "LLM_REQUEST_TIMEOUT_S": "llm_request_timeout_s",

    # Upload retention
    "RETENTION_COUNT":    "retention_count",

    # Job timeout & watchdog
    "JOB_TIMEOUT_S":              "job_timeout_s",
    "WATCHDOG_INTERVAL_S":        "watchdog_interval_s",
    "WATCHDOG_STALE_THRESHOLD_S": "watchdog_stale_threshold_s",

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
    # LLM provider: "ollama" (local/cloud), "lmstudio" (local), "azure" (prod),
    # "litellm" (proxy), "openai" (cloud), "mock" (testing)
    "llm_provider": "ollama",

    # Ollama settings (local: http://localhost:11434, cloud: https://ollama.com)
    "ollama_base_url": "https://ollama.com",
    "ollama_api_key": "",
    "ollama_model": "gemma4:31b-cloud",

    # LM Studio settings (local only — no API key needed)
    "lmstudio_base_url": "http://localhost:1234/v1",
    "lmstudio_model": "local-model",
    # Reasoning effort: "none" (Gemma 4), "low"/"medium"/"high"/"xhigh" (Muse Glimmer),
    # or "" to omit the parameter entirely
    "lmstudio_reasoning_effort": "none",

    # Azure OpenAI settings (pilot/prod)
    "azure_openai_endpoint": "",       # e.g. https://myinstance.openai.azure.com
    "azure_openai_api_key": "",
    "azure_openai_api_version": "2024-06-01",
    "azure_openai_deployment": "",     # chat model deployment name

    # OpenAI (cloud)
    "openai_base_url": "",             # leave empty for api.openai.com default
    "openai_api_key": "",
    "openai_model": "gpt-4o",

    # LiteLLM gateway (OpenAI-compatible proxy)
    "litellm_base_url": "",            # e.g. http://litellm.llm-gateway.svc.cluster.local:4000
    "litellm_api_key": "",
    "litellm_model": "default-fast",

    # LLM gateway — internal proxy that centralizes all LLM calls
    "llm_gateway_url": "",             # e.g. http://llm-gateway:8100

    # Infrastructure
    "database_url": "",                # e.g. postgresql://course_intelligence:course_intelligence@db:5432/course_intelligence
    "redis_url": "",                   # e.g. redis://redis:6379/0
    "s3_endpoint_url": "",             # e.g. http://minio:9000
    "s3_access_key": "",
    "s3_secret_key": "",
    "s3_bucket": "uploads",

    # LLM output token limit — prevents truncated JSON responses
    "llm_max_tokens": 8192,

    # Per-request HTTP timeout for LLM calls (seconds). Ensures a hung
    # LLM server returns control to Python so signal.alarm can fire.
    # Must be < job_timeout_s / max_retries (3) to stay within budget.
    "llm_request_timeout_s": 180,

    # Mock mode — run the graph without real LLM calls
    "mock_llm": False,

    # API server
    "api_host": "0.0.0.0",
    "api_port": 8000,

    # Upload retention — number of recent job uploads to keep in S3
    "retention_count": 10,

    # Job timeout — max seconds a single job may run before being killed
    "job_timeout_s": 600,

    # Watchdog — interval (s) between stale-job checks, and threshold (s)
    # for how long a job can stay in "processing" with no updated_at
    # heartbeat before being marked failed.  Must be > job_timeout_s and
    # should exceed the longest expected single pipeline step.
    "watchdog_interval_s": 60,
    "watchdog_stale_threshold_s": 900,

    # Enable uvicorn auto-reload (dev only). Must stay False in production/containers.
    "dev_reload": False,
})
