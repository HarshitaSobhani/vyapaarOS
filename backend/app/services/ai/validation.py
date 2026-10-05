"""Guards applied to every LLM output before it reaches a user."""
import re
from typing import Any

NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
LIST_MARKER_RE = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)
FORBIDDEN_PHRASES = (
    "legal action", "final warning", "court", "police", "blacklist", "last chance", "penalty",
    "will pay", "promised", "guarantee",
)
MAX_REMINDER_CHARS = 700


def _norm(raw: str) -> float | None:
    try:
        return float(raw.replace(",", "").rstrip("."))
    except ValueError:
        return None


def numbers_in(text: str) -> set[float]:
    return {n for m in NUMBER_RE.findall(text) if (n := _norm(m)) is not None}


def fact_numbers(facts: Any) -> set[float]:
    found: set[float] = set()
    if isinstance(facts, dict):
        for v in facts.values():
            found |= fact_numbers(v)
    elif isinstance(facts, (list, tuple)):
        for v in facts:
            found |= fact_numbers(v)
    elif isinstance(facts, bool) or facts is None:
        pass
    elif isinstance(facts, (int, float)) or hasattr(facts, "__float__"):
        f = float(facts)
        found |= {f, round(f), round(f, 1), round(f, 2)}
    else:
        found |= numbers_in(str(facts))
    return found


def unsupported_numbers(text: str, facts: Any) -> set[float]:
    """Numbers that appear in the text but nowhere in the facts."""
    allowed = fact_numbers(facts)
    cleaned = LIST_MARKER_RE.sub("", text)
    return {n for n in numbers_in(cleaned) if n not in allowed and round(n, 1) not in allowed}


def answer_is_grounded(text: str, facts: Any) -> bool:
    return bool(text.strip()) and not unsupported_numbers(text, facts)


def reminder_is_valid(text: str, facts: dict[str, Any]) -> bool:
    lowered = text.lower()
    if not text.strip() or len(text) > MAX_REMINDER_CHARS:
        return False
    if any(p in lowered for p in FORBIDDEN_PHRASES):
        return False
    if str(facts["invoice_number"]) not in text:
        return False
    amount_digits = str(facts["amount_display"]).replace("₹", "")
    return amount_digits in text and not unsupported_numbers(text, facts)
