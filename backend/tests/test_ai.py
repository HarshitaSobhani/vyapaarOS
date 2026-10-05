from app.core.config import Settings
from app.services.ai.mock_provider import MockAIProvider
from app.services.ai.provider import AIProvider
from app.services.ai.service import AIService, build_ai_service
from app.services.ai.validation import answer_is_grounded, reminder_is_valid

FACTS = {"customer_name": "Rajesh", "invoice_number": "INV-2609-0042", "amount": 82400,
         "amount_display": "₹82,400", "due_date": "12 Sep 2026", "days_overdue": 24}


class Boom(AIProvider):
    name = "openai"

    def answer(self, question, facts):
        raise TimeoutError("network down")

    explain_priority = answer

    def write_reminder(self, facts, variant=0):
        raise TimeoutError("network down")


class Fixed(AIProvider):
    name = "openai"

    def __init__(self, text):
        self.text = text

    def answer(self, question, facts):
        return self.text

    def explain_priority(self, facts):
        return self.text

    def write_reminder(self, facts, variant=0):
        return self.text


def test_mock_is_deterministic_and_variants_differ():
    m = MockAIProvider()
    assert m.write_reminder(FACTS) == m.write_reminder(FACTS)
    assert m.write_reminder(FACTS, 1) != m.write_reminder(FACTS, 0)
    assert "INV-2609-0042" in m.write_reminder(FACTS) and "₹82,400" in m.write_reminder(FACTS)


def test_provider_failure_falls_back_to_mock():
    r = AIService(Boom()).write_reminder(FACTS)
    assert r.fallback_used and r.provider == "mock" and "INV-2609-0042" in r.text


def test_reminder_with_invented_amount_is_rejected():
    bad = "Hi Rajesh, invoice INV-2609-0042 for ₹82,400 is overdue. Also ₹9,999 late fee."
    assert not reminder_is_valid(bad, FACTS)
    assert AIService(Fixed(bad)).write_reminder(FACTS).fallback_used


def test_aggressive_reminder_is_rejected():
    assert not reminder_is_valid("Final warning: pay INV-2609-0042 ₹82,400 or legal action follows.", FACTS)


def test_valid_llm_output_is_used():
    ok = "Hi Rajesh, a gentle reminder that invoice INV-2609-0042 for ₹82,400 is 24 days overdue. Thank you."
    r = AIService(Fixed(ok)).write_reminder(FACTS)
    assert not r.fallback_used and r.provider == "openai" and r.text == ok


def test_numbers_must_come_from_facts():
    facts = {"outstanding": 82400, "outstanding_display": "₹82,400", "days_overdue": 24}
    assert answer_is_grounded("They owe ₹82,400 and are 24 days late.", facts)
    assert not answer_is_grounded("They owe ₹90,000.", facts)
    assert answer_is_grounded("Reasons:\n1. Large balance of ₹82,400", facts)


def test_without_key_openai_setting_uses_mock():
    s = Settings(ai_provider="openai", openai_api_key="", _env_file=None)
    assert build_ai_service(s).primary.name == "mock"


def test_openai_provider_sends_facts_and_guardrails_through_sdk_client():
    from types import SimpleNamespace

    from app.services.ai.openai_provider import OpenAIProvider

    calls = []

    class FakeCompletions:
        def create(self, **kw):
            calls.append(kw)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Hi Rajesh, invoice INV-2609-0042 for ₹82,400 is overdue. Thank you."))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    svc = AIService(OpenAIProvider("sk-test", "gpt-test", client=client))
    r = svc.write_reminder(FACTS)
    assert r.provider == "openai" and not r.fallback_used
    sent = calls[0]["messages"]
    assert "Use only" in sent[0]["content"] and "INV-2609-0042" in sent[1]["content"]
