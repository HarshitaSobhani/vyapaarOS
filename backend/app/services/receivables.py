"""Deterministic receivables intelligence. Pure functions: no DB, no LLM."""
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

ZERO = Decimal("0")

# Scoring weights (max points per component, total 100).
W_AMOUNT, W_OVERDUE, W_BEHAVIOUR, W_VALUE = 30, 35, 20, 15
AMOUNT_CAP = Decimal("100000")      # outstanding at which the amount component saturates
OVERDUE_CAP_DAYS = 60
LATE_COUNT_CAP = 5
DELAY_VS_HISTORY_CAP = 15
VALUE_CAP = Decimal("500000")
HIGH_THRESHOLD, MEDIUM_THRESHOLD = 60, 35
DUE_SOON_DAYS = 7
COLLECTION_RATE_WINDOW_DAYS = 90


class Priority(StrEnum):
    high = "High"
    medium = "Medium"
    low = "Low"


@dataclass(frozen=True)
class InvoiceFacts:
    """An approved invoice with payment totals, as the engine sees it."""
    id: UUID
    number: str
    invoice_date: date
    due_date: date
    total: Decimal
    paid: Decimal
    last_payment_date: date | None = None

    @property
    def outstanding(self) -> Decimal:
        return max(self.total - self.paid, ZERO)

    @property
    def is_settled(self) -> bool:
        return self.outstanding == ZERO

    def days_overdue(self, today: date) -> int:
        if self.is_settled:
            return 0
        return max((today - self.due_date).days, 0)


@dataclass
class CustomerReceivable:
    customer_id: UUID
    customer_name: str
    company_name: str
    phone: str | None
    credit_limit: Decimal
    outstanding_amount: Decimal = ZERO
    overdue_amount: Decimal = ZERO
    days_overdue: int = 0                      # age of oldest overdue invoice, past due date
    oldest_overdue_age_days: int = 0           # days since that invoice was issued
    average_payment_delay: float | None = None  # avg days past due date across settled invoices
    average_days_to_pay: float | None = None    # avg days from invoice date to final payment
    invoice_count: int = 0
    open_invoice_count: int = 0
    late_payment_count: int = 0
    customer_value: Decimal = ZERO             # total invoiced
    total_paid: Decimal = ZERO
    delay_vs_history: int | None = None
    oldest_overdue_invoice_number: str | None = None
    oldest_overdue_invoice_id: UUID | None = None
    oldest_overdue_amount: Decimal = ZERO
    score: int = 0
    priority: Priority = Priority.low
    reasons: list[str] = field(default_factory=list)


def _inr(amount: Decimal) -> str:
    n = int(round(amount))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join([*parts, tail])
    return f"₹{'-' if n < 0 else ''}{s}"


def format_inr(amount: Decimal) -> str:
    return _inr(amount)


def compute_customer_receivable(
    customer_id: UUID, customer_name: str, company_name: str, phone: str | None,
    credit_limit: Decimal, invoices: Sequence[InvoiceFacts], today: date,
) -> CustomerReceivable:
    r = CustomerReceivable(customer_id, customer_name, company_name, phone, credit_limit)
    r.invoice_count = len(invoices)
    r.customer_value = sum((i.total for i in invoices), ZERO)
    r.total_paid = sum((i.paid for i in invoices), ZERO)
    delays: list[int] = []
    pay_days: list[int] = []
    oldest: InvoiceFacts | None = None
    for inv in invoices:
        if inv.is_settled:
            if inv.last_payment_date is not None:
                delay = (inv.last_payment_date - inv.due_date).days
                delays.append(delay)
                pay_days.append((inv.last_payment_date - inv.invoice_date).days)
                if delay > 0:
                    r.late_payment_count += 1
            continue
        r.outstanding_amount += inv.outstanding
        r.open_invoice_count += 1
        if inv.days_overdue(today) > 0:
            r.overdue_amount += inv.outstanding
            r.late_payment_count += 1
            if oldest is None or inv.due_date < oldest.due_date:
                oldest = inv
    if delays:
        r.average_payment_delay = round(sum(delays) / len(delays), 1)
        r.average_days_to_pay = round(sum(pay_days) / len(pay_days), 1)
    if oldest is not None:
        r.days_overdue = oldest.days_overdue(today)
        r.oldest_overdue_age_days = (today - oldest.invoice_date).days
        r.oldest_overdue_invoice_number = oldest.number
        r.oldest_overdue_invoice_id = oldest.id
        r.oldest_overdue_amount = oldest.outstanding
        if r.average_days_to_pay is not None:
            r.delay_vs_history = round(r.oldest_overdue_age_days - r.average_days_to_pay)
    _score(r)
    return r


