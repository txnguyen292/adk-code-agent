from __future__ import annotations

import os
from dataclasses import dataclass

import litellm

DEFAULT_BASE_URL = "https://us.api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_TEMPERATURE = 0.2


@dataclass(slots=True)
class OpenAIConfig:
    """Runtime configuration for using OpenAI models via LiteLLM."""

    api_key: str
    model: str = DEFAULT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        """Build configuration from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found in the environment. "
                "Set it before running the agent."
            )

        model = (
            os.getenv("OPENAI_MODEL")
            or os.getenv("OFFLINE_AGENT_MODEL")
            or DEFAULT_MODEL
        )
        base_url = (
            os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or DEFAULT_BASE_URL
        )
        temperature_raw = os.getenv("OPENAI_TEMPERATURE", str(DEFAULT_TEMPERATURE))
        try:
            temperature = float(temperature_raw)
        except ValueError as exc:
            raise ValueError(
                f"OPENAI_TEMPERATURE must be numeric, got '{temperature_raw}'."
            ) from exc

        return cls(
            api_key=api_key,
            model=model,
            temperature=temperature,
            base_url=base_url,
        )

    def _base_model_name(self) -> str:
        """Return the provider-stripped model name for capability checks."""
        model = (self.model or "").strip()
        if "/" in model:
            return model.split("/", 1)[1]
        return model

    def apply(self) -> None:
        """Ensure downstream libraries see the OpenAI credentials."""
        os.environ["OPENAI_API_KEY"] = self.api_key
        os.environ["OPENAI_MODEL"] = self.litellm_model()
        os.environ["OPENAI_BASE_URL"] = self.base_url
        os.environ["OPENAI_API_BASE"] = self.base_url
        litellm.api_base = self.base_url
        litellm.ssl_verify = False
        if self._base_model_name().lower().startswith("gpt-5"):
            litellm.drop_params = True

    def litellm_model(self) -> str:
        """Return a LiteLLM-compatible model identifier."""
        model = (self.model or "").strip()
        if not model:
            return model
        if "/" in model:
            return model
        if model.startswith(("gpt-", "o1-", "o3-", "o4-")):
            return f"openai/{model}"
        return model

    def effective_temperature(self) -> float:
        """Return a supported temperature for the selected model."""
        model = self._base_model_name().lower()
        if model.startswith("gpt-5"):
            return 1.0
        return self.temperature

    def drop_params_enabled(self) -> bool:
        """Return True when unsupported params should be dropped."""
        return self._base_model_name().lower().startswith("gpt-5")
