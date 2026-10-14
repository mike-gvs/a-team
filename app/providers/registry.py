from __future__ import annotations

from app.providers.anthropic import AnthropicProvider
from app.providers.base import ModelProvider
from app.providers.fake_priced import FakePricedProvider
from app.providers.stub import StubProvider


def available_providers(*, include_test: bool = False) -> list[dict[str, str | bool]]:
    rows: list[dict[str, str | bool]] = [
        {
            "id": StubProvider.id,
            "display_name": StubProvider.display_name,
            "paid": False,
            "default": True,
        },
        {
            "id": AnthropicProvider.id,
            "display_name": AnthropicProvider.display_name,
            "paid": True,
            "default": False,
        },
    ]
    if include_test:
        rows.append(
            {
                "id": FakePricedProvider.id,
                "display_name": FakePricedProvider.display_name,
                "paid": True,
                "default": False,
            }
        )
    return rows


def build_provider(
    backend: str,
    *,
    skills_dir: str,
    prompts_dir: str,
    anthropic_api_key: str = "",
    slug: str = "inbox-clerk",
) -> ModelProvider:
    if backend == "anthropic":
        return AnthropicProvider(api_key=anthropic_api_key)
    if backend == "fake-priced":
        return FakePricedProvider()
    return StubProvider(skills_dir=skills_dir, prompts_dir=prompts_dir, slug=slug)