def _score(r: CustomerReceivable) -> None:
    if r.outstanding_amount <= ZERO:
        r.score, r.priority, r.reasons = 0, Priority.low, ["Nothing outstanding"]
        return
    amount_pts = W_AMOUNT * min(float(r.outstanding_amount / AMOUNT_CAP), 1.0)
    overdue_pts = W_OVERDUE * min(r.days_overdue / OVERDUE_CAP_DAYS, 1.0)
    behaviour = 0.5 * min(r.late_payment_count / LATE_COUNT_CAP, 1.0)
    if r.delay_vs_history and r.delay_vs_history > 0:
        behaviour += 0.5 * min(r.delay_vs_history / DELAY_VS_HISTORY_CAP, 1.0)
    behaviour_pts = W_BEHAVIOUR * behaviour
    value_pts = W_VALUE * min(float(r.customer_value / VALUE_CAP), 1.0)
    r.score = round(amount_pts + overdue_pts + behaviour_pts + value_pts)
    if r.overdue_amount <= ZERO:
        r.priority = Priority.low  # nothing is late yet: monitor only
    elif r.score >= HIGH_THRESHOLD:
        r.priority = Priority.high
    elif r.score >= MEDIUM_THRESHOLD:
        r.priority = Priority.medium
    else:
        r.priority = Priority.low
    r.reasons = explain(r)


def explain(r: CustomerReceivable) -> list[str]:
    reasons: list[str] = []
    if r.overdue_amount <= ZERO:
        reasons.append(f"{_inr(r.outstanding_amount)} outstanding, none overdue yet")
        return reasons
    if r.outstanding_amount >= Decimal("75000"):
        reasons.append(f"Large outstanding balance ({_inr(r.outstanding_amount)})")
    else:
        reasons.append(f"{_inr(r.overdue_amount)} overdue of {_inr(r.outstanding_amount)} outstanding")
    reasons.append(f"Oldest invoice is {r.days_overdue} days past due")
    if r.delay_vs_history is not None and r.delay_vs_history > 0 and r.average_days_to_pay is not None:
        reasons.append(f"Payment is {r.delay_vs_history} days later than their historical average")
        reasons.append(f"Customer normally pays within {round(r.average_days_to_pay)} days")
    if r.late_payment_count >= 3:
        reasons.append(f"{r.late_payment_count} late payments on record")
    if r.credit_limit > ZERO and r.outstanding_amount > r.credit_limit:
        reasons.append(f"Outstanding exceeds credit limit of {_inr(r.credit_limit)}")
    if r.customer_value >= Decimal("300000"):
        reasons.append(f"High-value customer ({_inr(r.customer_value)} invoiced)")
    return reasons


# ---------- aggregate views ----------

BUCKETS: tuple[tuple[str, int, int | None], ...] = (
    ("Current", -10**6, 0), ("1–7 days", 1, 7), ("8–30 days", 8, 30),
    ("31–60 days", 31, 60), ("60+ days", 61, None),
)


def bucket_for(days_past_due: int) -> str:
    for label, lo, hi in BUCKETS:
        if days_past_due >= lo and (hi is None or days_past_due <= hi):
            return label
    return BUCKETS[0][0]


def aging_buckets(invoices: Iterable[InvoiceFacts], today: date) -> list[dict[str, object]]:
    totals = {label: ZERO for label, _, _ in BUCKETS}
    counts = {label: 0 for label, _, _ in BUCKETS}
    for inv in invoices:
        if inv.is_settled:
            continue
        label = bucket_for((today - inv.due_date).days)
        totals[label] += inv.outstanding
        counts[label] += 1
    return [{"bucket": label, "amount": totals[label], "invoice_count": counts[label]}
            for label, _, _ in BUCKETS]


@dataclass(frozen=True)
class CollectionSummary:
    total_outstanding: Decimal
    total_overdue: Decimal
    due_soon: Decimal
    collection_rate: float | None


def collection_summary(invoices: Sequence[InvoiceFacts], today: date) -> CollectionSummary:
    from datetime import timedelta
    outstanding = overdue = due_soon = ZERO
    billed = collected = ZERO
    window_start = today - timedelta(days=COLLECTION_RATE_WINDOW_DAYS)
    for inv in invoices:
        if not inv.is_settled:
            outstanding += inv.outstanding
            if inv.due_date < today:
                overdue += inv.outstanding
            elif (inv.due_date - today).days <= DUE_SOON_DAYS:
                due_soon += inv.outstanding
        if window_start <= inv.due_date <= today:
            billed += inv.total
            collected += min(inv.paid, inv.total)
    rate = round(float(collected / billed), 4) if billed > ZERO else None
    return CollectionSummary(outstanding, overdue, due_soon, rate)


def rank_priorities(receivables: Iterable[CustomerReceivable]) -> list[CustomerReceivable]:
    order = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
    open_ones = [r for r in receivables if r.outstanding_amount > ZERO]
    return sorted(open_ones, key=lambda r: (order[r.priority], -r.score, -r.outstanding_amount,
                                            r.company_name))
