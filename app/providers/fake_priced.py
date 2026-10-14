from __future__ import annotations

from app.providers.base import Completion, ModelProvider


class FakePricedProvider(ModelProvider):
    """Test-only backend that bills a fixed amount per call."""

    id = "fake-priced"
    display_name = "Fake priced (tests)"
    paid = True

    def __init__(self, price_usd: float = 0.01):
        self.price_usd = price_usd

    def complete(self, *, instructions: str, prompt: str) -> Completion:
        del instructions
        return Completion(
            text=f"fake-priced reply: {prompt[:80]}",
            cost_usd=self.price_usd,
            provider=self.id,
        )

    def reachable(self) -> bool:
        return True
