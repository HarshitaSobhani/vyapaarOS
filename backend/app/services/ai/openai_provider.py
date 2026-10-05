"""OpenAI-backed provider. The only module that imports the OpenAI SDK."""
from typing import Any

from openai import OpenAI

from app.services.ai import prompts
from app.services.ai.provider import AIProvider, Facts


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, client: Any | None = None) -> None:
        self._client = client or OpenAI(api_key=api_key, timeout=20.0, max_retries=1)
        self._model = model

    def _complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        resp = self._client.chat.completions.create(
            model=self._model, temperature=temperature, max_tokens=400,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return (resp.choices[0].message.content or "").strip()

    def answer(self, question: str, facts: Facts) -> str:
        return self._complete(prompts.ASSISTANT,
                              f"Question: {question}\n\n{prompts.facts_block(facts)}")

    def explain_priority(self, facts: Facts) -> str:
        return self._complete(prompts.COLLECTION_EXPLANATION, prompts.facts_block(facts))

    def write_reminder(self, facts: Facts, variant: int = 0) -> str:
        return self._complete(prompts.WHATSAPP, prompts.facts_block(facts),
                              temperature=min(0.2 + 0.2 * variant, 0.8))
