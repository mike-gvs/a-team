from __future__ import annotations

import os

import httpx

from app.providers.base import Completion, MissingSecretError, ModelProvider

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


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
        return Completion(text=text, cost_usd=0.0, provider=self.id)

    def reachable(self) -> bool:
        return bool(self.api_key)
