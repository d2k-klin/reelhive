import asyncio
from types import SimpleNamespace

import pytest
from conftest import FakeModel, make_script

from reelhive.agents.script_writer import ScriptWriterNode
from reelhive.config import Config, ImageGeneration, Tiers
from reelhive.core.context import RunContext
from reelhive.core.events import EventBus
from reelhive.providers.copilot.node import auth_status, deny_permission, list_models
from reelhive.providers.factory import ProviderError, build_model, build_models
from reelhive.visuals.generators.openai import OpenAIImageGenerator


@pytest.mark.parametrize(
    "provider,module,class_name",
    [
        ("bedrock", "strands.models.bedrock", "BedrockModel"),
        ("openai", "strands.models.openai", "OpenAIModel"),
        ("ollama", "strands.models.ollama", "OllamaModel"),
    ],
)
def test_provider_factory_passes_configured_models(provider, module, class_name, monkeypatch):
    calls = []
    monkeypatch.setattr(f"{module}.{class_name}", lambda **kwargs: calls.append(kwargs) or kwargs)
    config = Config(provider=provider, models={provider: Tiers(strong="strong-model", fast="fast-model")})
    models = build_models(config)
    assert {m["model_id"] for m in models.values()} == {"strong-model", "fast-model"}
    if provider == "ollama":
        assert all(c["host"] == config.ollama_host for c in calls)
    if provider == "openai":
        assert calls[0]["params"]["max_completion_tokens"] == config.max_tokens


def test_factory_mix_and_missing_dependency(monkeypatch):
    config = Config(
        provider="copilot",
        models={"copilot": Tiers(strong="a", fast="b"), "claude": Tiers(strong="c", fast="d")},
        nodes={"scenes": "claude", "script": "copilot"},
    )
    assert set(build_models(config)) == {"scenes"}
    with pytest.raises(ProviderError, match="not a Strands"):
        build_model(config, "copilot", "strong")
    import builtins

    real_import = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "strands.models.anthropic":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    with pytest.raises(ProviderError, match="Install"):
        build_models(Config())


class FakeCopilotSession:
    def __init__(self, options, payloads):
        self.options = options
        self.payloads = payloads
        self.closed = False

    async def send_and_wait(self, prompt, **kwargs):
        tool = self.options["tools"][0]
        self.options["on_event"](
            SimpleNamespace(type="assistant.message_delta", data=SimpleNamespace(delta_content="draft"))
        )
        self.options["on_event"](
            SimpleNamespace(type="assistant.usage", data=SimpleNamespace(input_tokens=10, output_tokens=5))
        )
        tool.handler(SimpleNamespace(arguments=self.payloads.pop(0)))

    async def disconnect(self):
        self.closed = True


class FakeCopilotClient:
    def __init__(self, payloads):
        self.payloads = payloads
        self.stopped = False

    async def start(self):
        pass

    async def create_session(self, **options):
        self.session = FakeCopilotSession(options, self.payloads)
        return self.session

    async def stop(self):
        self.stopped = True

    async def list_models(self):
        return [SimpleNamespace(id="available-model")]

    async def get_auth_status(self):
        return SimpleNamespace(isAuthenticated=True)


@pytest.mark.parametrize("invalid_first", [False, True])
def test_copilot_submit_stream_repair_and_permissions(tmp_path, brief, monkeypatch, invalid_first):
    config = Config(provider="copilot", models={"copilot": Tiers(strong="chosen", fast="fast")})
    payloads = ([{"beats": []}] if invalid_first else []) + [make_script(brief)]
    client = FakeCopilotClient(payloads)
    monkeypatch.setattr("copilot.CopilotClient", lambda: client)
    events = []
    bus = EventBus()
    bus.subscribe(events.append)
    ctx = RunContext(tmp_path, brief, bus, {}, None, None, config=config)
    asyncio.run(ScriptWriterNode().invoke_async("draft", {"ctx": ctx}))
    assert ctx.script and client.stopped and client.session.closed
    options = client.session.options
    assert options["available_tools"] == ["submit_script"]
    assert options["tools"][0].skip_permission
    assert options["enable_config_discovery"] is False and options["enable_file_hooks"] is False
    for request in ({"kind": "shell", "command": "echo bad"}, {"kind": "write", "path": "/tmp/bad"}):
        assert deny_permission(request, {}).kind == "user-not-available"
    assert any(e.type == "agent.text" and e.data["node"] == "script" for e in events)
    assert any(e.type == "node.task" and "Repairing" in e.data["task"] for e in events) == invalid_first


