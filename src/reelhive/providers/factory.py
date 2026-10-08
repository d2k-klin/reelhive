"""Picks the model behind each agent tier. Graph code never knows which provider is in use."""

from __future__ import annotations

from strands.models.model import Model

from reelhive.config import Config

TIERS = ("strong", "fast")


class ProviderError(RuntimeError):
    pass


def build_models(config: Config) -> dict[str, Model]:
    # ponytail: Claude only in M1; Bedrock, OpenAI, Ollama and Copilot land in M2 (plan §12).
    if config.provider != "claude":
        raise ProviderError(f"provider {config.provider!r} arrives in M2; M1 supports 'claude'")
    tiers = config.models.get("claude")
    if tiers is None:
        raise ProviderError("config.yaml: models.claude.{strong,fast} is required")
    from strands.models.anthropic import AnthropicModel

    return {tier: AnthropicModel(model_id=getattr(tiers, tier), max_tokens=config.max_tokens) for tier in TIERS}
