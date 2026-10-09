"""Provider selection stays outside graph construction."""

from __future__ import annotations

from strands.models.model import Model

from reelhive.config import Config

TIERS = ("strong", "fast")
NODE_TIERS = {
    "research": "fast",
    "script": "strong",
    "scenes": "fast",
    "music": "fast",
    "critic": "strong",
    "fix": "strong",
}


class ProviderError(RuntimeError):
    pass


def model_id(config: Config, provider: str, tier: str) -> str:
    tiers = config.models.get(provider)
    if tiers is None:
        raise ProviderError(f"config.yaml: models.{provider}.{{strong,fast}} is required")
    return str(getattr(tiers, tier))


def build_model(config: Config, provider: str, tier: str) -> Model:
    name = model_id(config, provider, tier)
    try:
        if provider == "claude":
            from strands.models.anthropic import AnthropicModel

            return AnthropicModel(model_id=name, max_tokens=config.max_tokens)
        if provider == "bedrock":
            from strands.models.bedrock import BedrockModel

            return BedrockModel(model_id=name, max_tokens=config.max_tokens)
        if provider == "openai":
            from strands.models.openai import OpenAIModel

            return OpenAIModel(model_id=name, params={"max_completion_tokens": config.max_tokens})
        if provider == "ollama":
            from strands.models.ollama import OllamaModel

            return OllamaModel(host=config.ollama_host, model_id=name, max_tokens=config.max_tokens)
    except ImportError as e:
        raise ProviderError(f"Install the {provider} extra: uv sync --extra {provider}") from e
    raise ProviderError(f"provider {provider!r} is not a Strands model")


def build_models(config: Config) -> dict[str, Model]:
    models = {}
    for tier in TIERS:
        provider = config.provider_for("", tier)
        if provider != "copilot":
            models[tier] = build_model(config, provider, tier)
        else:
            model_id(config, "copilot", tier)
    for node, provider in config.nodes.items():
        if provider == "copilot":
            model_id(config, provider, NODE_TIERS[node])
        else:
            models[node] = build_model(config, provider, NODE_TIERS[node])
    return models
