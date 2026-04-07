import os

import pytest

from core.llm.settings import OpenAIConfig


def test_from_env_uses_openai_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OFFLINE_AGENT_MODEL", raising=False)
    config = OpenAIConfig.from_env()
    assert config.model == "gpt-5.4"
    assert config.litellm_model() == "openai/gpt-5.4"


def test_from_env_uses_offline_agent_model_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("OFFLINE_AGENT_MODEL", "gpt-4o-mini")
    config = OpenAIConfig.from_env()
    assert config.model == "gpt-4o-mini"
    assert config.litellm_model() == "openai/gpt-4o-mini"


def test_gpt5_uses_supported_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.2")
    config = OpenAIConfig.from_env()
    assert config.effective_temperature() == 1.0
    assert config.drop_params_enabled() is True


def test_apply_sets_openai_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    config = OpenAIConfig.from_env()
    config.apply()
    assert os.environ["OPENAI_MODEL"] == "openai/gpt-4o-mini"
    assert os.environ["OPENAI_API_KEY"] == "test-key"
