from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.receivables import (
    InvoiceFacts,
    Priority,
    aging_buckets,
    bucket_for,
    collection_summary,
    compute_customer_receivable,
    format_inr,
)

TODAY = date(2026, 10, 5)


def inv(age: int, terms: int, total: int, paid: int = 0, paid_after: int | None = None, n: str = "I") -> InvoiceFacts:
    d = TODAY - timedelta(days=age)
    return InvoiceFacts(uuid4(), n, d, d + timedelta(days=terms), Decimal(total), Decimal(paid),
                        d + timedelta(days=paid_after) if paid_after is not None else None)


def calc(invoices: list[InvoiceFacts], credit: int = 100000):
    return compute_customer_receivable(uuid4(), "Rajesh", "ABC Electricals", None, Decimal(credit), invoices, TODAY)


def test_outstanding_and_partial_payment():
    r = calc([inv(10, 30, 1000, paid=400), inv(50, 30, 500, paid=500, paid_after=20)])
    assert r.outstanding_amount == Decimal(600)
    assert r.open_invoice_count == 1
    assert r.overdue_amount == 0


def test_days_overdue_uses_oldest_unpaid_invoice():
    r = calc([inv(60, 30, 1000, n="OLD"), inv(40, 30, 1000, n="NEW")])
    assert r.days_overdue == 30
    assert r.oldest_overdue_invoice_number == "OLD"
    assert r.overdue_amount == 2000


def test_not_yet_due_is_not_overdue():
    r = calc([inv(5, 30, 5000)])
    assert r.days_overdue == 0 and r.priority is Priority.low


def test_average_payment_delay_and_days_to_pay():
    r = calc([inv(100, 30, 100, paid=100, paid_after=40), inv(60, 30, 100, paid=100, paid_after=20)])
    assert r.average_payment_delay == 0.0           # +10 and -10 days vs due date
    assert r.average_days_to_pay == 30.0
    assert r.late_payment_count == 1


def test_high_priority_with_explanations():
    paid = [inv(150 - i * 20, 30, 40000, paid=40000, paid_after=40) for i in range(4)]
    r = calc([*paid, inv(70, 30, 90000, n="INV-9")], credit=50000)
    assert r.priority is Priority.high
    assert r.delay_vs_history == 70 - 40
    text = " ".join(r.reasons)
    assert "Large outstanding balance" in text and "later than their historical average" in text
    assert "normally pays within 40 days" in text and "exceeds credit limit" in text


def test_small_recent_overdue_is_not_high():
    r = calc([inv(33, 30, 3000)])
    assert r.priority is Priority.low


def test_customer_with_nothing_outstanding():
    r = calc([inv(40, 30, 1000, paid=1000, paid_after=30)])
    assert r.outstanding_amount == 0 and r.priority is Priority.low and r.score == 0


def test_aging_buckets():
    assert [bucket_for(d) for d in (-3, 0, 1, 7, 8, 30, 31, 60, 61)] == [
        "Current", "Current", "1–7 days", "1–7 days", "8–30 days", "8–30 days", "31–60 days",
        "31–60 days", "60+ days"]
    buckets = {b["bucket"]: b for b in aging_buckets([inv(40, 30, 100), inv(100, 30, 200), inv(10, 30, 50)], TODAY)}
    assert buckets["8–30 days"]["amount"] == 100 and buckets["60+ days"]["amount"] == 200
    assert buckets["Current"]["invoice_count"] == 1


def test_collection_summary():
    s = collection_summary([inv(50, 30, 1000, paid=1000, paid_after=25), inv(45, 30, 1000), inv(25, 30, 300)], TODAY)
    assert s.total_outstanding == 1300 and s.total_overdue == 1000 and s.due_soon == 300
    assert s.collection_rate == 0.5


def test_inr_formatting():
    assert format_inr(Decimal("82400")) == "₹82,400"
    assert format_inr(Decimal("1234567")) == "₹12,34,567"
