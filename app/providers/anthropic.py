from __future__ import annotations

import os

import httpx

from app.providers.base import Completion, MissingSecretError, ModelProvider

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
# Claude Sonnet 4.5 list prices (USD per million tokens).
INPUT_USD_PER_MTOK = 3.0
OUTPUT_USD_PER_MTOK = 15.0


def anthropic_cost_usd(usage: dict) -> float:
    inp = int(usage.get("input_tokens") or 0)
    out = int(usage.get("output_tokens") or 0)
    return round((inp * INPUT_USD_PER_MTOK + out * OUTPUT_USD_PER_MTOK) / 1_000_000, 6)


class AnthropicProvider(ModelProvider):
    id = "anthropic"
    display_name = "Anthropic"
    paid = True
    secret_name = "ANTHROPIC_API_KEY"

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-5"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model

    def complete(self, *, instructions: str, prompt: str) -> Completion:
        if not self.api_key:
            raise MissingSecretError(self.secret_name)
        payload = {
            "model": self.model,
            "max_tokens": 512,
            "system": instructions,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(ANTHROPIC_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if isinstance(block, dict)
        )
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return Completion(text=text, cost_usd=anthropic_cost_usd(usage), provider=self.id)

    def reachable(self) -> bool:
        return bool(self.api_key)
