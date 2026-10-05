"""Wraps a primary provider with validation and a deterministic fallback."""
import logging

from app.core.config import Settings, get_settings
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.provider import AIProvider, AIResult, Facts
from app.services.ai.validation import answer_is_grounded, reminder_is_valid

logger = logging.getLogger("vyapaaros.ai")


class AIService:
    def __init__(self, primary: AIProvider, fallback: AIProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback or MockAIProvider()

    def answer(self, question: str, facts: Facts) -> AIResult:
        return self._guarded(lambda p: p.answer(question, facts), lambda t: answer_is_grounded(t, facts))

    def explain_priority(self, facts: Facts) -> AIResult:
        return self._guarded(lambda p: p.explain_priority(facts), lambda t: answer_is_grounded(t, facts))

    def write_reminder(self, facts: Facts, variant: int = 0) -> AIResult:
        return self._guarded(lambda p: p.write_reminder(facts, variant),
                             lambda t: reminder_is_valid(t, facts))

    def _guarded(self, call, is_valid) -> AIResult:  # type: ignore[no-untyped-def]
        if self.primary.name != self.fallback.name:
            try:
                text = call(self.primary)
                if is_valid(text):
                    return AIResult(text, self.primary.name)
                logger.warning("AI output rejected by validation; using fallback")
            except Exception:  # provider/network failure must never break the feature
                logger.exception("AI provider failed; using fallback")
            return AIResult(call(self.fallback), self.fallback.name, fallback_used=True)
        return AIResult(call(self.primary), self.primary.name)


def build_ai_service(settings: Settings | None = None) -> AIService:
    settings = settings or get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        from app.services.ai.openai_provider import OpenAIProvider
        return AIService(OpenAIProvider(settings.openai_api_key, settings.openai_model))
    if settings.ai_provider == "openai":
        logger.warning("AI_PROVIDER=openai but OPENAI_API_KEY is empty; using mock provider")
    return AIService(MockAIProvider())
