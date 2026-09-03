"""Contract tests for LLM provider dispatch via build_llm_from_config()."""

import pytest

from course_intelligence.llm.clients import create_llm_client
from course_intelligence.llm.clients.factory import build_llm_from_config, _validate_provider_config
from course_intelligence.llm.clients.openai_client import OpenAIClient
from course_intelligence.llm.clients.azure_client import AzureOpenAIClient
from course_intelligence.llm.clients.mock_client import MockClient


# --- Factory dispatch ---

def test_factory_returns_openai_client_for_ollama():
    client = create_llm_client(provider="ollama", model="test-model", base_url="http://localhost:11434")
    assert isinstance(client, OpenAIClient)


def test_factory_returns_openai_client_for_lmstudio():
    client = create_llm_client(provider="lmstudio", model="local-model", base_url="http://localhost:1234/v1")
    assert isinstance(client, OpenAIClient)


def test_factory_returns_openai_client_for_openai():
    client = create_llm_client(provider="openai", model="gpt-4o", base_url=None)
    assert isinstance(client, OpenAIClient)


def test_factory_returns_openai_client_for_litellm():
    client = create_llm_client(provider="litellm", model="default-fast", base_url="http://litellm:4000")
    assert isinstance(client, OpenAIClient)


def test_factory_returns_azure_client_for_azure():
    client = create_llm_client(provider="azure", model="deployment", base_url="https://example.openai.azure.com")
    assert isinstance(client, AzureOpenAIClient)


def test_factory_returns_mock_client_when_mock_true():
    client = create_llm_client(provider="ollama", model="test", mock=True)
    assert isinstance(client, MockClient)


def test_factory_raises_for_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_client(provider="nonexistent", model="test")


# --- build_llm_from_config dispatch ---

def _mock_config(**overrides):
    base = {
        "llm_provider": "ollama",
        "mock_llm": True,
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "test-model",
        "ollama_api_key": "",
        "lmstudio_base_url": "http://localhost:1234/v1",
        "lmstudio_model": "local-model",
        "openai_base_url": "",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
        "litellm_base_url": "http://litellm:4000",
        "litellm_api_key": "key",
        "litellm_model": "default-fast",
        "azure_openai_endpoint": "https://example.openai.azure.com",
        "azure_openai_api_key": "key",
        "azure_openai_api_version": "2024-06-01",
        "azure_openai_deployment": "deployment",
        "llm_max_tokens": 8192,
    }
    base.update(overrides)
    return base


def test_build_llm_from_config_mock_returns_fake_model():
    llm = build_llm_from_config(_mock_config(mock_llm=True))
    assert llm is not None


def test_build_llm_from_config_ollama_creates_chat_model():
    config = _mock_config(mock_llm=False, llm_provider="ollama", ollama_api_key="test-key")
    llm = build_llm_from_config(config)
    assert llm is not None
    assert llm.model_name == "test-model"


def test_build_llm_from_config_lmstudio_creates_chat_model():
    config = _mock_config(mock_llm=False, llm_provider="lmstudio")
    llm = build_llm_from_config(config)
    assert llm is not None
    assert llm.model_name == "local-model"


def test_build_llm_from_config_openai_creates_chat_model():
    config = _mock_config(mock_llm=False, llm_provider="openai", openai_api_key="sk-test")
    llm = build_llm_from_config(config)
    assert llm is not None
    assert llm.model_name == "gpt-4o"


def test_build_llm_from_config_litellm_creates_chat_model():
    config = _mock_config(mock_llm=False, llm_provider="litellm")
    llm = build_llm_from_config(config)
    assert llm is not None


def test_build_llm_from_config_azure_creates_chat_model():
    config = _mock_config(mock_llm=False, llm_provider="azure")
    llm = build_llm_from_config(config)
    assert llm is not None


# --- Config validation (fail-fast) ---

def test_validation_passes_for_ollama_no_keys():
    _validate_provider_config("ollama", {})


def test_validation_passes_for_lmstudio_no_keys():
    _validate_provider_config("lmstudio", {})


def test_validation_fails_for_azure_missing_endpoint():
    with pytest.raises(ValueError, match="azure"):
        _validate_provider_config("azure", {"azure_openai_api_key": "key", "azure_openai_deployment": "dep"})


def test_validation_fails_for_openai_missing_key():
    with pytest.raises(ValueError, match="openai"):
        _validate_provider_config("openai", {})


def test_validation_fails_for_litellm_missing_url():
    with pytest.raises(ValueError, match="litellm"):
        _validate_provider_config("litellm", {"litellm_api_key": "key"})


def test_build_llm_from_config_raises_on_missing_azure_config():
    config = _mock_config(mock_llm=False, llm_provider="azure")
    config["azure_openai_endpoint"] = ""
    config["azure_openai_api_key"] = ""
    config["azure_openai_deployment"] = ""
    with pytest.raises(ValueError, match="azure"):
        build_llm_from_config(config)


# --- /v1 URL handling ---

def test_openai_client_appends_v1_when_missing():
    client = OpenAIClient(model="test", base_url="http://localhost:11434", api_key="dummy")
    llm = client.get_llm()
    assert llm.openai_api_base == "http://localhost:11434/v1"


def test_openai_client_does_not_double_append_v1():
    client = OpenAIClient(model="test", base_url="http://localhost:1234/v1", api_key="dummy")
    llm = client.get_llm()
    assert llm.openai_api_base == "http://localhost:1234/v1"


def test_openai_client_does_not_double_append_v1_with_trailing_slash():
    client = OpenAIClient(model="test", base_url="http://localhost:1234/v1/", api_key="dummy")
    llm = client.get_llm()
    assert llm.openai_api_base == "http://localhost:1234/v1/"
