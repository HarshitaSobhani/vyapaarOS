from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

Facts = dict[str, Any]


@dataclass(frozen=True)
class AIResult:
    text: str
    provider: str
    fallback_used: bool = False


class AIProvider(ABC):
    """What the application needs from an LLM. No vendor SDK types leak through this interface."""

    name: str

    @abstractmethod
    def answer(self, question: str, facts: Facts) -> str:
        """Answer a business question using only the supplied facts."""

    @abstractmethod
    def explain_priority(self, facts: Facts) -> str:
        """Explain a customer's collection priority and suggest a next action."""

    @abstractmethod
    def write_reminder(self, facts: Facts, variant: int = 0) -> str:
        """Draft a polite WhatsApp payment reminder."""
