from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class MissingSecretError(RuntimeError):
    def __init__(self, variable: str):
        self.variable = variable
        super().__init__(f"Missing required secret: {variable}")


@dataclass
class Completion:
    text: str
    cost_usd: float = 0.0
    provider: str = "stub"
    fallback: bool = False


class ModelProvider(ABC):
    """Clean interface for adding another model backend."""

    id: str
    display_name: str
    paid: bool = False
    secret_name: str | None = None

    @abstractmethod
    def complete(self, *, instructions: str, prompt: str) -> Completion:
        raise NotImplementedError

    @abstractmethod
    def reachable(self) -> bool:
        raise NotImplementedError