def test_copilot_rejects_repeated_invalid_output_and_closes(tmp_path, brief, monkeypatch):
    config = Config(provider="copilot", models={"copilot": Tiers(strong="chosen", fast="fast")})
    client = FakeCopilotClient([{}, {}])
    monkeypatch.setattr("copilot.CopilotClient", lambda: client)
    ctx = RunContext(tmp_path, brief, EventBus(), {}, None, None, config=config)
    with pytest.raises(ProviderError, match="Copilot script did not submit valid"):
        asyncio.run(ScriptWriterNode().execute(ctx))
    assert client.stopped and client.session.closed
    assert asyncio.run(list_models()) == ["available-model"]
    assert asyncio.run(auth_status())


def test_node_uses_override_model(tmp_path, brief):
    override = FakeModel({"Script": make_script(brief)})
    ctx = RunContext(tmp_path, brief, EventBus(), {"script": override}, None, None)
    asyncio.run(ScriptWriterNode().execute(ctx))
    assert override.calls == ["Script"]


def test_openai_generator_writes_bytes_and_usage(tmp_path, monkeypatch):
    import base64

    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            data=[SimpleNamespace(b64_json=base64.b64encode(b"image").decode())],
            usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 42}),
        )

    monkeypatch.setattr("openai.OpenAI", lambda: SimpleNamespace(images=SimpleNamespace(generate=generate)))
    generator = OpenAIImageGenerator(ImageGeneration(model="image-model", cost_per_image=0.04))
    result = generator.generate("clouds", "1024x1024", tmp_path / "out.png")
    assert (tmp_path / "out.png").read_bytes() == b"image"
    assert calls[0]["model"] == "image-model" and result["cost_usd"] == 0.04
    assert result["usage"]["total_tokens"] == 42


def test_strands_invalid_output_gets_one_repair(tmp_path, brief, monkeypatch):
    from pydantic import ValidationError

    from reelhive.schemas.script import Script

    calls = []

    class Agent:
        def __init__(self, **kwargs):
            pass

        async def invoke_async(self, prompt, **kwargs):
            calls.append(prompt)
            if len(calls) == 1:
                Script.model_validate({})
            return SimpleNamespace(
                structured_output=Script.model_validate(make_script(brief)),
                metrics=SimpleNamespace(accumulated_usage={"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}),
            )

    monkeypatch.setattr("reelhive.nodes.base.Agent", Agent)
    ctx = RunContext(tmp_path, brief, EventBus(), {"strong": None}, None, None)
    asyncio.run(ScriptWriterNode().execute(ctx))
    assert len(calls) == 2 and "Validation error" in calls[1] and ctx.script

    class BrokenAgent(Agent):
        async def invoke_async(self, *args, **kwargs):
            Script.model_validate({})

    monkeypatch.setattr("reelhive.nodes.base.Agent", BrokenAgent)
    with pytest.raises(ValidationError):
        asyncio.run(ScriptWriterNode().execute(ctx))


@pytest.mark.parametrize("failure", [TimeoutError, asyncio.CancelledError])
def test_copilot_cleans_up_on_timeout_or_cancellation(tmp_path, brief, monkeypatch, failure):
    config = Config(provider="copilot", models={"copilot": Tiers(strong="chosen", fast="fast")})
    client = FakeCopilotClient([])

    class FailedSession(FakeCopilotSession):
        async def send_and_wait(self, *args, **kwargs):
            raise failure()

    async def create(**options):
        client.session = FailedSession(options, [])
        return client.session

    client.create_session = create
    monkeypatch.setattr("copilot.CopilotClient", lambda: client)
    ctx = RunContext(tmp_path, brief, EventBus(), {}, None, None, config=config)
    with pytest.raises(failure):
        asyncio.run(ScriptWriterNode().execute(ctx))
    assert client.session.closed and client.stopped
