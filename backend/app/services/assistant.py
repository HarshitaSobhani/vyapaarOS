"""Retrieves structured business facts for a question; the LLM only explains them."""
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import InvoiceStatus
from app.services.ai.provider import AIResult, Facts
from app.services.ai.service import AIService
from app.services.inventory import StockStatus
from app.services.inventory_service import compute_risks, summarize
from app.services.invoices import count_by_status
from app.services.receivables import CustomerReceivable, format_inr
from app.services.receivables_service import ReceivablesSnapshot, build_snapshot

OUT_OF_SCOPE = ("I can answer questions about your receivables, collections, inventory and invoices. "
                "Try: “Which customers should I follow up with today?”")


def customer_facts(r: CustomerReceivable) -> dict[str, Any]:
    return {
        "company": r.company_name, "contact": r.customer_name, "priority": r.priority.value,
        "priority_score": r.score, "outstanding": r.outstanding_amount,
        "outstanding_display": format_inr(r.outstanding_amount), "overdue": r.overdue_amount,
        "overdue_display": format_inr(r.overdue_amount), "days_overdue": r.days_overdue,
        "average_payment_delay": r.average_payment_delay, "average_days_to_pay": r.average_days_to_pay,
        "late_payment_count": r.late_payment_count, "invoice_count": r.invoice_count,
        "customer_value": r.customer_value, "customer_value_display": format_inr(r.customer_value),
        "delay_vs_history": r.delay_vs_history, "reasons": r.reasons,
        "oldest_overdue_invoice": r.oldest_overdue_invoice_number,
    }


def _classify(question: str, snap: ReceivablesSnapshot) -> tuple[str, CustomerReceivable | None]:
    q = question.lower()
    for r in sorted(snap.customers, key=lambda r: -len(r.company_name)):
        if r.company_name.lower() in q or (len(r.customer_name) > 4 and r.customer_name.lower() in q):
            return "customer", r
    has = lambda *words: any(w in q for w in words)  # noqa: E731
    if has("stock", "inventory", "reorder", "purchase order", "supplier", "restock"):
        return "inventory", None
    if has("worst", "behavio", "slow pay", "pays late", "late pay", "habit"):
        return "worst_payers", None
    if has("cause", "reason", "why") and has("overdue", "receivable", "outstanding", "unpaid"):
        return "overdue_causes", None
    if has("follow", "chase", "collect", "remind", "priorit", "who owes", "owe"):
        return "priorities", None
    if has("overview", "summary", "attention", "today", "need", "status", "overdue", "receivable"):
        return "overview", None
    return "none", None


def retrieve_facts(db: Session, question: str, today: date) -> tuple[str, Facts | None]:
    snap = build_snapshot(db, today)
    intent, customer = _classify(question, snap)
    if intent == "none":
        return intent, None
    if intent == "customer" and customer is not None:
        return intent, {"intent": intent, "customer": customer_facts(customer)}
    overdue = [r for r in snap.customers if r.overdue_amount > 0]
    if intent == "priorities":
        top = snap.follow_ups[:5]
        return intent, {"intent": intent, "follow_up_count": len(snap.follow_ups),
                        "total_overdue_display": format_inr(snap.summary.total_overdue),
                        "customers": [customer_facts(r) for r in top]}
    if intent == "worst_payers":
        ranked = sorted((r for r in snap.customers if r.invoice_count > 0),
                        key=lambda r: (-r.late_payment_count, -(r.average_payment_delay or 0)))[:3]
        return intent, {"intent": intent, "customers": [customer_facts(r) for r in ranked]}
    if intent == "overdue_causes":
        ranked = sorted(overdue, key=lambda r: -r.overdue_amount)
        total = sum((r.overdue_amount for r in overdue), Decimal(0))
        over30 = sum((i.outstanding for i in snap.invoices
                      if not i.is_settled and (today - i.due_date).days > 30), Decimal(0))
        share = round(float(ranked[0].overdue_amount / total) * 100) if ranked and total else 0
        return intent, {
            "intent": intent, "total_overdue_display": format_inr(total),
            "overdue_customer_count": len(overdue), "top_share_pct": share,
            "over_30_days_display": format_inr(over30),
            "habitual_late_count": sum(r.late_payment_count >= 3 for r in overdue),
            "top_overdue": [{"company": r.company_name, "overdue_display": format_inr(r.overdue_amount)}
                            for r in ranked[:3]],
            "aging": [{**a, "amount_display": format_inr(a["amount"])} for a in snap.aging]}  # type: ignore[arg-type]
    risks = compute_risks(db, today)
    inv = summarize(risks)
    if intent == "inventory":
        urgent = sorted((r for r in risks if r.assessment.status is not StockStatus.healthy),
                        key=lambda r: (r.assessment.stock_coverage_days is None,
                                       r.assessment.stock_coverage_days or 0))[:5]
        return intent, {
            "intent": intent, "stockout_risk_count": inv.stockout_risk_10d,
            "critical_count": inv.critical, "low_count": inv.low_stock,
            "products": [{"name": r.product.name, "available": r.assessment.available_quantity,
                          "coverage_days": r.assessment.stock_coverage_days,
                          "recommended_order": r.assessment.recommended_order_quantity,
                          "unit": r.product.unit, "supplier": r.product.supplier_name} for r in urgent]}
    return "overview", {
        "intent": "overview", "follow_up_count": len(snap.follow_ups),
        "total_overdue_display": format_inr(snap.summary.total_overdue),
        "stockout_risk_count": inv.stockout_risk_10d, "purchase_order_count": len(inv.purchase_orders),
        "draft_invoice_count": count_by_status(db, InvoiceStatus.draft)}


def ask(db: Session, ai: AIService, question: str, today: date) -> tuple[str, Facts | None, AIResult]:
    intent, facts = retrieve_facts(db, question, today)
    if facts is None:
        return intent, None, AIResult(OUT_OF_SCOPE, "rules")
    return intent, facts, ai.answer(question, facts)


