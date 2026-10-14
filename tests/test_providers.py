from pathlib import Path

import httpx
import pytest
from app.providers.anthropic import AnthropicProvider, anthropic_cost_usd
from app.providers.base import MissingSecretError
from app.providers.registry import available_providers, build_provider
from app.providers.stub import StubProvider, extract_signature
from app.settings import REPO_ROOT
from tests.conftest import complete_wizard
from tests.fixtures.fictional import ANTHROPIC_API_KEY


def test_provider_order_stub_then_anthropic():
    rows = available_providers()
    assert [row["id"] for row in rows] == ["stub", "anthropic"]


def test_stub_reply_includes_skill_signature():
    provider = StubProvider(str(REPO_ROOT / "skills"), str(REPO_ROOT / "prompts"))
    result = provider.complete(instructions="hard rules", prompt="Do you have trail maps?")
    skill = (REPO_ROOT / "skills" / "inbox-clerk" / "SKILL.md").read_text()
    signature = extract_signature(skill)
    assert signature in result.text
    assert result.provider == "stub"
    assert result.cost_usd == 0


def test_changing_skill_changes_stub_reply(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "inbox-clerk"
    skill_dir.mkdir(parents=True)
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "inbox-clerk.md").write_text("Keep replies short.\n")
    (skill_dir / "SKILL.md").write_text(
        "---\nname: inbox-clerk\ndescription: demo\n---\n## Signature\nALPHA-SIGNATURE\n"
    )
    provider = StubProvider(str(tmp_path / "skills"), str(prompts))
    first = provider.complete(instructions="", prompt="hello")
    assert "ALPHA-SIGNATURE" in first.text
    (skill_dir / "SKILL.md").write_text(
        "---\nname: inbox-clerk\ndescription: demo\n---\n## Signature\nBETA-SIGNATURE\n"
    )
    second = provider.complete(instructions="", prompt="hello")
    assert "BETA-SIGNATURE" in second.text
    assert "ALPHA-SIGNATURE" not in second.text


def test_anthropic_missing_key_names_variable():
    provider = AnthropicProvider(api_key="")
    with pytest.raises(MissingSecretError) as exc:
        provider.complete(instructions="x", prompt="y")
    assert exc.value.variable == "ANTHROPIC_API_KEY"


def test_anthropic_is_not_called_during_stub_flow(client, monkeypatch):
    def fail_post(self, url, *args, **kwargs):
        if "anthropic.com" in str(url):
            raise AssertionError("live HTTP is not allowed in tests")
        return original_post(self, url, *args, **kwargs)

    original_post = httpx.Client.post
    monkeypatch.setattr(httpx.Client, "post", fail_post)
    complete_wizard(client)
    response = client.post(
        "/api/agents/inbox-clerk/messages",
        json={"prompt": "Need a paperback trail map"},
    )
    assert response.status_code == 200
    assert "Scout here" in response.json()["text"]


def test_anthropic_cost_from_token_usage():
    assert anthropic_cost_usd({"input_tokens": 1_000_000, "output_tokens": 1_000_000}) == 18.0
    assert anthropic_cost_usd({"input_tokens": 0, "output_tokens": 0}) == 0.0


def test_anthropic_complete_records_usage_cost(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "content": [{"type": "text", "text": "hello from anthropic"}],
                "usage": {"input_tokens": 1000, "output_tokens": 200},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            del args, kwargs
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    result = AnthropicProvider(api_key=ANTHROPIC_API_KEY).complete(
        instructions="x", prompt="y"
    )
    assert result.text == "hello from anthropic"
    assert result.cost_usd == anthropic_cost_usd({"input_tokens": 1000, "output_tokens": 200})
    assert result.cost_usd > 0


def test_build_provider_interface():
    stub = build_provider(
        "stub",
        skills_dir=str(REPO_ROOT / "skills"),
        prompts_dir=str(REPO_ROOT / "prompts"),
    )
    assert stub.id == "stub"
    anth = build_provider("anthropic", skills_dir=".", prompts_dir=".", anthropic_api_key="x")
    assert anth.id == "anthropic"
    assert anth.paid is True
